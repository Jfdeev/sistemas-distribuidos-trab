"""Gera o gráfico de speedup medido vs. teto teórico da Lei de Amdahl.

Lê ``resultados.csv`` (produzido por ``benchmark.py``), calcula
``speedup(N) = tempo_sequencial / tempo_paralelo(N)`` e plota os pontos
medidos sobre a curva teórica de Amdahl.

Uso:
    python scripts/plot_speedup.py [--csv resultados.csv] [--saida grafico_speedup.png]
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

# ---------------------------------------------------------------------------
# Fração paralelizável estimada do programa (o "P" da Lei de Amdahl).
#
# COMO FOI ESTIMADA: a varredura do espaço de busca é quase inteiramente
# paralelizável — cada processo trata uma fatia independente. A parte serial
# residual vem de: criar/juntar processos, iniciar o Manager, particionar o
# espaço e agregar o resumo final. Medimos empiricamente essa fração pela
# métrica de Karp-Flatt a partir dos próprios dados (ver `karp_flatt` abaixo)
# e arredondamos para o valor constante usado na curva teórica.
#
# Ajuste este valor com o P médio impresso pelo script após rodar com seus
# números reais de nuvem.
# ---------------------------------------------------------------------------
FRACAO_PARALELIZAVEL = 0.97


def amdahl(p: float, n: int) -> float:
    """Speedup teórico máximo com fração paralelizável ``p`` e ``n`` núcleos."""
    return 1.0 / ((1.0 - p) + p / n)


def karp_flatt(speedup: float, n: int) -> float | None:
    """Fração serial empírica ``e`` pela métrica de Karp-Flatt.

    e = (1/S - 1/N) / (1 - 1/N).  A fração paralelizável é ``1 - e``.
    Retorna None para n == 1 (indefinido).
    """
    if n == 1:
        return None
    return (1.0 / speedup - 1.0 / n) / (1.0 - 1.0 / n)


def ler_resultados(caminho: pathlib.Path) -> dict[int, float]:
    """Lê o CSV e devolve {n_processos: tempo_medio_s} apenas do paralelo,
    além de registrar o tempo sequencial sob a chave 0."""
    tempos: dict[int, float] = {}
    with caminho.open(encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            n = int(linha["n_processos"])
            tempo = float(linha["tempo_medio_s"])
            if linha["configuracao"] == "sequencial":
                tempos[0] = tempo  # chave 0 = tempo sequencial de referência
            else:
                tempos[n] = tempo
    if 0 not in tempos:
        raise RuntimeError("linha 'sequencial' ausente no CSV")
    return tempos


def gerar_grafico(tempos: dict[int, float], saida: pathlib.Path) -> None:
    import matplotlib

    matplotlib.use("Agg")  # backend sem interface gráfica, para salvar arquivo
    import matplotlib.pyplot as plt

    tempo_seq = tempos[0]
    ns = sorted(n for n in tempos if n != 0)
    speedups = [tempo_seq / tempos[n] for n in ns]

    # Fração serial média medida (Karp-Flatt) — informativa para o relatório.
    es = [karp_flatt(s, n) for s, n in zip(speedups, ns) if n != 1]
    if es:
        e_medio = sum(es) / len(es)
        print(f"Fração serial média medida (Karp-Flatt): {e_medio:.4f}")
        print(f"=> Fração paralelizável medida ~ {1 - e_medio:.4f}")
    print(f"Constante FRACAO_PARALELIZAVEL usada na curva: {FRACAO_PARALELIZAVEL}")

    curva_ns = list(range(1, max(ns) + 1))
    curva_amdahl = [amdahl(FRACAO_PARALELIZAVEL, n) for n in curva_ns]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(curva_ns, curva_amdahl, "--", color="#888",
            label=f"Amdahl (P={FRACAO_PARALELIZAVEL})")
    ax.plot(ns, ns, ":", color="#ccc", label="Speedup ideal (linear)")
    ax.plot(ns, speedups, "o-", color="#2563eb", label="Speedup medido")

    ax.set_xlabel("Número de processos (N)")
    ax.set_ylabel("Speedup (Tseq / Tpar)")
    ax.set_title("Speedup medido vs. Lei de Amdahl")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(saida, dpi=120)
    print(f"Gráfico salvo em: {saida}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Plota speedup vs. Amdahl.")
    parser.add_argument("--csv", type=pathlib.Path, default=RAIZ / "resultados.csv")
    parser.add_argument("--saida", type=pathlib.Path, default=RAIZ / "grafico_speedup.png")
    args = parser.parse_args(argv)

    tempos = ler_resultados(args.csv)
    gerar_grafico(tempos, args.saida)


if __name__ == "__main__":
    main()
