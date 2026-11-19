"""Punto de entrada del generador de 02_seed.sql.

Define la interfaz de línea de comandos del proyecto poblador.
Por ahora solo expone --help; cada issue posterior añade su parte.

Uso:
    python main.py --help
    python main.py --seed 42
"""

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos de la CLI."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Generador de 02_seed.sql para poblar la base de salud "
            "de la provincia de Entre Ríos, Argentina."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=(
            "Semilla para reproducibilidad. "
            "Por defecto se usa el valor de config.SEED."
        ),
    )
    return parser


def main() -> None:
    """Ejecuta la CLI del programa."""
    parser = build_parser()
    parser.parse_args()


if __name__ == "__main__":
    main()
