"""Test cases para el issue #15: Internaciones.

Verifica:
- Exactamente 150 internaciones: 40 actuales y 110 pasadas.
- Registros distintos y solo de servicios con interna=true.
- fecha_ingreso igual a dia_visita del registro.
- Actuales: egreso NULL e ingreso reciente.
- Pasadas: egreso posterior al ingreso, dentro de la duración configurada y
  anterior a hoy.
- Un paciente no tiene internaciones superpuestas (a lo sumo una activa).
- Falla con PoolAgotadoError si no hay registros suficientes.
- Reproducibilidad con la misma semilla.
"""

import random
from datetime import date, timedelta

import pytest

from config import (
    DURACION_INTERNACION_DIAS,
    INTERNACION_ACTUAL_DIAS,
    INTERNACIONES_ACTUALES,
    INTERNACIONES_PASADAS,
)
from generadores.internaciones import generar_internaciones
from pools import PoolAgotadoError


# ---------------------------------------------------------------------------
# Datos sintéticos
# ---------------------------------------------------------------------------

TIPOS = [
    {"nombre": "Con internacion", "interna": True},
    {"nombre": "Sin internacion", "interna": False},
]

SERVICIOS = [
    {"id": 1, "id_centro_salud": 1, "nombre_tipo_servicio": "Con internacion"},
    {"id": 2, "id_centro_salud": 1, "nombre_tipo_servicio": "Sin internacion"},
    {"id": 3, "id_centro_salud": 2, "nombre_tipo_servicio": "Con internacion"},
]


def _hoy() -> date:
    return date.today()


def _armar_registros(
    n_recientes_internan: int = 60,
    n_pasados_internan: int = 400,
    n_no_internan: int = 100,
    n_pacientes: int = 400,
    seed: int = 1,
) -> list[dict]:
    """Registros: recientes y antiguos en servicios que internan + otros."""
    rng = random.Random(seed)
    hoy = _hoy()
    registros: list[dict] = []

    def agregar(id_servicio: int, fecha: date) -> None:
        registros.append({
            "id_servicio": id_servicio,
            "dni_paciente": 30_000_000 + rng.randrange(n_pacientes),
            "matricula_personal": "541000000001",
            "dia_visita": fecha.isoformat(),
            "diagnostico": "d",
            "tratamiento": "t",
        })

    # Recientes (últimos 20 días) en servicios que internan
    for _ in range(n_recientes_internan):
        agregar(rng.choice([1, 3]), hoy - timedelta(days=rng.randint(1, 20)))
    # Antiguos (hasta ~2 años atrás) en servicios que internan
    for _ in range(n_pasados_internan):
        agregar(rng.choice([1, 3]), hoy - timedelta(days=rng.randint(21, 700)))
    # Servicio que NO interna (recientes y antiguos)
    for _ in range(n_no_internan):
        agregar(2, hoy - timedelta(days=rng.randint(1, 700)))

    rng.shuffle(registros)
    return registros


def _generar(registros=None, seed: int = 42):
    registros = registros if registros is not None else _armar_registros()
    internaciones = generar_internaciones(
        registros_hc=registros,
        servicios=SERVICIOS,
        tipo_servicio=TIPOS,
        rng=random.Random(seed),
    )
    return registros, internaciones


def _registro_de(registros: list[dict], internacion: dict) -> dict:
    """El id de un registro es su posición (1-based) en la lista."""
    return registros[internacion["id_registro_hc"] - 1]


def _a_fecha(valor: str) -> date:
    return date.fromisoformat(valor[:10])


# ---------------------------------------------------------------------------
# Cantidades
# ---------------------------------------------------------------------------

def test_genera_150_internaciones():
    _, internaciones = _generar()
    assert len(internaciones) == INTERNACIONES_ACTUALES + INTERNACIONES_PASADAS == 150


def test_exactamente_40_actuales_y_110_pasadas():
    _, internaciones = _generar()
    actuales = [i for i in internaciones if i["fecha_egreso"] is None]
    pasadas = [i for i in internaciones if i["fecha_egreso"] is not None]
    assert len(actuales) == INTERNACIONES_ACTUALES
    assert len(pasadas) == INTERNACIONES_PASADAS


def test_tienen_los_campos_requeridos_y_ids_correlativos():
    _, internaciones = _generar()
    for n, i in enumerate(internaciones, start=1):
        assert set(i) == {"id", "id_registro_hc", "fecha_ingreso", "fecha_egreso"}
        assert i["id"] == n


# ---------------------------------------------------------------------------
# Registros
# ---------------------------------------------------------------------------

def test_registros_distintos():
    _, internaciones = _generar()
    ids = [i["id_registro_hc"] for i in internaciones]
    assert len(ids) == len(set(ids))


def test_solo_servicios_con_interna_true():
    registros, internaciones = _generar()
    interna = {s["id"]: s["nombre_tipo_servicio"] == "Con internacion" for s in SERVICIOS}
    for i in internaciones:
        r = _registro_de(registros, i)
        assert interna[r["id_servicio"]], (
            f"Internación {i['id']} sobre un servicio que no interna"
        )


