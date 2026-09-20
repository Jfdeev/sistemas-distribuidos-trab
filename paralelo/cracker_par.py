"""Quebrador de hash — versão PARALELA (multiprocessing), CLI de medição.

=========================================================================
POR QUE PROCESSOS E NÃO THREADS
-------------------------------------------------------------------------
O trabalho aqui é *CPU-bound*: quase todo o tempo é gasto calculando
SHA-256, uma operação de CPU pura. No CPython, o GIL (Global Interpreter
Lock) permite que apenas UMA thread execute bytecode Python por vez, então
threads NÃO dariam paralelismo real para trabalho CPU-bound — haveria
concorrência, mas com as threads rodando uma de cada vez em um único
núcleo. Por isso usamos ``multiprocessing.Process``: cada processo tem seu
próprio interpretador e seu próprio GIL, e o sistema operacional os
distribui entre os núcleos físicos, obtendo paralelismo de verdade.
=========================================================================

Esta CLI executa uma varredura e imprime o resumo (usada pelo benchmark). A
lógica de varredura vive em ``comum/motor.py`` e é compartilhada com o
dashboard web. Para a interface web interativa, use ``dashboard/app.py``.

Uso:
    python paralelo/cracker_par.py [--processos N] [--comprimento N]
                                   [--charset ...] [--hash-alvo HEX]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import pathlib
import sys

# Permite executar o script diretamente sem instalar o pacote.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from comum.config import (  # noqa: E402
    PREFIXO_JSON,
    adicionar_argumentos_espaco,
    espaco_e_alvo,
)
from comum.estado import EstadoCompartilhado  # noqa: E402
from comum.motor import executar_paralelo  # noqa: E402


def _imprimir_resumo(resumo: dict) -> None:
    print("=" * 60)
    print(f"QUEBRADOR PARALELO — {resumo['n_processos']} processo(s)")
    print("=" * 60)
    print(f"Senha encontrada   : {resumo['senha']}")
    print(f"Encontrada pela fatia: {resumo['processo_que_encontrou']}")
    print(f"Candidatos testados: {resumo['testados']:,}".replace(",", "."))
    print(f"Tempo total (parede): {resumo['tempo_s']:.3f} s")
    print("Tempo por processo:")
    for fatia, duracao in resumo["tempos_por_processo_s"].items():
        marca = f"{duracao:.3f} s" if duracao is not None else "(sem dados)"
        print(f"  fatia {fatia}: {marca}")
    # Linha legível por máquina, consumida pelo benchmark.py.
    print(PREFIXO_JSON + json.dumps(resumo))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Quebrador de hash paralelo.")
    adicionar_argumentos_espaco(parser)
    parser.add_argument(
        "--processos",
        type=int,
        default=os.cpu_count(),
        help="Número de processos (padrão: nº de vCPUs = %(default)s).",
    )
    args = parser.parse_args(argv)

    espaco, hash_alvo = espaco_e_alvo(args)
    n_processos = max(1, args.processos)

    print(
        f"Espaço: charset={espaco.charset!r} comprimento={espaco.comprimento} "
        f"total={espaco.tamanho_total():,}".replace(",", ".")
    )
    print(f"Hash-alvo: {hash_alvo}")
    print(f"Processos: {n_processos}")

    # O Manager gerencia o dict compartilhado; usá-lo como context manager
    # garante que o processo do Manager seja encerrado ao final.
    with mp.Manager() as gerente:
        estado = EstadoCompartilhado(
            gerente,
            n_processos=n_processos,
            total_candidatos=espaco.tamanho_total(),
            hash_alvo=hash_alvo,
            charset=espaco.charset,
            comprimento=espaco.comprimento,
        )
        resumo = executar_paralelo(espaco, hash_alvo, n_processos, estado)
        _imprimir_resumo(resumo)


if __name__ == "__main__":
    # freeze_support() é boa prática no Windows (modo spawn), sobretudo se o
    # programa vier a ser empacotado como executável.
    mp.freeze_support()
    main()
