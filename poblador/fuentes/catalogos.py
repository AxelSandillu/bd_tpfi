"""Catálogos curados: punto único de acceso a listas de referencia.

Centraliza obras sociales, nombres de centros de salud, franjas horarias y
áreas telefónicas de Entre Ríos. Valida que ningún nombre supere los 30
caracteres ni se repita en columnas UNIQUE.

Todos los datos provienen de config.py; este módulo solo los expone y los
valida, para que el resto del programa los importe desde un solo lugar.
"""

from config import (
    AREAS_TELEFONICAS,
    CENTROS_SALUD_NUMEROS,
    CENTROS_SALUD_PATRON,
    CENTROS_SALUD_ZONAS,
    FRANJAS_HORARIAS,
    OBRAS_SOCIALES,
)

LIMITE_NOMBRE = 30


class CatalogoInvalido(Exception):
    """Un catálogo curado no cumple las reglas de longitud o unicidad."""


def _validar_nombres(nombres: list[str], origen: str) -> None:
    """Verifica que cada nombre tenga <= 30 caracteres y no se repita."""
    vistos = set()
    for nombre in nombres:
        if not isinstance(nombre, str):
            raise CatalogoInvalido(
                f"{origen}: se esperaba texto, se encontró {type(nombre).__name__}"
            )
        if len(nombre) > LIMITE_NOMBRE:
            raise CatalogoInvalido(
                f"{origen}: '{nombre}' excede los {LIMITE_NOMBRE} caracteres "
                f"(tiene {len(nombre)})"
            )
        if nombre in vistos:
            raise CatalogoInvalido(f"{origen}: nombre duplicado '{nombre}'")
        vistos.add(nombre)


def obras_sociales() -> list[str]:
    """Devuelve la lista de obras sociales curadas (máx. 30 chars, sin repetir)."""
    _validar_nombres(OBRAS_SOCIALES, "obras_sociales")
    return list(OBRAS_SOCIALES)


def centros_salud(cantidad: int) -> list[str]:
    """Genera `cantidad` nombres únicos de centros de salud (máx. 30 chars).

    Combina los patrones, zonas y números de config.py sin repetir.
    """
    generados: list[str] = []
    vistos = set()

    for patron in CENTROS_SALUD_PATRON:
        for zona in CENTROS_SALUD_ZONAS:
            for numero in CENTROS_SALUD_NUMEROS:
                nombre = patron.format(zona=zona, numero=numero)
                if len(nombre) > LIMITE_NOMBRE:
                    continue
                if nombre in vistos:
                    continue
                generados.append(nombre)
                vistos.add(nombre)
                if len(generados) >= cantidad:
                    return generados

    if len(generados) < cantidad:
        raise CatalogoInvalido(
            f"centros_salud: no se pudieron generar {cantidad} nombres únicos "
            f"(solo {len(generados)} disponibles con los patrones configurados)"
        )
    return generados


def franjas_horarias() -> list[tuple[str, str]]:
    """Devuelve las franjas horarias de config.py."""
    return list(FRANJAS_HORARIAS)


def areas_telefonicas() -> dict[str, str]:
    """Devuelve las áreas telefónicas de config.py."""
    return dict(AREAS_TELEFONICAS)
