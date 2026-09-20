"""Testes das utilidades de hash."""
from comum.hashutil import confere, hash_de


def test_hash_de_vetor_conhecido():
    # Vetor de teste clássico do SHA-256 para a string "abc".
    esperado = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert hash_de("abc") == esperado


def test_confere_positivo():
    alvo = hash_de("senha123")
    assert confere("senha123", alvo) is True


def test_confere_negativo():
    alvo = hash_de("senha123")
    assert confere("senha124", alvo) is False


def test_hash_e_deterministico():
    assert hash_de("qualquer") == hash_de("qualquer")
