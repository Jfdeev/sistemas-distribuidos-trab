"""Configuração de linha de comando compartilhada pelos quebradores.

Tanto ``cracker_seq.py`` quanto ``cracker_par.py`` (e o ``benchmark.py``)
precisam construir o mesmo espaço de busca e resolver o mesmo hash-alvo a
partir dos argumentos. Concentrar isso aqui evita duplicação (DRY) e garante
que as duas versões comparem exatamente o mesmo trabalho.
"""
from __future__ import annotations

import argparse
import re

from comum.hashutil import hash_de
from comum.keyspace import CHARSET_PADRAO, COMPRIMENTO_PADRAO, EspacoDeBusca

# Prefixo da linha "legível por máquina" que os quebradores imprimem no fim.
# O benchmark.py procura por esta linha para extrair o resumo em JSON.
PREFIXO_JSON = "RESULTADO_JSON "

# Um SHA-256 em hexadecimal tem exatamente 64 dígitos hex.
_RE_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def resolver_hash_alvo(
    espaco: EspacoDeBusca,
    *,
    hash_alvo: str | None = None,
    senha: str | None = None,
) -> str:
    """Decide qual hash-alvo usar, com validação.

    Precedência: ``senha`` (mais amigável) > ``hash_alvo`` > pior caso.

    * ``senha``: valida que ela cabe no espaço (comprimento e charset) e
      retorna o SHA-256 dela — ótimo para demonstração ao vivo.
    * ``hash_alvo``: valida que é um SHA-256 hexadecimal (64 dígitos).
    * nada: usa o PIOR CASO (hash da última senha do espaço), padrão do
      benchmark por ser determinístico.
    """
    if senha:
        if len(senha) != espaco.comprimento:
            raise ValueError(
                f"a senha tem {len(senha)} caractere(s), mas o comprimento "
                f"configurado é {espaco.comprimento}"
            )
        fora = sorted(set(senha) - set(espaco.charset))
        if fora:
            raise ValueError(
                "a senha contém caracteres fora do charset: " + "".join(fora)
            )
        return hash_de(senha)

    if hash_alvo:
        if not _RE_SHA256.match(hash_alvo):
            raise ValueError(
                "hash-alvo inválido: informe um SHA-256 com 64 dígitos hexadecimais"
            )
        return hash_alvo.lower()

    return hash_de(espaco.senha_alvo())


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
    parser.add_argument(
        "--senha-alvo",
        type=str,
        default=None,
        help=(
            "Senha conhecida para gerar o alvo (o programa calcula o SHA-256 "
            "dela). Tem precedência sobre --hash-alvo. Útil para demonstração."
        ),
    )


def espaco_e_alvo(args: argparse.Namespace) -> tuple[EspacoDeBusca, str]:
    """Constrói o espaço de busca e resolve o hash-alvo a partir dos args."""
    espaco = EspacoDeBusca(charset=args.charset, comprimento=args.comprimento)
    hash_alvo = resolver_hash_alvo(
        espaco,
        hash_alvo=args.hash_alvo,
        senha=getattr(args, "senha_alvo", None),
    )
    return espaco, hash_alvo
