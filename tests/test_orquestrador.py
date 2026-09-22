"""Testes do orquestrador de execuções do dashboard."""
import time

import pytest

from dashboard.orquestrador import ExecucaoOcupadaError, Orquestrador

# Espaço minúsculo ("ab" ^ 4 = 16 candidatos), senha-alvo (pior caso) = "bbbb".
CHARSET = "ab"
COMPRIMENTO = 4


def _esperar_conclusao(orq: Orquestrador, timeout: float = 20.0) -> dict:
    limite = time.time() + timeout
    while time.time() < limite:
        estado = orq.status()
        if estado["situacao"] in ("concluido", "erro"):
            return estado
        time.sleep(0.05)
    raise AssertionError("execução não concluiu no tempo esperado")


@pytest.mark.parametrize("metodo,n", [("sequencial", 1), ("paralelo", 4)])
def test_orquestrador_encontra_senha(metodo, n):
    orq = Orquestrador()
    try:
        orq.iniciar(metodo=metodo, comprimento=COMPRIMENTO, charset=CHARSET, n_processos=n)
        estado = _esperar_conclusao(orq)
        assert estado["situacao"] == "concluido"
        assert estado["resultado_final"]["senha"] == "bbbb"
        assert estado["testados_total"] == 16  # varreu tudo, sem early-stop
    finally:
        orq.encerrar()


def test_sequencial_forca_um_processo():
    orq = Orquestrador()
    try:
        # Mesmo pedindo 8 processos, o método sequencial usa 1.
        orq.iniciar(metodo="sequencial", comprimento=COMPRIMENTO, charset=CHARSET, n_processos=8)
        estado = _esperar_conclusao(orq)
        assert estado["parametros"]["n_processos"] == 1
        assert estado["n_processos"] == 1
    finally:
        orq.encerrar()


def test_iniciar_com_senha_customizada():
    """Alvo vindo de uma senha específica dentro do espaço."""
    orq = Orquestrador()
    try:
        # senha "abab" está no espaço "ab"^4.
        orq.iniciar(
            metodo="paralelo", comprimento=4, charset="ab", n_processos=4, senha="abab"
        )
        estado = _esperar_conclusao(orq)
        assert estado["situacao"] == "concluido"
        assert estado["resultado_final"]["senha"] == "abab"
    finally:
        orq.encerrar()


def test_metodo_invalido_e_rejeitado():
    orq = Orquestrador()
    with pytest.raises(ValueError):
        orq.iniciar(metodo="turbo", comprimento=2, charset="ab", n_processos=1)


def test_senha_fora_do_espaco_e_rejeitada():
    orq = Orquestrador()
    with pytest.raises(ValueError):
        # "abc" tem char fora do charset "ab".
        orq.iniciar(metodo="paralelo", comprimento=4, charset="ab", n_processos=2, senha="abc")


def test_charset_invalido_e_rejeitado():
    orq = Orquestrador()
    with pytest.raises(ValueError):
        orq.iniciar(metodo="paralelo", comprimento=2, charset="aab", n_processos=2)


def test_nao_permite_duas_execucoes_simultaneas():
    orq = Orquestrador()
    try:
        # iniciar() marca "rodando" de forma síncrona, então a 2ª chamada
        # imediata deve ser rejeitada (o espaço maior é só folga extra).
        orq.iniciar(metodo="paralelo", comprimento=5, charset="abcdefghij", n_processos=2)
        with pytest.raises(ExecucaoOcupadaError):
            orq.iniciar(metodo="paralelo", comprimento=5, charset="abcdefghij", n_processos=2)
        _esperar_conclusao(orq)
    finally:
        orq.encerrar()
