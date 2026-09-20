"""Configuração de linha de comando compartilhada pelos quebradores.

Tanto ``cracker_seq.py`` quanto ``cracker_par.py`` (e o ``benchmark.py``)
precisam construir o mesmo espaço de busca e resolver o mesmo hash-alvo a
partir dos argumentos. Concentrar isso aqui evita duplicação (DRY) e garante
que as duas versões comparem exatamente o mesmo trabalho.
"""
from __future__ import annotations

import argparse

from comum.hashutil import hash_de
from comum.keyspace import CHARSET_PADRAO, COMPRIMENTO_PADRAO, EspacoDeBusca

# Prefixo da linha "legível por máquina" que os quebradores imprimem no fim.
# O benchmark.py procura por esta linha para extrair o resumo em JSON.
PREFIXO_JSON = "RESULTADO_JSON "


def adicionar_argumentos_espaco(parser: argparse.ArgumentParser) -> None:
    """Registra os argumentos que definem o espaço de busca e o alvo."""
    parser.add_argument(
        "--comprimento",
        type=int,
        default=COMPRIMENTO_PADRAO,
        help="Comprimento das senhas candidatas (padrão: %(default)s).",
    )
    parser.add_argument(
        "--charset",
        type=str,
        default=CHARSET_PADRAO,
        help="Conjunto de caracteres permitidos (padrão: [a-z0-9]).",
    )
    parser.add_argument(
        "--hash-alvo",
        type=str,
        default=None,
        help=(
            "SHA-256 alvo em hexadecimal. Se omitido, usa o PIOR CASO: o "
            "hash da última senha do espaço de busca."
        ),
    )


def espaco_e_alvo(args: argparse.Namespace) -> tuple[EspacoDeBusca, str]:
    """Constrói o espaço de busca e resolve o hash-alvo a partir dos args."""
    espaco = EspacoDeBusca(charset=args.charset, comprimento=args.comprimento)
    hash_alvo = args.hash_alvo or hash_de(espaco.senha_alvo())
    return espaco, hash_alvo
