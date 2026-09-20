"""Testes do gerador/particionador do espaço de busca.

Cobre as duas garantias exigidas pelo enunciado:
  1. A soma dos candidatos das fatias bate com o total (sem sobreposição
     nem buraco).
  2. A senha fixada na última posição recalcula para o hash-alvo.
"""
import pytest

from comum.hashutil import hash_de
from comum.keyspace import EspacoDeBusca


# ---------------------------------------------------------------------------
# 1. Particionamento: cobertura exata do espaço.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("comprimento", [1, 2, 3])
@pytest.mark.parametrize("n_fatias", [1, 2, 3, 4, 7, 8, 100])
def test_particionamento_cobre_espaco_inteiro(comprimento, n_fatias):
    espaco = EspacoDeBusca(charset="abc", comprimento=comprimento)
    total = espaco.tamanho_total()
    fatias = espaco.particionar(n_fatias)

    # A soma dos tamanhos das fatias é exatamente o total.
    soma = sum(fim - inicio for inicio, fim in fatias)
    assert soma == total

    # As fatias são contíguas: começam em 0, terminam no total, sem gaps.
    assert fatias[0][0] == 0
    assert fatias[-1][1] == total
    for (_, fim_anterior), (inicio_seguinte, _) in zip(fatias, fatias[1:]):
        assert fim_anterior == inicio_seguinte  # sem buraco nem sobreposição


@pytest.mark.parametrize("n_fatias", [1, 2, 3, 5, 8])
def test_particionamento_visita_cada_indice_uma_unica_vez(n_fatias):
    espaco = EspacoDeBusca(charset="ab", comprimento=4)  # 16 índices
    total = espaco.tamanho_total()
    fatias = espaco.particionar(n_fatias)

    visitados = []
    for inicio, fim in fatias:
        visitados.extend(range(inicio, fim))

    assert visitados == list(range(total))  # ordem preservada, sem repetição


def test_particionamento_tamanhos_o_mais_iguais_possivel():
    espaco = EspacoDeBusca(charset="ab", comprimento=3)  # total = 8
    fatias = espaco.particionar(3)
    tamanhos = sorted(fim - inicio for inicio, fim in fatias)
    # 8 dividido em 3 => [2, 3, 3]: diferença máxima de 1 entre fatias.
    assert tamanhos == [2, 3, 3]


# ---------------------------------------------------------------------------
# 2. Sanidade do gerador: senha-alvo no último índice recalcula o hash.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "charset,comprimento",
    [("ab", 3), ("abc", 4), ("abcdefghijklmnopqrstuvwxyz0123456789", 3)],
)
def test_senha_alvo_esta_no_ultimo_indice_e_recalcula_hash(charset, comprimento):
    espaco = EspacoDeBusca(charset=charset, comprimento=comprimento)
    ultimo = espaco.tamanho_total() - 1

    senha = espaco.senha_alvo()
    # É de fato o candidato do último índice...
    assert senha == espaco.indice_para_candidato(ultimo)
    # ...e é o último símbolo do charset repetido (pior caso).
    assert senha == charset[-1] * comprimento

    # Checagem de sanidade: recalcular o hash da senha reproduz o alvo.
    hash_alvo = hash_de(senha)
    assert hash_de(espaco.senha_alvo()) == hash_alvo


# ---------------------------------------------------------------------------
# Consistência entre acesso aleatório e varredura incremental.
# ---------------------------------------------------------------------------
def test_gerar_intervalo_bate_com_indice_para_candidato():
    espaco = EspacoDeBusca(charset="abc", comprimento=3)
    total = espaco.tamanho_total()
    por_intervalo = list(espaco.gerar_intervalo(0, total))
    por_indice = [espaco.indice_para_candidato(i) for i in range(total)]
    assert por_intervalo == por_indice


def test_gerar_intervalo_parcial():
    espaco = EspacoDeBusca(charset="abc", comprimento=3)
    trecho = list(espaco.gerar_intervalo(5, 9))
    assert trecho == [espaco.indice_para_candidato(i) for i in range(5, 9)]


def test_primeiro_candidato_e_o_primeiro_simbolo_repetido():
    espaco = EspacoDeBusca(charset="xyz", comprimento=4)
    assert espaco.indice_para_candidato(0) == "xxxx"


# ---------------------------------------------------------------------------
# Validações de entrada.
# ---------------------------------------------------------------------------
def test_charset_com_repetidos_e_rejeitado():
    with pytest.raises(ValueError):
        EspacoDeBusca(charset="aab", comprimento=2)


def test_comprimento_invalido_e_rejeitado():
    with pytest.raises(ValueError):
        EspacoDeBusca(charset="abc", comprimento=0)


def test_indice_fora_do_intervalo():
    espaco = EspacoDeBusca(charset="ab", comprimento=2)
    with pytest.raises(IndexError):
        espaco.indice_para_candidato(espaco.tamanho_total())
