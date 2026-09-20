"""Geração determinística do espaço de busca e seu particionamento.

O espaço de busca é o conjunto de todas as strings de um dado *comprimento*
formadas a partir de um *charset* fixo. Cada candidato recebe um índice
inteiro em ``[0, tamanho_total)`` por meio de uma numeração posicional de
base ``len(charset)`` (o candidato de índice 0 é ``charset[0]`` repetido; o
de índice ``tamanho_total - 1`` é ``charset[-1]`` repetido).

Como a numeração é totalmente determinística, tanto a versão sequencial
quanto a paralela varrem exatamente os mesmos candidatos na mesma ordem, e
o particionamento em fatias contíguas cobre o espaço inteiro sem
sobreposição nem buraco.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

# ---------------------------------------------------------------------------
# Configuração central do espaço de busca.
#
# O enunciado do trabalho cita "6 caracteres, [a-z0-9]" como exemplo, mas
# 36**6 ≈ 2,2 bilhões de candidatos tornam inviável varrer o espaço INTEIRO
# várias vezes em Python puro (o benchmark repete cada configuração e nunca
# pode parar antes de esgotar o espaço). Por isso o comprimento padrão é
# deliberadamente menor e TODOS os scripts aceitam sobrescrever charset e
# comprimento por argumento de linha de comando.
#
# Regra prática de calibração (ver README): escolha o comprimento de forma
# que a execução sequencial leve de ~15 s a ~60 s na sua máquina/instância.
# Assim o speedup fica visível sem que o benchmark demore demais.
# ---------------------------------------------------------------------------
CHARSET_PADRAO = "abcdefghijklmnopqrstuvwxyz0123456789"  # [a-z0-9], base 36
COMPRIMENTO_PADRAO = 5  # 36**5 = 60.466.176 candidatos


@dataclass(frozen=True)
class EspacoDeBusca:
    """Descreve um espaço de busca e sabe mapear índice <-> candidato."""

    charset: str = CHARSET_PADRAO
    comprimento: int = COMPRIMENTO_PADRAO

    def __post_init__(self) -> None:
        if self.comprimento <= 0:
            raise ValueError("comprimento deve ser >= 1")
        if len(self.charset) == 0:
            raise ValueError("charset não pode ser vazio")
        if len(set(self.charset)) != len(self.charset):
            raise ValueError("charset não pode ter caracteres repetidos")

    @property
    def base(self) -> int:
        """Base da numeração posicional (quantidade de símbolos do charset)."""
        return len(self.charset)

    def tamanho_total(self) -> int:
        """Quantidade total de candidatos do espaço (base ** comprimento)."""
        return self.base ** self.comprimento

    def indice_para_candidato(self, indice: int) -> str:
        """Converte um índice inteiro no candidato correspondente.

        Usa numeração posicional big-endian: o dígito mais significativo fica
        na primeira posição da string. Ideal para acesso aleatório (ex.:
        obter a senha-alvo no último índice). Para varredura sequencial de um
        intervalo grande prefira :meth:`gerar_intervalo`, que é incremental.
        """
        total = self.tamanho_total()
        if not 0 <= indice < total:
            raise IndexError(f"índice {indice} fora de [0, {total})")
        base = self.base
        digitos = [0] * self.comprimento
        for posicao in range(self.comprimento - 1, -1, -1):
            indice, resto = divmod(indice, base)
            digitos[posicao] = resto
        return "".join(self.charset[d] for d in digitos)

    def gerar_intervalo(self, inicio: int, fim: int) -> Iterator[str]:
        """Gera os candidatos dos índices em ``[inicio, fim)`` em ordem.

        Implementado como um "odômetro" que incrementa os dígitos in-place,
        evitando refazer a divisão inteira a cada candidato — o que importa
        no laço quente do quebrador.
        """
        if inicio >= fim:
            return
        total = self.tamanho_total()
        if not (0 <= inicio <= total and inicio <= fim <= total):
            raise IndexError(f"intervalo [{inicio}, {fim}) fora de [0, {total}]")

        base = self.base
        charset = self.charset
        comprimento = self.comprimento

        # Estado inicial = dígitos do índice `inicio` (big-endian).
        indice = inicio
        digitos = [0] * comprimento
        for posicao in range(comprimento - 1, -1, -1):
            indice, digitos[posicao] = divmod(indice, base)

        for _ in range(fim - inicio):
            yield "".join(charset[d] for d in digitos)
            # Incrementa o odômetro a partir do dígito menos significativo.
            posicao = comprimento - 1
            while posicao >= 0:
                digitos[posicao] += 1
                if digitos[posicao] < base:
                    break
                digitos[posicao] = 0
                posicao -= 1

    def particionar(self, n_fatias: int) -> list[tuple[int, int]]:
        """Divide ``[0, tamanho_total)`` em ``n_fatias`` faixas contíguas.

        As faixas têm tamanhos o mais iguais possível: o resto da divisão é
        distribuído uma unidade por vez entre as primeiras fatias. A união
        das faixas cobre o espaço inteiro, sem sobreposição nem buraco. Se
        ``n_fatias`` for maior que o total, as últimas faixas ficam vazias
        (inicio == fim), o que é tratado normalmente por ``gerar_intervalo``.
        """
        if n_fatias <= 0:
            raise ValueError("n_fatias deve ser >= 1")
        total = self.tamanho_total()
        tamanho_base, resto = divmod(total, n_fatias)

        fatias: list[tuple[int, int]] = []
        inicio = 0
        for k in range(n_fatias):
            tamanho = tamanho_base + (1 if k < resto else 0)
            fim = inicio + tamanho
            fatias.append((inicio, fim))
            inicio = fim
        return fatias

    def senha_alvo(self) -> str:
        """Senha fixada no PIOR CASO: o último candidato do espaço.

        Fixar o alvo na última posição garante que qualquer varredura
        completa (sequencial ou paralela) processe exatamente o mesmo volume
        de trabalho, tornando os tempos comparáveis entre execuções.
        """
        return self.indice_para_candidato(self.tamanho_total() - 1)


# Instância padrão usada pelos scripts quando nada é sobrescrito.
ESPACO_PADRAO = EspacoDeBusca()
