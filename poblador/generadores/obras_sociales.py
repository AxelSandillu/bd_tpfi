"""Generador de obras sociales.

Genera 50 obras sociales con IDs secuenciales, razon_social desde
config.OBRAS_SOCIALES y estado BOOLEAN (~10% inactivas).

Toda la configuración vive en config.py (OBRAS_SOCIALES, PCT_OBRAS_SOCIALES_INACTIVAS).
"""

import random

from config import PCT_OBRAS_SOCIALES_INACTIVAS, TOTALES
from fuentes.catalogos import obras_sociales


def generar_obras_sociales(rng: random.Random) -> list[dict]:
    """Devuelve 50 obras sociales (IDs 1..50).

    Las últimas N (según PCT_OBRAS_SOCIALES_INACTIVAS) se marcan como
    inactivas (estado=false) de forma determinista con la semilla.
    """
    cantidad = TOTALES["obra_social"]
    nombres = obras_sociales()[:cantidad]

    n_inactivas = int(round(cantidad * PCT_OBRAS_SOCIALES_INACTIVAS))

    resultado: list[dict] = []
    for i, nombre in enumerate(nombres, start=1):
        # Las últimas n_inactivas son inactivas (estado=false), el resto activas.
        estado = i <= (cantidad - n_inactivas)
        resultado.append({
            "id": i,
            "razon_social": nombre,
            "estado": estado,
        })

    return resultado
