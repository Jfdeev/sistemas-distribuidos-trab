"""Motor de varredura compartilhado (worker + orquestração de processos).

Este módulo concentra a lógica de execução usada tanto pela CLI paralela
(`paralelo/cracker_par.py`) quanto pelo dashboard web. Cada processo executa
:func:`trabalhar` sobre uma fatia do espaço; :func:`executar_paralelo`
particiona o espaço, dispara os processos e aguarda todos.

A versão "sequencial" nada mais é do que ``executar_paralelo`` com um único
processo varrendo o espaço inteiro (uma só fatia) — reaproveitando o mesmo
código (DRY).
"""
from __future__ import annotations

import multiprocessing as mp
import os
import time

from comum.estado import EstadoCompartilhado
from comum.hashutil import confere
from comum.keyspace import EspacoDeBusca

# A cada quantos candidatos cada processo atualiza seu contador no dict
# compartilhado. Alto o bastante para não gerar contenção no Manager, baixo
# o bastante para o dashboard parecer "ao vivo".
LOTE_ATUALIZACAO = 50_000


def trabalhar(
    espaco: EspacoDeBusca,
    inicio: int,
    fim: int,
    hash_alvo: str,
    id_fatia: int,
    estado: EstadoCompartilhado,
) -> None:
    """Função executada por cada processo: varre a fatia ``[inicio, fim)``."""
    pid = os.getpid()
    marco = time.perf_counter()
    testados = 0

    for candidato in espaco.gerar_intervalo(inicio, fim):
        testados += 1
        if confere(candidato, hash_alvo):
            # A escrita em resultado_final é a seção crítica; a serialização
            # via Lock está encapsulada em tentar_registrar_resultado().
            estado.tentar_registrar_resultado(candidato, id_fatia, pid)
            # Sem early-stop: continua varrendo a fatia até o fim.
        if testados % LOTE_ATUALIZACAO == 0:
            estado.registrar_progresso(id_fatia, pid, testados)

    duracao = time.perf_counter() - marco
    estado.registrar_conclusao(id_fatia, pid, testados, duracao)


def executar_paralelo(
    espaco: EspacoDeBusca,
    hash_alvo: str,
    n_processos: int,
    estado: EstadoCompartilhado,
) -> dict:
    """Dispara os processos, aguarda todos e devolve o resumo da execução."""
    fatias = espaco.particionar(n_processos)
    estado.marcar_inicio()

    processos: list[mp.Process] = []
    for id_fatia, (inicio, fim) in enumerate(fatias):
        processo = mp.Process(
            target=trabalhar,
            args=(espaco, inicio, fim, hash_alvo, id_fatia, estado),
            name=f"fatia-{id_fatia}",
        )
        processos.append(processo)
        processo.start()

    for processo in processos:
        processo.join()

    estado.marcar_fim()
    return montar_resumo(espaco, n_processos, estado)


def montar_resumo(
    espaco: EspacoDeBusca,
    n_processos: int,
    estado: EstadoCompartilhado,
) -> dict:
    """Monta o dicionário-resumo canônico de uma execução concluída."""
    foto = estado.snapshot()
    resultado = foto["resultado_final"]
    tempos_por_processo = {
        chave: dados.get("duracao_s")
        for chave, dados in sorted(
            foto["progresso"].items(), key=lambda kv: int(kv[0])
        )
    }
    return {
        "versao": "sequencial" if n_processos == 1 else "paralelo",
        "senha": resultado["senha"] if resultado else None,
        "processo_que_encontrou": resultado["processo"] if resultado else None,
        "testados": foto["testados_total"],
        "tempo_s": foto["tempo_decorrido_s"],
        "n_processos": n_processos,
        "total_candidatos": espaco.tamanho_total(),
        "tempos_por_processo_s": tempos_por_processo,
    }
