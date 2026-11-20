"""Test cases para el issue #8: Geografía y centros de salud.

Verifica:
- 15 departamentos de Entre Ríos.
- 15 ciudades (una por departamento) con FK resueltas.
- 20 barrios con nombres únicos a nivel global.
- 20 centros de salud (uno por barrio) con FK resueltas.
- direccion <= 30 caracteres y inaguracion anterior a hoy.
- Reproducibilidad con la misma semilla.
- Uso de fallback offline (sin red).
"""

from datetime import date
from unittest import mock

import pytest

from generadores.geografia import (
    _nombre_barrio_unico,
    generar_geografia,
)

# ---------------------------------------------------------------------------
# Fixture de datos offline (fallback) para no depender de red
# ---------------------------------------------------------------------------

FALLBACK_DEPARTAMENTOS = [
    {"id": 3001, "nombre": "Paraná"},
    {"id": 3002, "nombre": "Concordia"},
    {"id": 3003, "nombre": "Concepción del Uruguay"},
    {"id": 3004, "nombre": "Gualeguaychú"},
    {"id": 3005, "nombre": "Colón"},
    {"id": 3006, "nombre": "Gualeguay"},
    {"id": 3007, "nombre": "Federación"},
    {"id": 3008, "nombre": "Federal"},
    {"id": 3009, "nombre": "La Paz"},
    {"id": 3010, "nombre": "Villaguay"},
    {"id": 3011, "nombre": "Uruguay"},
    {"id": 3012, "nombre": "Tala"},
    {"id": 3013, "nombre": "Feliciano"},
    {"id": 3014, "nombre": "San Salvador"},
    {"id": 3015, "nombre": "Diamante"},
]

FALLBACK_LOCALIDADES = {
    3001: [{"id": 30001, "nombre": "Paraná", "id_departamento": 3001}],
    3002: [{"id": 30002, "nombre": "Concordia", "id_departamento": 3002}],
    3003: [{"id": 30003, "nombre": "Concepción del Uruguay", "id_departamento": 3003}],
    3004: [{"id": 30004, "nombre": "Gualeguaychú", "id_departamento": 3004}],
    3005: [{"id": 30005, "nombre": "Colón", "id_departamento": 3005}],
    3006: [{"id": 30006, "nombre": "Gualeguay", "id_departamento": 3006}],
    3007: [{"id": 30007, "nombre": "Federación", "id_departamento": 3007}],
    3008: [{"id": 30008, "nombre": "Federal", "id_departamento": 3008}],
    3009: [{"id": 30009, "nombre": "La Paz", "id_departamento": 3009}],
    3010: [{"id": 30010, "nombre": "Villaguay", "id_departamento": 3010}],
    3011: [{"id": 30011, "nombre": "Basavilbaso", "id_departamento": 3011}],
    3012: [{"id": 30012, "nombre": "Tala", "id_departamento": 3012}],
    3013: [{"id": 30013, "nombre": "Feliciano", "id_departamento": 3013}],
    3014: [{"id": 30014, "nombre": "San Salvador", "id_departamento": 3014}],
    3015: [{"id": 30015, "nombre": "Diamante", "id_departamento": 3015}],
}

FALLBACK_CALLES = {
    3001: [{"id": 1, "nombre": "San Martín", "id_departamento": 3001, "id_localidad": 30001}],
    3002: [{"id": 4, "nombre": "25 de Mayo", "id_departamento": 3002, "id_localidad": 30002}],
    3003: [{"id": 6, "nombre": "Urquiza", "id_departamento": 3003, "id_localidad": 30003}],
    3004: [{"id": 8, "nombre": "Belgrano", "id_departamento": 3004, "id_localidad": 30004}],
    3005: [{"id": 10, "nombre": "San Martín", "id_departamento": 3005, "id_localidad": 30005}],
    3006: [{"id": 11, "nombre": "Rivadavia", "id_departamento": 3006, "id_localidad": 30006}],
    3007: [{"id": 12, "nombre": "Mitre", "id_departamento": 3007, "id_localidad": 30007}],
    3008: [{"id": 13, "nombre": "Belgrano", "id_departamento": 3008, "id_localidad": 30008}],
    3009: [{"id": 14, "nombre": "Laprida", "id_departamento": 3009, "id_localidad": 30009}],
    3010: [{"id": 15, "nombre": "San Martín", "id_departamento": 3010, "id_localidad": 30010}],
    3011: [{"id": 16, "nombre": "Urquiza", "id_departamento": 3011, "id_localidad": 30011}],
    3012: [{"id": 17, "nombre": "Rivadavia", "id_departamento": 3012, "id_localidad": 30012}],
    3013: [{"id": 18, "nombre": "Mitre", "id_departamento": 3013, "id_localidad": 30013}],
    3014: [{"id": 19, "nombre": "Belgrano", "id_departamento": 3014, "id_localidad": 30014}],
    3015: [{"id": 20, "nombre": "San Martín", "id_departamento": 3015, "id_localidad": 30015}],
}

