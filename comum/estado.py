"""Estado compartilhado entre os processos trabalhadores e o dashboard.

Toda a comunicação entre processos passa por um único
``multiprocessing.Manager().dict()`` (exigência do enunciado). Esse dict
guarda, por fatia/processo, o contador de candidatos testados e o timestamp
da última atualização, além de dois campos reservados:

* ``resultado_final`` — a senha encontrada e quem a encontrou. É a **seção
  crítica** do programa: vários processos poderiam tentar escrevê-la, então
  a escrita é protegida por um ``multiprocessing.Lock()`` e só o primeiro a
  chegar registra o resultado.
* ``meta`` — instantes de início e fim da varredura, para calcular o tempo
  decorrido exibido no dashboard.

Esta classe é um simples invólucro (wrapper) sobre esses recursos. Ela é
enviada como argumento para cada ``Process`` — os proxies do Manager e o
Lock são serializáveis pela máquina de multiprocessing, inclusive no Windows
(modo *spawn*).
"""
from __future__ import annotations

import multiprocessing as mp
import time
from typing import Any


class EstadoCompartilhado:
    """Encapsula o dict compartilhado e o lock da seção crítica."""

    CHAVE_RESULTADO = "resultado_final"
    CHAVE_META = "meta"
    _CHAVES_RESERVADAS = frozenset({CHAVE_RESULTADO, CHAVE_META})

    def __init__(
        self,
        gerente: mp.managers.SyncManager,
        *,
        n_processos: int,
        total_candidatos: int,
        hash_alvo: str,
        charset: str,
        comprimento: int,
    ) -> None:
        # Dict compartilhado entre todos os processos.
        self.dados = gerente.dict()
        # Primitiva de sincronização que protege a seção crítica.
        self.lock = mp.Lock()
        self.dados[self.CHAVE_META] = {"inicio": None, "fim": None}

        # Metadados imutáveis após a criação. São lidos apenas pelo dashboard,
        # que roda no processo principal; os trabalhadores recebem uma cópia
        # (via pickle) e não dependem desses valores.
        self.n_processos = n_processos
        self.total_candidatos = total_candidatos
        self.hash_alvo = hash_alvo
        self.charset = charset
        self.comprimento = comprimento

    # ------------------------------------------------------------------
    # Escritas feitas pelos processos trabalhadores.
    # ------------------------------------------------------------------
    def registrar_progresso(self, id_fatia: int, pid: int, testados: int) -> None:
        """Atualiza o contador de uma fatia (chamado a cada lote de candidatos).

        Reatribui o dicionário inteiro da fatia porque mutações *in-place* em
        valores aninhados de um Manager dict não se propagam entre processos.
        """
        self.dados[str(id_fatia)] = {
            "pid": pid,
            "testados": testados,
            "atualizado_em": time.time(),
            "concluido": False,
            "duracao_s": None,
        }

    def registrar_conclusao(
        self, id_fatia: int, pid: int, testados: int, duracao_s: float
    ) -> None:
        """Marca a fatia como concluída e grava o tempo do processo."""
        self.dados[str(id_fatia)] = {
            "pid": pid,
            "testados": testados,
            "atualizado_em": time.time(),
            "concluido": True,
            "duracao_s": duracao_s,
        }

    def tentar_registrar_resultado(self, senha: str, id_fatia: int, pid: int) -> None:
        """Registra a senha encontrada de forma segura entre processos.

        Só o PRIMEIRO processo a encontrar a senha escreve em
        ``resultado_final``; os demais (caso houvesse mais de uma colisão)
        encontram a chave já preenchida e não sobrescrevem.
        """
        # ===================== INÍCIO DA SEÇÃO CRÍTICA =====================
        # A partir daqui apenas um processo por vez executa: o lock serializa
        # o teste-e-escrita sobre `resultado_final`, evitando condição de
        # corrida entre trabalhadores que terminem quase ao mesmo tempo.
        with self.lock:
            if self.CHAVE_RESULTADO not in self.dados:
                self.dados[self.CHAVE_RESULTADO] = {
                    "senha": senha,
                    "processo": id_fatia,
                    "pid": pid,
                    "encontrado_em": time.time(),
                }
        # ====================== FIM DA SEÇÃO CRÍTICA =======================

    def marcar_inicio(self) -> None:
        self._atualizar_meta("inicio", time.time())

    def marcar_fim(self) -> None:
        self._atualizar_meta("fim", time.time())

    def _atualizar_meta(self, campo: str, valor: float) -> None:
        meta = dict(self.dados[self.CHAVE_META])
        meta[campo] = valor
        self.dados[self.CHAVE_META] = meta

    # ------------------------------------------------------------------
    # Leitura feita pelo dashboard (processo principal).
    # ------------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        """Monta uma foto consistente do estado, pronta para virar JSON."""
        bruto = dict(self.dados)  # cópia rasa dos itens do Manager dict
        meta = bruto.get(self.CHAVE_META, {})
        resultado = bruto.get(self.CHAVE_RESULTADO)

        fatias = {
            chave: valor
            for chave, valor in bruto.items()
            if chave not in self._CHAVES_RESERVADAS
        }
        testados_total = sum(f["testados"] for f in fatias.values())

        inicio = meta.get("inicio")
        fim = meta.get("fim")
        if inicio is None:
            decorrido = 0.0
        else:
            decorrido = (fim if fim is not None else time.time()) - inicio

        return {
            "n_processos": self.n_processos,
            "total_candidatos": self.total_candidatos,
            "hash_alvo": self.hash_alvo,
            "charset": self.charset,
            "comprimento": self.comprimento,
            "tempo_decorrido_s": decorrido,
            "testados_total": testados_total,
            "progresso": fatias,
            "resultado_final": resultado,
            "concluido": fim is not None,
        }
