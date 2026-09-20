"""Testes de integração das versões sequencial e paralela.

Usam um espaço de busca minúsculo para rodar rápido, mas exercitam o
caminho real: varredura completa, contagem de candidatos e escrita da senha
no estado compartilhado sob a seção crítica.
"""
import multiprocessing as mp

import pytest

from comum.estado import EstadoCompartilhado
from comum.hashutil import hash_de
from comum.keyspace import EspacoDeBusca
from comum.motor import executar_paralelo
from sequencial.cracker_seq import executar_sequencial

# Espaço pequeno: "ab" ^ 4 = 16 candidatos. Senha-alvo (pior caso) = "bbbb".
ESPACO = EspacoDeBusca(charset="ab", comprimento=4)


def test_sequencial_encontra_pior_caso_e_conta_tudo():
    alvo = hash_de(ESPACO.senha_alvo())
    resumo = executar_sequencial(ESPACO, alvo)
    assert resumo["senha"] == "bbbb"
    assert resumo["testados"] == ESPACO.tamanho_total()  # varreu o espaço inteiro


def _rodar_paralelo(n_processos: int) -> dict:
    with mp.Manager() as gerente:
        alvo = hash_de(ESPACO.senha_alvo())
        estado = EstadoCompartilhado(
            gerente,
            n_processos=n_processos,
            total_candidatos=ESPACO.tamanho_total(),
            hash_alvo=alvo,
            charset=ESPACO.charset,
            comprimento=ESPACO.comprimento,
        )
        return executar_paralelo(ESPACO, alvo, n_processos, estado)


@pytest.mark.parametrize("n_processos", [1, 2, 3, 4])
def test_paralelo_encontra_senha_e_soma_dos_testados_bate(n_processos):
    resumo = _rodar_paralelo(n_processos)
    assert resumo["senha"] == "bbbb"
    # A soma dos candidatos testados por todas as fatias == total do espaço.
    assert resumo["testados"] == ESPACO.tamanho_total()


def test_paralelo_reporta_qual_fatia_encontrou():
    # Com 2 processos, o pior caso ("bbbb", último índice) cai na 2ª fatia (id 1).
    resumo = _rodar_paralelo(2)
    assert resumo["processo_que_encontrou"] == 1


def test_sequencial_e_paralelo_concordam_na_senha():
    alvo = hash_de(ESPACO.senha_alvo())
    resumo_seq = executar_sequencial(ESPACO, alvo)
    resumo_par = _rodar_paralelo(4)
    assert resumo_seq["senha"] == resumo_par["senha"]
    assert resumo_seq["testados"] == resumo_par["testados"]
