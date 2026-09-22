"""Testes da resolução do hash-alvo (hash, senha ou pior caso)."""
import pytest

from comum.config import resolver_hash_alvo
from comum.hashutil import hash_de
from comum.keyspace import EspacoDeBusca

ESPACO = EspacoDeBusca(charset="abcdefghijklmnopqrstuvwxyz0123456789", comprimento=5)


def test_pior_caso_quando_nada_informado():
    assert resolver_hash_alvo(ESPACO) == hash_de(ESPACO.senha_alvo())


def test_hash_valido_e_normalizado_para_minusculo():
    alvo = hash_de("abcde").upper()
    assert resolver_hash_alvo(ESPACO, hash_alvo=alvo) == alvo.lower()


def test_hash_invalido_rejeitado():
    with pytest.raises(ValueError):
        resolver_hash_alvo(ESPACO, hash_alvo="nao-e-um-hash")


def test_senha_gera_o_hash_dela():
    assert resolver_hash_alvo(ESPACO, senha="test1") == hash_de("test1")


def test_senha_tem_precedencia_sobre_hash():
    alvo = resolver_hash_alvo(ESPACO, hash_alvo=hash_de("aaaaa"), senha="test1")
    assert alvo == hash_de("test1")


def test_senha_tamanho_diferente_rejeitada():
    with pytest.raises(ValueError):
        resolver_hash_alvo(ESPACO, senha="abc")  # 3 != 5


def test_senha_fora_do_charset_rejeitada():
    with pytest.raises(ValueError):
        resolver_hash_alvo(ESPACO, senha="TESTE")  # maiúsculas fora de [a-z0-9]