def test_usa_el_id_del_registro_si_existe():
    registros = _armar_registros()
    # Ids explícitos que no coinciden con la posición.
    for pos, r in enumerate(registros, start=1):
        r["id"] = 10_000 + pos
    _, internaciones = _generar(registros)
    por_id = {r["id"]: r for r in registros}
    assert all(i["id_registro_hc"] in por_id for i in internaciones)


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------

def test_ingreso_igual_a_dia_visita():
    registros, internaciones = _generar()
    for i in internaciones:
        assert i["fecha_ingreso"] == _registro_de(registros, i)["dia_visita"]


def test_actuales_tienen_ingreso_reciente():
    _, internaciones = _generar()
    hoy = _hoy()
    desde = hoy - timedelta(days=INTERNACION_ACTUAL_DIAS[1])
    hasta = hoy - timedelta(days=INTERNACION_ACTUAL_DIAS[0])
    for i in internaciones:
        if i["fecha_egreso"] is None:
            assert desde <= _a_fecha(i["fecha_ingreso"]) <= hasta


def test_pasadas_egreso_posterior_al_ingreso_y_dentro_de_la_duracion():
    _, internaciones = _generar()
    dur_min, dur_max = DURACION_INTERNACION_DIAS
    for i in internaciones:
        if i["fecha_egreso"] is None:
            continue
        dias = (_a_fecha(i["fecha_egreso"]) - _a_fecha(i["fecha_ingreso"])).days
        assert dias > 0, f"Egreso no es posterior al ingreso en {i}"
        assert dur_min <= dias <= dur_max, f"Duración {dias} fuera de rango en {i}"


def test_pasadas_egresan_antes_de_hoy():
    _, internaciones = _generar()
    hoy = _hoy()
    for i in internaciones:
        if i["fecha_egreso"] is not None:
            assert _a_fecha(i["fecha_egreso"]) < hoy


# ---------------------------------------------------------------------------
# Sin solapamientos por paciente
# ---------------------------------------------------------------------------

def _intervalos_por_paciente(registros, internaciones):
    por_paciente: dict[int, list[tuple[date, date]]] = {}
    for i in internaciones:
        dni = _registro_de(registros, i)["dni_paciente"]
        ingreso = _a_fecha(i["fecha_ingreso"])
        egreso = _a_fecha(i["fecha_egreso"]) if i["fecha_egreso"] else date.max
        por_paciente.setdefault(dni, []).append((ingreso, egreso))
    return por_paciente


def test_sin_solapamientos_por_paciente():
    registros, internaciones = _generar()
    for dni, intervalos in _intervalos_por_paciente(registros, internaciones).items():
        intervalos.sort()
        for (_, fin_a), (ini_b, _) in zip(intervalos, intervalos[1:]):
            assert fin_a < ini_b, f"Paciente {dni} con internaciones superpuestas"


def test_a_lo_sumo_una_internacion_activa_por_paciente():
    registros, internaciones = _generar()
    dnis_activos = [
        _registro_de(registros, i)["dni_paciente"]
        for i in internaciones if i["fecha_egreso"] is None
    ]
    assert len(dnis_activos) == len(set(dnis_activos))


def test_pocos_pacientes_fuerza_a_evitar_solapamientos():
    """Con muy pocos pacientes el generador igual no superpone internaciones."""
    registros = _armar_registros(
        n_recientes_internan=80, n_pasados_internan=600, n_pacientes=120, seed=3
    )
    registros, internaciones = _generar(registros)
    assert len(internaciones) == 150
    for dni, intervalos in _intervalos_por_paciente(registros, internaciones).items():
        intervalos.sort()
        for (_, fin_a), (ini_b, _) in zip(intervalos, intervalos[1:]):
            assert fin_a < ini_b


# ---------------------------------------------------------------------------
# Errores y reproducibilidad
# ---------------------------------------------------------------------------

def test_falla_si_no_hay_suficientes_actuales_elegibles():
    registros = _armar_registros(n_recientes_internan=10)
    with pytest.raises(PoolAgotadoError, match="actuales"):
        _generar(registros)


def test_falla_si_no_hay_suficientes_pasadas_elegibles():
    registros = _armar_registros(n_pasados_internan=20, n_recientes_internan=45)
    with pytest.raises(PoolAgotadoError, match="pasadas"):
        _generar(registros)


def test_registros_de_servicios_que_no_internan_no_alcanzan():
    # Todo en el servicio 2 (interna=false): no hay candidatos.
    registros = _armar_registros(
        n_recientes_internan=0, n_pasados_internan=0, n_no_internan=500
    )
    with pytest.raises(PoolAgotadoError):
        _generar(registros)


def test_misma_seed_mismo_resultado():
    registros = _armar_registros()
    _, a = _generar(registros, seed=42)
    _, b = _generar(registros, seed=42)
    assert a == b


def test_distinta_seed_cambia_la_seleccion():
    registros = _armar_registros()
    _, a = _generar(registros, seed=1)
    _, b = _generar(registros, seed=2)
    assert a != b
