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
    CHAVE_CONTADOR = "contador_global"
    _CHAVES_RESERVADAS = frozenset({CHAVE_RESULTADO, CHAVE_META, CHAVE_CONTADOR})

    def __init__(
        self,
        gerente: mp.managers.SyncManager,
        *,
        n_processos: int,
        total_candidatos: int,
        hash_alvo: str,
        charset: str,
        comprimento: int,
        usar_lock: bool = True,
    ) -> None:
        # Dict compartilhado entre todos os processos.
        self.dados = gerente.dict()
        # Primitiva de sincronização que protege as seções críticas.
        self.lock = mp.Lock()
        # Se False, as seções críticas rodam SEM o lock — apenas para
        # demonstrar a condição de corrida ao vivo (ver `somar_ao_contador_global`).
        self.usar_lock = usar_lock
        self.dados[self.CHAVE_META] = {"inicio": None, "fim": None}
        # Contador global compartilhado, escrito por TODOS os processos.
        self.dados[self.CHAVE_CONTADOR] = 0

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

    def somar_ao_contador_global(self, quantidade: int) -> None:
        """Soma ``quantidade`` ao contador global compartilhado.

        Esta é a seção crítica *contestada* do programa: TODOS os processos
        incrementam a MESMA variável (`contador_global`) num padrão
        ler-modificar-escrever. Como o Manager atende cada leitura e cada
        escrita como operações separadas, sem o lock dois processos podem ler
        o mesmo valor antigo e sobrescrever um ao outro — o clássico
        *lost update* (condição de corrida). Com o lock, o total sempre fecha
        exatamente com o tamanho do espaço de busca.

        O incremento é feito em LOTES (não a cada candidato) para não
        transformar isto numa trava em volta do laço inteiro — o que mataria
        o paralelismo.
        """
        if self.usar_lock:
            # =================== INÍCIO DA SEÇÃO CRÍTICA ===================
            with self.lock:
                self.dados[self.CHAVE_CONTADOR] = (
                    self.dados.get(self.CHAVE_CONTADOR, 0) + quantidade
                )
            # ==================== FIM DA SEÇÃO CRÍTICA =====================
        else:
            # Versão SEM sincronização — só para demonstrar a corrida ao vivo.
            atual = self.dados.get(self.CHAVE_CONTADOR, 0)
            self.dados[self.CHAVE_CONTADOR] = atual + quantidade

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
        contador_global = bruto.get(self.CHAVE_CONTADOR, 0)

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
            "contador_global": contador_global,
            # True quando o contador global (somado sob lock) fecha com o total:
            # prova visual de que não houve condição de corrida.
            "contador_confere": contador_global == self.total_candidatos,
            "usar_lock": self.usar_lock,
            "progresso": fatias,
            "resultado_final": resultado,
            "concluido": fim is not None,
        }
