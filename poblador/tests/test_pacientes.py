"""Test cases para el issue #9: Pacientes.

Verifica:
- 400 pacientes generados.
- DNI únicos.
- Nombres de la API (mockeados para funcionar offline).
- ~15% pediátricos (fecha de nacimiento local, 0-17 años).
- ~25% sin obra social (id_obra_social y num_asociado NULL).
- Casi ninguno con obra social inactiva.
- Nacimiento estrictamente anterior a hoy.
- Reproducibilidad con la misma semilla.
"""

from datetime import date
from unittest import mock

import pytest

from generadores.pacientes import (
    _fecha_nacimiento_adulto,
    _fecha_nacimiento_pediatrico,
    generar_pacientes,
)


# ---------------------------------------------------------------------------
# Fixtures y mocks
# ---------------------------------------------------------------------------

OBRAS_SOCIALES_MOCK = [
    {"id": i, "razon_social": f"OS {i}", "estado": i > 45}  # 5 inactivas (46-50)
    for i in range(1, 51)
]


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
    """Mockea obtener_personas para no llamar a randomuser.me."""
    with mock.patch(
        "generadores.pacientes.obtener_personas",
        return_value=list(PERSONAS_API_MOCK),
    ):
        yield


@pytest.fixture(autouse=True)
def reset_registro_identificadores():
    """Resetea el registro de identificadores entre tests."""
    from generadores.identificadores import RegistroIdentificadores
    RegistroIdentificadores().reset()
    yield
    RegistroIdentificadores().reset()


# ---------------------------------------------------------------------------
# Test: generar_pacientes completo
# ---------------------------------------------------------------------------

def test_generar_pacientes_devuelve_400(mocked_obtener_personas):
    pacientes = generar_pacientes(OBRAS_SOCIALES_MOCK)
    assert len(pacientes) == 400


def test_pacientes_dni_unicos(mocked_obtener_personas):
    pacientes = generar_pacientes(OBRAS_SOCIALES_MOCK)
    dnis = [p["dni"] for p in pacientes]
    assert len(dnis) == len(set(dnis)), "Los DNI deben ser únicos"


def test_pacientes_nacimiento_anterior_a_hoy(mocked_obtener_personas):
    pacientes = generar_pacientes(OBRAS_SOCIALES_MOCK)
    hoy = date.today()
    for p in pacientes:
        fecha = date.fromisoformat(p["nacimiento"][:10])
        assert fecha < hoy, f"Nacimiento no es anterior a hoy: {p['nacimiento']}"


def test_pacientes_tienen_nombre_y_apellido(mocked_obtener_personas):
    pacientes = generar_pacientes(OBRAS_SOCIALES_MOCK)
    for p in pacientes:
        assert p["nombre"], "Nombre no puede estar vacío"
        assert p["apellido"], "Apellido no puede estar vacío"


# ---------------------------------------------------------------------------
# Test: pacientes sin obra social (~25%)
# ---------------------------------------------------------------------------

def test_pacientes_sin_obra_social_aproximadamente_25(mocked_obtener_personas):
    pacientes = generar_pacientes(OBRAS_SOCIALES_MOCK)
    sin_os = [p for p in pacientes if p["id_obra_social"] is None]
    # ~25% de 400 = 100. Permitir margen de 5 por redondeo.
    assert 95 <= len(sin_os) <= 105, (
        f"Esperadas ~100 sin obra social, obtuve {len(sin_os)}"
    )
    for p in sin_os:
        assert p["num_asociado"] is None, (
            "Sin obra social debe tener num_asociado NULL"
        )


def test_pacientes_con_obra_social_tienen_num_asociado(mocked_obtener_personas):
    pacientes = generar_pacientes(OBRAS_SOCIALES_MOCK)
    for p in pacientes:
        if p["id_obra_social"] is not None:
            assert p["num_asociado"] is not None, (
                "Con obra social debe tener num_asociado"
            )


