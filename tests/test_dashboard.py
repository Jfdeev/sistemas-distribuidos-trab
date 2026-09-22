"""Testes das rotas HTTP do dashboard (via Flask test client)."""
import time

import pytest

flask = pytest.importorskip("flask")  # pula se o Flask não estiver instalado

from dashboard.app import criar_app  # noqa: E402
from dashboard.orquestrador import Orquestrador  # noqa: E402


@pytest.fixture()
def cliente():
    orquestrador = Orquestrador()
    app = criar_app(orquestrador)
    app.config.update(TESTING=True)
    yield app.test_client()
    orquestrador.encerrar()


def test_index_renderiza(cliente):
    resp = cliente.get("/")
    assert resp.status_code == 200
    assert b"<title>" in resp.data


def test_status_ocioso(cliente):
    dados = cliente.get("/api/status").get_json()
    assert dados["situacao"] == "ocioso"


def test_iniciar_executa_ate_concluir(cliente):
    resp = cliente.post(
        "/api/iniciar",
        json={"metodo": "paralelo", "comprimento": 4, "charset": "ab", "n_processos": 2},
    )
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True

    limite = time.time() + 20
    dados = {}
    while time.time() < limite:
        dados = cliente.get("/api/status").get_json()
        if dados["situacao"] in ("concluido", "erro"):
            break
        time.sleep(0.05)

    assert dados["situacao"] == "concluido"
    assert dados["resultado_final"]["senha"] == "bbbb"


def test_iniciar_com_metodo_invalido_retorna_400(cliente):
    resp = cliente.post("/api/iniciar", json={"metodo": "turbo", "comprimento": 2, "charset": "ab"})
    assert resp.status_code == 400
    assert resp.get_json()["ok"] is False


def test_iniciar_com_senha_customizada(cliente):
    resp = cliente.post(
        "/api/iniciar",
        json={
            "metodo": "paralelo", "comprimento": 4, "charset": "ab",
            "n_processos": 2, "senha": "baba",
        },
    )
    assert resp.status_code == 200

    limite = time.time() + 20
    dados = {}
    while time.time() < limite:
        dados = cliente.get("/api/status").get_json()
        if dados["situacao"] in ("concluido", "erro"):
            break
        time.sleep(0.05)
    assert dados["situacao"] == "concluido"
    assert dados["resultado_final"]["senha"] == "baba"


def test_iniciar_com_hash_invalido_retorna_400(cliente):
    resp = cliente.post(
        "/api/iniciar",
        json={"metodo": "paralelo", "comprimento": 4, "charset": "ab", "hash_alvo": "xyz"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["ok"] is False
