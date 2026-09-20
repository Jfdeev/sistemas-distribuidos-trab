"""Mede o tempo de parede das versões sequencial e paralela.

Roda ``cracker_seq.py`` uma vez (repetido) e ``cracker_par.py`` para cada
N em ``--processos-lista`` (padrão 1,2,4,8), cada configuração pelo menos
``--repeticoes`` vezes (padrão 2), calcula a média e grava um CSV com as
colunas: ``configuracao, n_processos, tempo_medio_s, candidatos_totais``.

Cada execução é um subprocesso separado, e o tempo de parede é medido
externamente com ``time.perf_counter()`` — é o tempo real de ponta a ponta
do processo. Para espaços grandes (o caso de interesse), o custo de subir o
interpretador é desprezível frente ao tempo de varredura.

Uso:
    python scripts/benchmark.py [--comprimento N] [--charset ...]
                                [--processos-lista 1,2,4,8]
                                [--repeticoes 2] [--saida resultados.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import time
from statistics import mean

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from comum.config import PREFIXO_JSON  # noqa: E402


def _extrair_json(saida: str) -> dict:
    """Localiza e decodifica a linha RESULTADO_JSON emitida pelo quebrador."""
    for linha in saida.splitlines():
        if linha.startswith(PREFIXO_JSON):
            return json.loads(linha[len(PREFIXO_JSON):])
    raise RuntimeError("linha RESULTADO_JSON não encontrada na saída do processo")


def _rodar_uma_vez(comando: list[str]) -> tuple[float, dict]:
    """Executa um comando, cronometrando o tempo de parede."""
    inicio = time.perf_counter()
    proc = subprocess.run(
        comando,
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    tempo_parede = time.perf_counter() - inicio
    if proc.returncode != 0:
        raise RuntimeError(
            f"processo falhou (código {proc.returncode}):\n{proc.stderr}"
        )
    return tempo_parede, _extrair_json(proc.stdout)


def _media_de(comando: list[str], repeticoes: int, rotulo: str) -> tuple[float, dict]:
    """Roda o mesmo comando várias vezes e devolve (tempo médio, último resumo)."""
    tempos: list[float] = []
    ultimo_resumo: dict = {}
    for i in range(1, repeticoes + 1):
        tempo, resumo = _rodar_uma_vez(comando)
        ultimo_resumo = resumo
        tempos.append(tempo)
        print(f"  {rotulo} — execução {i}/{repeticoes}: {tempo:.3f} s")
    media = mean(tempos)
    print(f"  {rotulo} — média: {media:.3f} s")
    return media, ultimo_resumo


def _args_espaco(args: argparse.Namespace) -> list[str]:
    return ["--comprimento", str(args.comprimento), "--charset", args.charset]


def executar(args: argparse.Namespace) -> list[dict]:
    py = sys.executable
    linhas: list[dict] = []

    print(">> Sequencial")
    cmd_seq = [py, "sequencial/cracker_seq.py", *_args_espaco(args)]
    media_seq, resumo_seq = _media_de(cmd_seq, args.repeticoes, "sequencial")
    linhas.append(
        {
            "configuracao": "sequencial",
            "n_processos": 1,
            "tempo_medio_s": round(media_seq, 4),
            "candidatos_totais": resumo_seq["total_candidatos"],
        }
    )

    for n in args.processos_lista:
        print(f">> Paralelo com {n} processo(s)")
        cmd_par = [
            py,
            "paralelo/cracker_par.py",
            "--processos",
            str(n),
            *_args_espaco(args),
        ]
        media_par, resumo_par = _media_de(cmd_par, args.repeticoes, f"paralelo_{n}")
        linhas.append(
            {
                "configuracao": f"paralelo_{n}",
                "n_processos": n,
                "tempo_medio_s": round(media_par, 4),
                "candidatos_totais": resumo_par["total_candidatos"],
            }
        )

    return linhas


def salvar_csv(linhas: list[dict], caminho: pathlib.Path) -> None:
    campos = ["configuracao", "n_processos", "tempo_medio_s", "candidatos_totais"]
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)
    print(f"\nCSV salvo em: {caminho}")


def _lista_de_inteiros(texto: str) -> list[int]:
    return [int(parte) for parte in texto.split(",") if parte.strip()]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark sequencial vs paralelo.")
    parser.add_argument("--comprimento", type=int, default=5)
    parser.add_argument("--charset", type=str, default="abcdefghijklmnopqrstuvwxyz0123456789")
    parser.add_argument(
        "--processos-lista",
        type=_lista_de_inteiros,
        default=[1, 2, 4, 8],
        help="Lista de nº de processos, separada por vírgula (padrão: 1,2,4,8).",
    )
    parser.add_argument("--repeticoes", type=int, default=2)
    parser.add_argument(
        "--saida",
        type=pathlib.Path,
        default=RAIZ / "resultados.csv",
    )
    args = parser.parse_args(argv)

    print(
        f"vCPUs detectadas: {os.cpu_count()} | "
        f"comprimento={args.comprimento} | charset={args.charset!r}\n"
    )
    linhas = executar(args)
    salvar_csv(linhas, args.saida)


if __name__ == "__main__":
    main()
