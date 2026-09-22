"""Teste do verificador de equivalência (seq == par)."""
from comum.hashutil import hash_de
from comum.keyspace import EspacoDeBusca

from scripts.verificar import verificar

ESPACO = EspacoDeBusca(charset="ab", comprimento=5)  # 2^5 = 32 candidatos


def test_verificar_confirma_equivalencia():
    alvo = hash_de(ESPACO.senha_alvo())
    resultado = verificar(ESPACO, alvo, n_processos=4)
    assert resultado["igual"] is True
    assert resultado["sequencial"]["senha"] == resultado["paralelo"]["senha"]
    assert resultado["sequencial"]["testados"] == resultado["paralelo"]["testados"]
