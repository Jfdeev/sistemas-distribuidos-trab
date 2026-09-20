"""Servidor Flask do dashboard: painel de controle + status ao vivo.

Diferente de rodar a CLI, aqui o dashboard é um SERVIDOR que você sobe uma
vez; pela própria página você escolhe o método (sequencial/paralelo), o
número de processos e o comprimento, e dispara a execução. O servidor
orquestra a varredura em processos trabalhadores e a página faz polling em
``/api/status`` a cada 500 ms.

Rotas:
* ``GET  /``            → painel de controle + visualização ao vivo.
* ``GET  /api/status``  → situação atual e progresso, em JSON.
* ``POST /api/iniciar`` → inicia uma execução com os parâmetros informados.

Uso:
    python dashboard/app.py [--porta 8080] [--host 0.0.0.0]
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

# Permite executar o script diretamente sem instalar o pacote.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from flask import Flask, jsonify, render_template, request  # noqa: E402

from dashboard.orquestrador import ExecucaoOcupadaError, Orquestrador  # noqa: E402

CHARSET_PADRAO = "abcdefghijklmnopqrstuvwxyz0123456789"


def criar_app(orquestrador: Orquestrador | None = None) -> Flask:
    """Cria a aplicação Flask ligada a um orquestrador (injetável nos testes)."""
    orquestrador = orquestrador or Orquestrador()
    app = Flask(__name__)
    app.config["ORQUESTRADOR"] = orquestrador

    @app.route("/")
    def index() -> str:
        return render_template("status.html", cpu_count=os.cpu_count() or 1)

    @app.route("/api/status")
    def status():
        return jsonify(orquestrador.status())

    @app.route("/api/iniciar", methods=["POST"])
    def iniciar():
        dados = request.get_json(silent=True) or {}
        try:
            metodo = str(dados.get("metodo", "paralelo"))
            comprimento = int(dados.get("comprimento", 5))
            charset = str(dados.get("charset") or CHARSET_PADRAO)
            n_processos = int(dados.get("n_processos", os.cpu_count() or 1))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "erro": "parâmetros inválidos"}), 400

        try:
            orquestrador.iniciar(
                metodo=metodo,
                comprimento=comprimento,
                charset=charset,
                n_processos=n_processos,
            )
        except ExecucaoOcupadaError as exc:
            return jsonify({"ok": False, "erro": str(exc)}), 409
        except ValueError as exc:
            return jsonify({"ok": False, "erro": str(exc)}), 400

        return jsonify({"ok": True})

    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Dashboard web do quebrador.")
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args(argv)

    app = criar_app()
    print(f"Dashboard em http://localhost:{args.porta}  (Ctrl+C para sair)")
    app.run(
        host=args.host,
        port=args.porta,
        threaded=True,
        use_reloader=False,
        debug=False,
    )


if __name__ == "__main__":
    # freeze_support() é boa prática no Windows (modo spawn), já que o
    # orquestrador cria processos trabalhadores.
    import multiprocessing as mp

    mp.freeze_support()
    main()
