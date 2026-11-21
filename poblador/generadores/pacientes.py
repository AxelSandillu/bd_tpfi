"""Generador de pacientes.

Genera 400 pacientes con:

- Nombres de randomuser.me (con cache, funciona offline).
- ~15% pediátricos: nombre/apellido de la API, fecha de nacimiento generada
  localmente (niños de 0 a 17 años).
- ~25% sin obra social (id_obra_social y num_asociado NULL).
- Casi ninguno con obra social inactiva (solo un 5% de los que tienen OS).
- DNI único correlacionado con el año de nacimiento (registro global).
- Nacimiento estrictamente anterior a hoy.

Depende de:
  - fuentes.randomuser (issue #4) para nombres y fechas de adultos.
  - generadores.identificadores (issue #7) para DNI y num_asociado únicos.
  - config.py para todos los porcentajes y cantidades.
"""

import random
from datetime import date, timedelta

from config import (
    FECHA_REFERENCIA,
    PCT_PACIENTES_PEDIATRICOS,
    PCT_PACIENTES_SIN_OBRA_SOCIAL,
    SEED,
    TOTALES,
)
from fuentes.randomuser import obtener_personas
from generadores.identificadores import RegistroIdentificadores


def _hoy() -> date:
    """Fecha de referencia (config.FECHA_REFERENCIA o hoy real)."""
    if FECHA_REFERENCIA is not None:
        return FECHA_REFERENCIA
    return date.today()


def _fecha_nacimiento_pediatrico(rng: random.Random) -> date:
    """Fecha de nacimiento para un paciente pediátrico (0-17 años, anterior a hoy)."""
    hoy = _hoy()
    inicio = date(hoy.year - 17, 1, 1)
    fin = hoy - timedelta(days=1)
    dias = (fin - inicio).days
    return inicio + timedelta(days=rng.randint(0, dias))


def _fecha_nacimiento_adulto(persona: dict, rng: random.Random) -> date:
    """Fecha de nacimiento de un adulto desde la API, asegurando < hoy."""
    hoy = _hoy()
    nacimiento = date.fromisoformat(persona["nacimiento"][:10])
    if nacimiento >= hoy:
        # Fallback: un día antes de hoy (no debería ocurrir con la API)
        nacimiento = hoy - timedelta(days=1)
    return nacimiento


def generar_pacientes(
    obras_sociales_lista: list[dict],
    rng: random.Random | None = None,
) -> list[dict]:
    """Devuelve 400 pacientes.

    Args:
        obras_sociales_lista: salida de generar_obras_sociales() (para FK).
        rng: generador aleatorio (si None, se usa config.SEED).
    """
    if rng is None:
        rng = random.Random(SEED)

    # Resetear el registro global para garantizar reproducibilidad
    # (el singleton persiste estado entre llamadas).
    registro = RegistroIdentificadores()
    registro.reset()

    cantidad = TOTALES["paciente"]
    ids_activas = [o["id"] for o in obras_sociales_lista if o["estado"]]
    ids_inactivas = [o["id"] for o in obras_sociales_lista if not o["estado"]]

    # Personas de la API (una llamada por nacionalidad, con cache)
    personas_api = obtener_personas(cantidad)

    n_pediatricos = int(round(cantidad * PCT_PACIENTES_PEDIATRICOS))
    n_sin_obra_social = int(round(cantidad * PCT_PACIENTES_SIN_OBRA_SOCIAL))

    resultado: list[dict] = []
    for i in range(1, cantidad + 1):
        persona = personas_api[(i - 1) % len(personas_api)]

        es_pediatrico = (i - 1) < n_pediatricos
        if es_pediatrico:
            nacimiento = _fecha_nacimiento_pediatrico(rng)
        else:
            nacimiento = _fecha_nacimiento_adulto(persona, rng)

        ano_nacimiento = nacimiento.year
        dni = registro.generar_dni(ano_nacimiento, rng)

        sin_obra_social = (i - 1) < n_sin_obra_social

        if sin_obra_social:
            id_obra_social = None
            num_asociado = None
        else:
            # ~5% de los que tienen obra social reciben una inactiva
            if ids_inactivas and rng.random() < 0.05:
                id_obra_social = rng.choice(ids_inactivas)
            else:
                id_obra_social = rng.choice(ids_activas) if ids_activas else None
            num_asociado = registro.generar_num_asociado(rng)

        resultado.append({
            "dni": dni,
            "id_obra_social": id_obra_social,
            "nombre": persona["nombre"],
            "apellido": persona["apellido"],
            "nacimiento": nacimiento.isoformat(),
            "num_asociado": num_asociado,
        })

    return resultado