def test_pacientes_num_asociado_unicos(mocked_obtener_personas):
    pacientes = generar_pacientes(OBRAS_SOCIALES_MOCK)
    numeros = [p["num_asociado"] for p in pacientes if p["num_asociado"] is not None]
    assert len(numeros) == len(set(numeros)), "num_asociado debe ser único"


# ---------------------------------------------------------------------------
# Test: obra social inactiva (casi ninguno)
# ---------------------------------------------------------------------------

def test_pacientes_casi_ninguno_con_obra_social_inactiva(mocked_obtener_personas):
    pacientes = generar_pacientes(OBRAS_SOCIALES_MOCK)
    inactivas_ids = {o["id"] for o in OBRAS_SOCIALES_MOCK if not o["estado"]}
    con_inactiva = [
        p for p in pacientes
        if p["id_obra_social"] is not None and p["id_obra_social"] in inactivas_ids
    ]
    # ~5% de los ~300 con obra social = ~15. Máximo 30 para ser "casi ninguno".
    assert len(con_inactiva) <= 30, (
        f"Demasiados pacientes con obra social inactiva: {len(con_inactiva)}"
    )


# ---------------------------------------------------------------------------
# Test: pacientes pediátricos (~15%)
# ---------------------------------------------------------------------------

def test_pacientes_pediatricos_aproximadamente_15(mocked_obtener_personas):
    pacientes = generar_pacientes(OBRAS_SOCIALES_MOCK)
    hoy = date.today()
    pediatricos = [
        p for p in pacientes
        if (hoy.year - date.fromisoformat(p["nacimiento"][:10]).year) <= 17
    ]
    # ~15% de 400 = 60. Permitir margen de 10 por aproximación.
    assert 50 <= len(pediatricos) <= 70, (
        f"Esperados ~60 pediátricos, obtuve {len(pediatricos)}"
    )


# ---------------------------------------------------------------------------
# Test: utilidades de fecha
# ---------------------------------------------------------------------------

def test_fecha_nacimiento_pediatrico_es_menor_de_18_anios():
    import random
    rng = random.Random(42)
    fecha = _fecha_nacimiento_pediatrico(rng)
    hoy = date.today()
    edad = hoy.year - fecha.year
    if (hoy.month, hoy.day) < (fecha.month, fecha.day):
        edad -= 1
    assert 0 <= edad <= 17, f"Edad pediátrica fuera de rango: {edad}"


def test_fecha_nacimiento_adulto_usa_api():
    persona = {"nacimiento": "1985-03-15T00:00:00.000Z"}
    import random
    rng = random.Random(42)
    fecha = _fecha_nacimiento_adulto(persona, rng)
    assert fecha == date(1985, 3, 15)
    assert fecha < date.today()


def test_fecha_nacimiento_adulto_respeta_limite_hoy():
    persona = {"nacimiento": "2030-01-01T00:00:00.000Z"}  # futuro
    import random
    rng = random.Random(42)
    fecha = _fecha_nacimiento_adulto(persona, rng)
    assert fecha < date.today()


# ---------------------------------------------------------------------------
# Test: reproducibilidad
# ---------------------------------------------------------------------------

def test_misma_seed_genera_mismo_resultado(mocked_obtener_personas):
    import random
    pacientes_a = generar_pacientes(OBRAS_SOCIALES_MOCK, random.Random(42))
    pacientes_b = generar_pacientes(OBRAS_SOCIALES_MOCK, random.Random(42))
    assert pacientes_a == pacientes_b


def test_distinta_seed_genera_resultado_distinto(mocked_obtener_personas):
    import random
    pacientes_a = generar_pacientes(OBRAS_SOCIALES_MOCK, random.Random(42))
    pacientes_b = generar_pacientes(OBRAS_SOCIALES_MOCK, random.Random(99))
    dnis_a = {p["dni"] for p in pacientes_a}
    dnis_b = {p["dni"] for p in pacientes_b}
    # Con semillas diferentes es muy probable que los DNIs difieran
    assert dnis_a != dnis_b
