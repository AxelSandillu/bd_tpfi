"""Generador de personal y especialidades.

Genera:
- personal: 100 médicos + 200 enfermeros, todos mayores de 18, con matrícula
  SISA, teléfono y email válidos, nacimiento anterior a hoy.
- especialidad: 15 especialidades tomadas de data/tipos_servicio.json.

Deja listo el espacio para `especializado_en`, que se completa en el issue #12.

Depende de:
  - fuentes.randomuser (issue #4) para nombres y fechas de nacimiento.
  - generadores.identificadores (issue #7) para DNI, matrícula, teléfono, email.
  - config.py para todas las constantes ajustables.
  - data/tipos_servicio.json (issue #3) para las especialidades.
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path

from config import EDAD_PERSONAL, ENFERMEROS, MEDICOS, SEED, TOTALES
from fuentes.randomuser import obtener_personas
from generadores.identificadores import RegistroIdentificadores


def _hoy() -> date:
    """Fecha de referencia (config.FECHA_REFERENCIA o hoy real)."""
    from config import FECHA_REFERENCIA
    if FECHA_REFERENCIA is not None:
        return FECHA_REFERENCIA
    return date.today()


def _fecha_nacimiento_personal(rng: random.Random) -> date:
    """Fecha de nacimiento con edad entre EDAD_PERSONAL (22-65), anterior a hoy.

    Resta exactamente `edad` años a la fecha de hoy, de modo que la edad
    calculada cae siempre dentro del rango [22, 65].
    """
    hoy = _hoy()
    edad = rng.randint(EDAD_PERSONAL[0], EDAD_PERSONAL[1])
    try:
        return date(hoy.year - edad, hoy.month, hoy.day)
    except ValueError:
        # 29 de febrero en año no bisiesto -> 28 de febrero
        return date(hoy.year - edad, hoy.month, 28)


def _telefono_para_personal(rng: random.Random, registro: RegistroIdentificadores) -> str:
    """Genera teléfono usando el nombre de una ciudad de config (área telefónica)."""
    from config import AREAS_TELEFONICAS
    ciudad = rng.choice(list(AREAS_TELEFONICAS.keys()))
    return registro.generar_telefono(ciudad, rng)


def _email_para_personal(nombre: str, apellido: str, rng: random.Random,
                         registro: RegistroIdentificadores) -> str:
    """Genera email normalizado único."""
    return registro.generar_email(nombre, apellido, rng)


def generar_especialidades(ruta_json: str | None = None) -> list[dict]:
    """Carga las especialidades de data/tipos_servicio.json.

    Devuelve lista de dicts con clave 'nombre'. IDs se asignan al emitir SQL.
    """
    if ruta_json is None:
        from config import RUTA_TIPOS_SERVICIO
        ruta_json = RUTA_TIPOS_SERVICIO

    with open(ruta_json, encoding="utf-8") as f:
        datos = json.load(f)

    especialidades = datos["especialidades"]
    return [{"nombre": e} for e in especialidades]


def generar_personal(rng: random.Random | None = None) -> list[dict]:
    """Devuelve 300 personal: 100 médicos + 200 enfermeros.

    Cada fila: matricula, nombre, apellido, telefono, email, nacimiento, rol.
    """
    if rng is None:
        rng = random.Random(SEED)

    # Resetear registro global para reproducibilidad (singleton con estado).
    registro = RegistroIdentificadores()
    registro.reset()

    cantidad_total = TOTALES["personal"]
    n_medicos = MEDICOS
    n_enfermeros = ENFERMEROS

    # Personas de la API (una llamada por nacionalidad, con cache)
    personas_api = obtener_personas(cantidad_total)

    resultado: list[dict] = []
    for i in range(1, cantidad_total + 1):
        persona = personas_api[(i - 1) % len(personas_api)]

        # Rol: primero médicos, luego enfermeros
        if i <= n_medicos:
            rol = "Médico"
        else:
            rol = "Enfermero"

        nacimiento = _fecha_nacimiento_personal(rng)
        ano_nacimiento = nacimiento.year
        dni = registro.generar_dni(ano_nacimiento, rng)

        # Matrícula SISA desde el DNI (país 54, tipo 1=DNI)
        matricula = registro.generar_matricula(dni, tipo_doc=1)

        # Teléfono con área de una ciudad de config
        telefono = _telefono_para_personal(rng, registro)

        # Email normalizado único
        email = _email_para_personal(persona["nombre"], persona["apellido"], rng, registro)

        resultado.append({
            "matricula": matricula,
            "nombre": persona["nombre"],
            "apellido": persona["apellido"],
            "telefono": telefono,
            "email": email,
            "nacimiento": nacimiento.isoformat(),
            "rol": rol,
        })

    return resultado
