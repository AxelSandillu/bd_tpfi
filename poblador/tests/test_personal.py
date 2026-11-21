"""Test cases para el issue #10: Personal y especialidades.

Verifica:
- 300 personal: 100 médicos + 200 enfermeros.
- Matrículas únicas que cumplen regex del dominio Matricula.
- Teléfono y email válidos, únicos.
- Nacimiento anterior a hoy, edad entre 22 y 65.
- 15 especialidades del JSON.
- Reproducibilidad con la misma semilla.
"""

from datetime import date
from unittest import mock

import pytest

from generadores.personal import (
    _fecha_nacimiento_personal,
    generar_especialidades,
    generar_personal,
)


# ---------------------------------------------------------------------------
# Fixtures y mocks
# ---------------------------------------------------------------------------

PERSONAS_API_MOCK = [
    {
        "nombre": "Juan",
        "apellido": "Pérez",
        "nacimiento": "1985-03-15T00:00:00.000Z",
        "nat": "es",
    },
    {
        "nombre": "María",
        "apellido": "González",
        "nacimiento": "1990-07-22T00:00:00.000Z",
        "nat": "mx",
    },
    {
        "nombre": "Carlos",
        "apellido": "Silva",
        "nacimiento": "1975-11-10T00:00:00.000Z",
        "nat": "br",
    },
]


@pytest.fixture
def mocked_obtener_personas():
    with mock.patch(
        "generadores.personal.obtener_personas",
        return_value=list(PERSONAS_API_MOCK),
    ):
        yield


@pytest.fixture(autouse=True)
def reset_registro_identificadores():
    from generadores.identificadores import RegistroIdentificadores
    RegistroIdentificadores().reset()
    yield
    RegistroIdentificadores().reset()


# ---------------------------------------------------------------------------
# Test: generar_personal completo
# ---------------------------------------------------------------------------

def test_generar_personal_devuelve_300(mocked_obtener_personas):
    personal = generar_personal()
    assert len(personal) == 300


def test_personal_100_medicos_200_enfermeros(mocked_obtener_personas):
    personal = generar_personal()
    medicos = [p for p in personal if p["rol"] == "Médico"]
    enfermeros = [p for p in personal if p["rol"] == "Enfermero"]
    assert len(medicos) == 100
    assert len(enfermeros) == 200


def test_personal_matriculas_unicas(mocked_obtener_personas):
    personal = generar_personal()
    matriculas = [p["matricula"] for p in personal]
    assert len(matriculas) == len(set(matriculas)), "Matrículas deben ser únicas"


def test_personal_matricula_cumple_regex(mocked_obtener_personas):
    import re
    regex = re.compile(r"^[0-9]{2}[1-5][0-9]+$")
    personal = generar_personal()
    for p in personal:
        assert regex.match(p["matricula"]), f"Matrícula inválida: {p['matricula']}"


def test_personal_matricula_empieza_con_54(mocked_obtener_personas):
    """País argentino = 54 (SISA_PAIS)."""
    personal = generar_personal()
    for p in personal:
        assert p["matricula"].startswith("54"), (
            f"Matrícula debe empezar con 54: {p['matricula']}"
        )


def test_personal_telefonos_unicos(mocked_obtener_personas):
    personal = generar_personal()
    telefonos = [p["telefono"] for p in personal]
    assert len(telefonos) == len(set(telefonos)), "Teléfonos deben ser únicos"


def test_personal_telefono_formato(mocked_obtener_personas):
    import re
    regex = re.compile(r"^\+?[0-9\s\-\(\)]{7,15}$")
    personal = generar_personal()
    for p in personal:
        assert regex.match(p["telefono"]), f"Teléfono inválido: {p['telefono']}"
        assert len(p["telefono"]) <= 30, f"Teléfono excede 30 chars: {p['telefono']}"


def test_personal_emails_unicos(mocked_obtener_personas):
    personal = generar_personal()
    emails = [p["email"] for p in personal]
    assert len(emails) == len(set(emails)), "Emails deben ser únicos"


def test_personal_email_formato(mocked_obtener_personas):
    import re
    regex = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    personal = generar_personal()
    for p in personal:
        assert regex.match(p["email"]), f"Email inválido: {p['email']}"
        assert len(p["email"]) <= 30, f"Email excede 30 chars: {p['email']}"


def test_personal_nombres_y_apellidos(mocked_obtener_personas):
    personal = generar_personal()
    for p in personal:
        assert p["nombre"], "Nombre no puede estar vacío"
        assert p["apellido"], "Apellido no puede estar vacío"


def test_personal_nacimiento_anterior_a_hoy(mocked_obtener_personas):
    personal = generar_personal()
    hoy = date.today()
    for p in personal:
        fecha = date.fromisoformat(p["nacimiento"][:10])
        assert fecha < hoy, f"Nacimiento no es anterior a hoy: {p['nacimiento']}"


def test_personal_edad_entre_22_y_65(mocked_obtener_personas):
    personal = generar_personal()
    hoy = date.today()
    for p in personal:
        fecha = date.fromisoformat(p["nacimiento"][:10])
        edad = hoy.year - fecha.year
        if (hoy.month, hoy.day) < (fecha.month, fecha.day):
            edad -= 1
        assert 22 <= edad <= 65, f"Edad fuera de rango (22-65): {edad}"


# ---------------------------------------------------------------------------
# Test: especialidades del JSON
# ---------------------------------------------------------------------------

def test_generar_especialidades_devuelve_15():
    especialidades = generar_especialidades()
    assert len(especialidades) == 15


def test_especialidades_tienen_nombre():
    especialidades = generar_especialidades()
    for e in especialidades:
        assert "nombre" in e
        assert e["nombre"], "Nombre de especialidad no puede estar vacío"


def test_especialidades_max_30_caracteres():
    especialidades = generar_especialidades()
    for e in especialidades:
        assert len(e["nombre"]) <= 30, (
            f"Especialidad excede 30 caracteres: '{e['nombre']}'"
        )


def test_especialidades_nombres_unicos():
    especialidades = generar_especialidades()
    nombres = [e["nombre"] for e in especialidades]
    assert len(nombres) == len(set(nombres)), "Nombres de especialidad deben ser únicos"


# ---------------------------------------------------------------------------
# Test: utilidad de fecha de nacimiento
# ---------------------------------------------------------------------------

def test_fecha_nacimiento_personal_rango_edad():
    import random
    rng = random.Random(42)
    fecha = _fecha_nacimiento_personal(rng)
    hoy = date.today()
    edad = hoy.year - fecha.year
    if (hoy.month, hoy.day) < (fecha.month, fecha.day):
        edad -= 1
    assert 22 <= edad <= 65, f"Edad fuera de rango: {edad}"
    assert fecha < hoy


# ---------------------------------------------------------------------------
# Test: reproducibilidad
# ---------------------------------------------------------------------------

def test_misma_seed_genera_mismo_resultado(mocked_obtener_personas):
    personal_a = generar_personal()
    personal_b = generar_personal()
    assert personal_a == personal_b
