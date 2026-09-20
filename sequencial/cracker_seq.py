"""Quebrador de hash — versão SEQUENCIAL (linha de base).

Varre o espaço de busca inteiro, em um único processo, calculando o SHA-256
de cada candidato e comparando com o alvo. Não há *early-stop*: mesmo após
encontrar a senha, a varredura continua até esgotar o espaço, para que o
volume de trabalho seja idêntico ao da versão paralela e os tempos sejam
comparáveis.

Uso:
    python sequencial/cracker_seq.py [--comprimento N] [--charset ...] [--hash-alvo HEX]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

# Permite executar o script diretamente (python sequencial/cracker_seq.py)
# sem instalar o pacote: coloca a raiz do repositório no sys.path.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from comum.config import (  # noqa: E402  (import após ajustar o sys.path)
    PREFIXO_JSON,
    adicionar_argumentos_espaco,
    espaco_e_alvo,
)
from comum.hashutil import confere  # noqa: E402
from comum.keyspace import EspacoDeBusca  # noqa: E402


def executar_sequencial(espaco: EspacoDeBusca, hash_alvo: str) -> dict:
    """Varre o espaço inteiro e devolve um resumo da execução.

    Retorna um dicionário com a senha encontrada (ou ``None``), o total de
    candidatos testados e o tempo decorrido em segundos.
    """
    inicio = time.perf_counter()
    testados = 0
    senha_encontrada: str | None = None

    for candidato in espaco.gerar_intervalo(0, espaco.tamanho_total()):
        testados += 1
        if confere(candidato, hash_alvo):
            senha_encontrada = candidato
            # Sem early-stop de propósito: continua varrendo até o fim.

    tempo_s = time.perf_counter() - inicio
    return {
        "versao": "sequencial",
        "senha": senha_encontrada,
        "processo_que_encontrou": None,
        "testados": testados,
        "tempo_s": tempo_s,
        "n_processos": 1,
        "total_candidatos": espaco.tamanho_total(),
    }


def _imprimir_resumo(resumo: dict) -> None:
    print("=" * 60)
    print("QUEBRADOR SEQUENCIAL — resultado")
    print("=" * 60)
    print(f"Senha encontrada : {resumo['senha']}")
    print(f"Candidatos testados: {resumo['testados']:,}".replace(",", "."))
    print(f"Tempo total       : {resumo['tempo_s']:.3f} s")
    # Linha legível por máquina, consumida pelo benchmark.py.
    print(PREFIXO_JSON + json.dumps(resumo))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Quebrador de hash sequencial.")
    adicionar_argumentos_espaco(parser)
    args = parser.parse_args(argv)

    espaco, hash_alvo = espaco_e_alvo(args)
    print(
        f"Espaço: charset={espaco.charset!r} comprimento={espaco.comprimento} "
        f"total={espaco.tamanho_total():,}".replace(",", ".")
    )
    print(f"Hash-alvo: {hash_alvo}")
    resumo = executar_sequencial(espaco, hash_alvo)
    _imprimir_resumo(resumo)


if __name__ == "__main__":
    main()
