"""Utilidades de hash SHA-256 usadas pelo quebrador.

Este módulo concentra as duas operações de hash do projeto para evitar
duplicação (DRY): gerar o hash-alvo a partir de uma senha conhecida e
conferir se um candidato bate com esse alvo.
"""
from __future__ import annotations

import hashlib


def hash_de(texto: str) -> str:
    """Retorna o SHA-256 (em hexadecimal) do texto informado.

    A codificação é fixada em UTF-8 para que o hash seja reprodutível em
    qualquer máquina, independentemente do locale do sistema.
    """
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def confere(candidato: str, hash_alvo: str) -> bool:
    """Indica se o candidato, ao ser hasheado, reproduz o hash-alvo.

    Observação de desempenho: no laço quente do quebrador esta função é
    chamada uma vez por candidato. O custo extra da chamada de função
    (frente a inlinar ``hashlib.sha256`` no laço) é pequeno e foi mantido
    de propósito para preservar legibilidade e reaproveitamento — o gargalo
    real é o próprio cálculo do SHA-256, não a chamada Python em volta dele.
    """
    return hash_de(candidato) == hash_alvo