FALLBACK_BARRIOS = [
    {"nombre": "Centro", "lat": -31.7325, "lon": -60.5236},
    {"nombre": "San Martín", "lat": -31.7400, "lon": -60.5300},
    {"nombre": "San Miguel", "lat": -31.7300, "lon": -60.5200},
    {"nombre": "San Benito", "lat": -31.7450, "lon": -60.5150},
    {"nombre": "La Floresta", "lat": -31.7500, "lon": -60.5100},
    {"nombre": "Centro", "lat": -31.3960, "lon": -58.0190},
    {"nombre": "San Carlos", "lat": -31.3900, "lon": -58.0250},
    {"nombre": "La Bianca", "lat": -31.4000, "lon": -58.0100},
    {"nombre": "Centro", "lat": -32.4870, "lon": -58.2310},
    {"nombre": "San José", "lat": -32.4800, "lon": -58.2400},
    {"nombre": "Centro", "lat": -33.1360, "lon": -58.5160},
    {"nombre": "San Martín", "lat": -33.1300, "lon": -58.5200},
    {"nombre": "Centro", "lat": -32.2270, "lon": -58.1350},
    {"nombre": "Centro", "lat": -33.1430, "lon": -58.7130},
    {"nombre": "Centro", "lat": -31.8500, "lon": -59.7800},
    {"nombre": "Norte", "lat": -31.7300, "lon": -60.5200},
    {"nombre": "Sur", "lat": -31.7400, "lon": -60.5300},
    {"nombre": "Este", "lat": -31.7350, "lon": -60.5250},
    {"nombre": "Oeste", "lat": -31.7450, "lon": -60.5150},
]


# ---------------------------------------------------------------------------
# Mocks de fuentes (evitan llamadas de red)
# ---------------------------------------------------------------------------

def _mock_departamentos():
    return list(FALLBACK_DEPARTAMENTOS)


def _mock_localidades(id_departamento):
    return list(FALLBACK_LOCALIDADES.get(id_departamento, []))


def _mock_calles(id_departamento, id_localidad=None):
    return [c for c in FALLBACK_CALLES.get(id_departamento, [])
            if id_localidad is None or c.get("id_localidad") == id_localidad]


def _mock_barrios():
    return list(FALLBACK_BARRIOS)


@pytest.fixture
def mocked_fuentes():
    """Parchea las funciones de fuentes de generadores.geografia para usar datos offline."""
    with mock.patch("generadores.geografia.obtener_departamentos", side_effect=_mock_departamentos), \
         mock.patch("generadores.geografia.obtener_localidades", side_effect=_mock_localidades), \
         mock.patch("generadores.geografia.obtener_calles", side_effect=_mock_calles), \
         mock.patch("generadores.geografia.obtener_barrios", side_effect=_mock_barrios):
        yield


# ---------------------------------------------------------------------------
# Test: generar_geografia completo
# ---------------------------------------------------------------------------

def test_generar_geografia_devuelve_15_departamentos(mocked_fuentes):
    datos = generar_geografia(seed=42)
    assert len(datos["departamento"]) == 15


def test_generar_geografia_devuelve_15_ciudades(mocked_fuentes):
    datos = generar_geografia(seed=42)
    assert len(datos["ciudad"]) == 15


def test_generar_geografia_devuelve_20_barrios(mocked_fuentes):
    datos = generar_geografia(seed=42)
    assert len(datos["barrio"]) == 20


def test_generar_geografia_devuelve_20_centros(mocked_fuentes):
    datos = generar_geografia(seed=42)
    assert len(datos["centro_de_salud"]) == 20


def test_departamentos_tienen_ids_secuenciales(mocked_fuentes):
    datos = generar_geografia(seed=42)
    ids = [d["id"] for d in datos["departamento"]]
    assert ids == list(range(1, 16))


def test_ciudades_tienen_fk_a_departamentos(mocked_fuentes):
    datos = generar_geografia(seed=42)
    depto_ids = {d["id"] for d in datos["departamento"]}
    for c in datos["ciudad"]:
        assert c["id_departamento"] in depto_ids


def test_barrios_tienen_fk_a_ciudades(mocked_fuentes):
    datos = generar_geografia(seed=42)
    ciudad_ids = {c["id"] for c in datos["ciudad"]}
    for b in datos["barrio"]:
        assert b["id_ciudad"] in ciudad_ids


