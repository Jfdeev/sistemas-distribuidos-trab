"""Verificação de equivalência: a paralela produz o mesmo que a sequencial.

Roda as duas versões com a MESMA entrada e confirma que encontram a mesma
senha e testam a mesma quantidade de candidatos. É a "prova de resultado
verificável" pedida na lauda — ótimo para mostrar na apresentação.

Uso:
    python scripts/verificar.py [--comprimento N] [--charset ...] [--processos N]
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from comum.config import adicionar_argumentos_espaco, espaco_e_alvo  # noqa: E402
from comum.estado import EstadoCompartilhado  # noqa: E402
from comum.keyspace import EspacoDeBusca  # noqa: E402
from comum.motor import executar_paralelo  # noqa: E402
from sequencial.cracker_seq import executar_sequencial  # noqa: E402


def verificar(espaco: EspacoDeBusca, hash_alvo: str, n_processos: int) -> dict:
    """Roda seq e par com a mesma entrada e devolve o comparativo."""
    seq = executar_sequencial(espaco, hash_alvo)
    with mp.Manager() as gerente:
        estado = EstadoCompartilhado(
            gerente,
            n_processos=n_processos,
            total_candidatos=espaco.tamanho_total(),
            hash_alvo=hash_alvo,
            charset=espaco.charset,
            comprimento=espaco.comprimento,
        )
        par = executar_paralelo(espaco, hash_alvo, n_processos, estado)

    igual = seq["senha"] == par["senha"] and seq["testados"] == par["testados"]
    return {"igual": igual, "sequencial": seq, "paralelo": par}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifica seq == par.")
    adicionar_argumentos_espaco(parser)
    parser.add_argument("--processos", type=int, default=os.cpu_count())
    args = parser.parse_args(argv)

    espaco, hash_alvo = espaco_e_alvo(args)
    resultado = verificar(espaco, hash_alvo, max(1, args.processos))
    seq, par = resultado["sequencial"], resultado["paralelo"]

    print(f"Sequencial -> senha={seq['senha']!r}  testados={seq['testados']}")
    print(f"Paralelo   -> senha={par['senha']!r}  testados={par['testados']}")
    print(
        "Contador global sob lock fechou: "
        + ("SIM" if par["contador_confere"] else "NÃO (condição de corrida!)")
    )
    if resultado["igual"]:
        print("\n[OK] RESULTADO VERIFICADO: paralela == sequencial (mesma entrada).")
        return 0
    print("\n[FALHOU] as versões divergiram!")
    return 1


if __name__ == "__main__":
    mp.freeze_support()
    sys.exit(main())
