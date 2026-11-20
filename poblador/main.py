"""Punto de entrada del generador de 02_seed.sql.

Define la interfaz de línea de comandos del proyecto poblador.
Al arrancar valida data/tipos_servicio.json y aborta con un mensaje claro si
el JSON es inválido, antes de generar nada.

Uso:
    python main.py --help
    python main.py --seed 42
"""

import argparse
import sys

from config import RUTA_TIPOS_SERVICIO
from validar import TiposServicioInvalido, cargar_tipos_servicio


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
    """Ejecuta la CLI del programa.

    Valida tipos_servicio.json antes de seguir. Un JSON inválido aborta el
    programa antes de generar nada y explica exactamente qué corregir.
    """
    parser = build_parser()
    parser.parse_args()

    try:
        cargar_tipos_servicio(RUTA_TIPOS_SERVICIO)
    except TiposServicioInvalido as exc:
        print(f"Error de validación: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