def test_centros_tienen_fk_a_barrios(mocked_fuentes):
    datos = generar_geografia(seed=42)
    barrio_ids = {b["id"] for b in datos["barrio"]}
    for c in datos["centro_de_salud"]:
        assert c["id_barrio"] in barrio_ids


# ---------------------------------------------------------------------------
# Test: nombres únicos de barrios a nivel global
# ---------------------------------------------------------------------------

def test_barrios_tienen_nombres_unicos_globalmente(mocked_fuentes):
    datos = generar_geografia(seed=42)
    nombres = [b["nombre"] for b in datos["barrio"]]
    assert len(nombres) == len(set(nombres)), "Los nombres de barrio deben ser únicos globalmente"


def test_barrio_nombre_respeta_limite_30_caracteres(mocked_fuentes):
    datos = generar_geografia(seed=42)
    for b in datos["barrio"]:
        assert len(b["nombre"]) <= 30, f"Barrio excede 30 caracteres: '{b['nombre']}'"


# ---------------------------------------------------------------------------
# Test: centros de salud
# ---------------------------------------------------------------------------

def test_centro_de_salud_direccion_max_30(mocked_fuentes):
    datos = generar_geografia(seed=42)
    for c in datos["centro_de_salud"]:
        assert len(c["direccion"]) <= 30, f"Dirección excede 30 caracteres: '{c['direccion']}'"


def test_centro_de_salud_inaguracion_anterior_a_hoy(mocked_fuentes):
    datos = generar_geografia(seed=42)
    hoy = date.today()
    for c in datos["centro_de_salud"]:
        fecha = date.fromisoformat(c["inaguracion"])
        assert fecha < hoy, f"Inauguración no es anterior a hoy: {c['inaguracion']}"


def test_centro_de_salud_uno_por_barrio(mocked_fuentes):
    datos = generar_geografia(seed=42)
    barrio_ids_usados = {c["id_barrio"] for c in datos["centro_de_salud"]}
    assert len(barrio_ids_usados) == 20, "Cada centro debe pertenecer a un barrio distinto"
    assert len(datos["centro_de_salud"]) == 20


# ---------------------------------------------------------------------------
# Test: reproducibilidad
# ---------------------------------------------------------------------------

def test_misma_seed_genera_mismo_resultado(mocked_fuentes):
    datos_a = generar_geografia(seed=42)
    datos_b = generar_geografia(seed=42)
    assert datos_a == datos_b


def test_distinta_seed_genera_resultado_distinto(mocked_fuentes):
    datos_a = generar_geografia(seed=42)
    datos_b = generar_geografia(seed=99)
    assert datos_a != datos_b


# ---------------------------------------------------------------------------
# Test: _nombre_barrio_unico (utilidad)
# ---------------------------------------------------------------------------

def test_nombre_barrio_unico_no_repite_si_no_existe():
    usados = {"Centro", "San Martín"}
    resultado = _nombre_barrio_unico("La Floresta", "Paraná", usados)
    assert resultado == "La Floresta"


def test_nombre_barrio_unico_califica_con_ciudad_si_repite():
    usados = {"Centro"}
    resultado = _nombre_barrio_unico("Centro", "Paraná", usados)
    assert resultado != "Centro"
    assert "Centro" in resultado
    assert "Paraná" in resultado
    assert len(resultado) <= 30


def test_nombre_barrio_unico_sufijo_numerico_si_necesario():
    usados = {"Centro", "Centro Paraná"}
    resultado = _nombre_barrio_unico("Centro", "Paraná", usados)
    assert resultado.startswith("Centro ")
    assert resultado not in usados
    assert len(resultado) <= 30


# ---------------------------------------------------------------------------
# Test: exclusión de departamentos (config.DEPARTAMENTOS_EXCLUIDOS)
# ---------------------------------------------------------------------------

def test_departamentos_excluidos_respetados(mocked_fuentes):
    from config import DEPARTAMENTOS_EXCLUIDOS
    originales = list(DEPARTAMENTOS_EXCLUIDOS)
    try:
        DEPARTAMENTOS_EXCLUIDOS.clear()
        DEPARTAMENTOS_EXCLUIDOS.append("Paraná")
        datos = generar_geografia(seed=42)
        nombres = {d["nombre"] for d in datos["departamento"]}
        assert "Paraná" not in nombres
        assert len(datos["departamento"]) <= 15
    finally:
        DEPARTAMENTOS_EXCLUIDOS.clear()
        DEPARTAMENTOS_EXCLUIDOS.extend(originales)
