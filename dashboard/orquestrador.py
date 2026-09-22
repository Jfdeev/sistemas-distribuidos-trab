"""Orquestrador de execuções disparadas pelo dashboard.

Mantém, no máximo, UMA execução por vez. A execução roda em processos
trabalhadores (via :func:`comum.motor.executar_paralelo`), disparados de uma
thread de orquestração para não bloquear o servidor web — assim o endpoint
de status continua respondendo enquanto a varredura acontece.

Método:
* ``"sequencial"`` → 1 processo varrendo o espaço inteiro (1 núcleo).
* ``"paralelo"``   → N processos, uma fatia contígua cada.

Ambos reutilizam o mesmo motor de varredura (DRY).
"""
from __future__ import annotations

import multiprocessing as mp
import threading
from typing import Any, Optional

from comum.config import resolver_hash_alvo
from comum.estado import EstadoCompartilhado
from comum.keyspace import EspacoDeBusca
from comum.motor import executar_paralelo

_METODOS_VALIDOS = ("sequencial", "paralelo")


class ExecucaoOcupadaError(RuntimeError):
    """Levantada ao tentar iniciar uma execução com outra em andamento."""


class Orquestrador:
    """Gerencia o ciclo de vida da execução corrente do quebrador."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._gerente: Optional[mp.managers.SyncManager] = None
        self._estado: Optional[EstadoCompartilhado] = None
        self._thread: Optional[threading.Thread] = None
        self._situacao = "ocioso"  # ocioso | rodando | concluido | erro
        self._metodo: Optional[str] = None
        self._parametros: Optional[dict] = None
        self._erro: Optional[str] = None

    def ocupado(self) -> bool:
        return self._situacao == "rodando"

    def iniciar(
        self,
        *,
        metodo: str,
        comprimento: int,
        charset: str,
        n_processos: int,
        hash_alvo: str | None = None,
        senha: str | None = None,
    ) -> None:
        """Inicia uma nova execução. Levanta se já houver uma em andamento.

        O alvo pode vir de ``senha`` (o painel calcula o hash dela), de
        ``hash_alvo`` (hex), ou, se ambos vazios, do pior caso (padrão).
        """
        metodo = metodo.lower()
        if metodo not in _METODOS_VALIDOS:
            raise ValueError("metodo deve ser 'sequencial' ou 'paralelo'")

        # Valida os parâmetros ANTES de mexer no estado atual, para que uma
        # entrada inválida não derrube uma execução anterior já concluída.
        espaco = EspacoDeBusca(charset=charset, comprimento=comprimento)
        n = 1 if metodo == "sequencial" else max(1, n_processos)
        hash_alvo = resolver_hash_alvo(espaco, hash_alvo=hash_alvo, senha=senha)

        with self._lock:
            if self._situacao == "rodando":
                raise ExecucaoOcupadaError("já existe uma execução em andamento")
            self._encerrar_gerente()

            self._gerente = mp.Manager()
            self._estado = EstadoCompartilhado(
                self._gerente,
                n_processos=n,
                total_candidatos=espaco.tamanho_total(),
                hash_alvo=hash_alvo,
                charset=charset,
                comprimento=comprimento,
            )
            self._metodo = metodo
            self._parametros = {
                "comprimento": comprimento,
                "charset": charset,
                "n_processos": n,
            }
            self._erro = None
            self._situacao = "rodando"

            self._thread = threading.Thread(
                target=self._rodar,
                args=(espaco, hash_alvo, n),
                daemon=True,
                name="orquestrador",
            )
            self._thread.start()

    def _rodar(self, espaco: EspacoDeBusca, hash_alvo: str, n: int) -> None:
        try:
            executar_paralelo(espaco, hash_alvo, n, self._estado)
            self._situacao = "concluido"
        except Exception as exc:  # expõe o erro no dashboard em vez de sumir
            self._erro = str(exc)
            self._situacao = "erro"

    def status(self) -> dict[str, Any]:
        """Retorna a situação atual mais a foto do estado (se houver)."""
        payload: dict[str, Any] = {
            "situacao": self._situacao,
            "metodo": self._metodo,
            "parametros": self._parametros,
            "erro": self._erro,
        }
        if self._estado is not None:
            payload.update(self._estado.snapshot())
        return payload

    def encerrar(self) -> None:
        """Encerra o Manager corrente (usado no fim dos testes/servidor)."""
        with self._lock:
            self._encerrar_gerente()

    def _encerrar_gerente(self) -> None:
        if self._gerente is not None:
            try:
                self._gerente.shutdown()
            except Exception:
                pass
            self._gerente = None
            self._estado = None
