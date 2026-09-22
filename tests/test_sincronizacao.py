"""Testes do contador global compartilhado (a seção crítica contestada)."""
import multiprocessing as mp

import pytest

from comum.estado import EstadoCompartilhado
from comum.hashutil import hash_de
from comum.keyspace import EspacoDeBusca
from comum.motor import executar_paralelo

# Espaço pequeno o bastante para o teste ser rápido, grande o bastante para
# que vários lotes sejam somados por vários processos.
ESPACO = EspacoDeBusca(charset="abcdefghij", comprimento=5)  # 10^5 = 100.000


def _rodar(n_processos: int, usar_lock: bool) -> dict:
    with mp.Manager() as gerente:
        alvo = hash_de(ESPACO.senha_alvo())
        estado = EstadoCompartilhado(
            gerente,
            n_processos=n_processos,
            total_candidatos=ESPACO.tamanho_total(),
            hash_alvo=alvo,
            charset=ESPACO.charset,
            comprimento=ESPACO.comprimento,
            usar_lock=usar_lock,
        )
        return executar_paralelo(ESPACO, alvo, n_processos, estado)


@pytest.mark.parametrize("n_processos", [2, 4, 8])
def test_contador_global_fecha_com_lock(n_processos):
    """Com o lock, o contador global sempre bate com o tamanho do espaço."""
    resumo = _rodar(n_processos, usar_lock=True)
    assert resumo["usou_lock"] is True
    assert resumo["contador_global"] == ESPACO.tamanho_total()
    assert resumo["contador_confere"] is True


def test_contador_sem_lock_nao_ultrapassa_o_total():
    """Sem o lock pode haver 'lost updates'; o contador nunca passa do total.

    Não afirmamos que HÁ corrida (é não determinística), apenas que o modo
    roda e mantém o invariante contador <= total.
    """
    resumo = _rodar(8, usar_lock=False)
    assert resumo["usou_lock"] is False
    assert resumo["contador_global"] <= ESPACO.tamanho_total()


def test_contador_no_sequencial_fecha():
    """Sequencial (1 processo) também soma o total corretamente."""
    resumo = _rodar(1, usar_lock=True)
    assert resumo["contador_global"] == ESPACO.tamanho_total()
    assert resumo["contador_confere"] is True
