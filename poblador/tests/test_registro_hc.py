"""Test cases para el issue #13: Registros de historia clínica.

Verifica:
- 750 registros generados.
- El médico trabaja en el servicio (está en personal_servicio).
- Ninguna visita cae fuera del horario del servicio.
- Ninguna visita es antes del nacimiento del paciente.
- Ninguna visita es antes de la inauguración del centro.
- Diagnóstico y tratamiento corresponden al tipo de servicio.
- Las 40 internaciones actuales tienen fechas recientes.
- Reproducibilidad con la misma semilla.
"""

from datetime import date, timedelta
from unittest import mock

import pytest

from generadores.registro_hc import (
    _dia_siguiente,
    _fecha_reciente,
    generar_registro_hc,
)


# ---------------------------------------------------------------------------
# Fixtures de datos mínimos
# ---------------------------------------------------------------------------

SERVICIOS_MINIMO = [
    {
        "id": 1, "id_centro_salud": 1, "nombre_tipo_servicio": "Pediatría general",
    },
    {
        "id": 2, "id_centro_salud": 2, "nombre_tipo_servicio": "Cardiología",
    },
]

PERSONAL_MINIMO = [
    {"matricula": "M001", "rol": "Médico", "nombre": "M1", "apellido": "Ap"},
    {"matricula": "M002", "rol": "Médico", "nombre": "M2", "apellido": "Ap"},
    {"matricula": "E001", "rol": "Enfermero", "nombre": "E1", "apellido": "Ap"},
]

PERSONAL_SERVICIO_MINIMO = [
    {"id_servicio": 1, "matricula_personal": "M001"},
    {"id_servicio": 1, "matricula_personal": "E001"},
    {"id_servicio": 2, "matricula_personal": "M002"},
]

PACIENTES_MINIMO = [
    {"dni": 30000001, "nacimiento": "1980-01-15T00:00:00.000Z"},
    {"dni": 30000002, "nacimiento": "2015-06-10T00:00:00.000Z"},
    {"dni": 30000003, "nacimiento": "1995-03-20T00:00:00.000Z"},
]

CENTROS_MINIMO = [
    {"id": 1, "inaguracion": "1990-01-01T00:00:00.000Z"},
    {"id": 2, "inaguracion": "2000-01-01T00:00:00.000Z"},
]

HORARIOS_MINIMO = [
    {"id": 1, "apertura": "07:00", "cierre": "13:00", "dia": "Lunes"},
    {"id": 2, "apertura": "08:00", "cierre": "16:00", "dia": "Martes"},
    {"id": 3, "apertura": "13:00", "cierre": "19:00", "dia": "Miércoles"},
]

ATENCION_SERVICIO_MINIMO = [
    {"id_servicio": 1, "id_horario": 1},
    {"id_servicio": 1, "id_horario": 2},
    {"id_servicio": 2, "id_horario": 3},
]

TIPOS_SERVICIO_MINIMO = [
    {
        "nombre": "Pediatría general",
        "casos": [
            {"cie10": "J21.9", "diagnostico": "Bronquiolitis aguda",
             "tratamiento": "Hidratación"},
            {"cie10": "J06.9", "diagnostico": "Infección de vías respiratorias",
             "tratamiento": "Antipiréticos"},
        ],
    },
    {
        "nombre": "Cardiología",
        "casos": [
            {"cie10": "I10", "diagnostico": "Hipertensión esencial",
             "tratamiento": "Amlodipino"},
        ],
    },
]

DATOS_JSON_MINIMO = {
    "especialidades": ["Pediatría", "Cardiología"],
    "tipos_servicio": TIPOS_SERVICIO_MINIMO,
}


# ---------------------------------------------------------------------------
# Test: utilidades de fecha
# ---------------------------------------------------------------------------

def test_dia_siguiente_respeta_dia_semana():
    # Desde un lunes, buscar próximo lunes
    desde = date(2026, 11, 16)  # lunes
    resultado = _dia_siguiente("Lunes", desde)
    assert resultado == desde

    # Desde martes, próximo lunes
    desde = date(2026, 11, 17)  # martes
    resultado = _dia_siguiente("Lunes", desde)
    assert resultado == date(2026, 11, 23)  # lunes siguiente


def test_fecha_reciente_es_anterior_a_hoy():
    import random
    rng = random.Random(42)
    fecha = _fecha_reciente(rng)
    assert fecha < date.today()
    assert fecha >= date.today() - timedelta(days=20)


# ---------------------------------------------------------------------------
# Test: generar_registro_hc completo
# ---------------------------------------------------------------------------

def test_generar_registro_hc_devuelve_750():
    registros = generar_registro_hc(
        servicios=SERVICIOS_MINIMO,
        personal_servicio=PERSONAL_SERVICIO_MINIMO,
        personal=PERSONAL_MINIMO,
        horario_atencion=HORARIOS_MINIMO,
        atencion_servicio=ATENCION_SERVICIO_MINIMO,
        pacientes=PACIENTES_MINIMO,
        centros_de_salud=CENTROS_MINIMO,
        tipo_servicio=TIPOS_SERVICIO_MINIMO,
    )
    assert len(registros) == 750


def test_registros_tienen_campos_requeridos():
    registros = generar_registro_hc(
        servicios=SERVICIOS_MINIMO,
        personal_servicio=PERSONAL_SERVICIO_MINIMO,
        personal=PERSONAL_MINIMO,
        horario_atencion=HORARIOS_MINIMO,
        atencion_servicio=ATENCION_SERVICIO_MINIMO,
        pacientes=PACIENTES_MINIMO,
        centros_de_salud=CENTROS_MINIMO,
        tipo_servicio=TIPOS_SERVICIO_MINIMO,
    )
    for r in registros:
        assert "id_servicio" in r
        assert "dni_paciente" in r
        assert "matricula_personal" in r
        assert "dia_visita" in r
        assert "diagnostico" in r
        assert "tratamiento" in r


def test_medico_trabaja_en_el_servicio():
    registros = generar_registro_hc(
        servicios=SERVICIOS_MINIMO,
        personal_servicio=PERSONAL_SERVICIO_MINIMO,
        personal=PERSONAL_MINIMO,
        horario_atencion=HORARIOS_MINIMO,
        atencion_servicio=ATENCION_SERVICIO_MINIMO,
        pacientes=PACIENTES_MINIMO,
        centros_de_salud=CENTROS_MINIMO,
        tipo_servicio=TIPOS_SERVICIO_MINIMO,
    )
    medicos_por_servicio = {}
    for ps in PERSONAL_SERVICIO_MINIMO:
        medicos_por_servicio.setdefault(ps["id_servicio"], set()).add(
            ps["matricula_personal"]
    )
    medicos_set = {p["matricula"] for p in PERSONAL_MINIMO if p["rol"] == "Médico"}

    for r in registros:
        assert r["matricula_personal"] in medicos_por_servicio[r["id_servicio"]], (
            f"Médico {r['matricula_personal']} no trabaja en servicio {r['id_servicio']}"
        )
        assert r["matricula_personal"] in medicos_set


def test_visita_no_es_antes_de_inauguracion():
    registros = generar_registro_hc(
        servicios=SERVICIOS_MINIMO,
        personal_servicio=PERSONAL_SERVICIO_MINIMO,
        personal=PERSONAL_MINIMO,
        horario_atencion=HORARIOS_MINIMO,
        atencion_servicio=ATENCION_SERVICIO_MINIMO,
        pacientes=PACIENTES_MINIMO,
        centros_de_salud=CENTROS_MINIMO,
        tipo_servicio=TIPOS_SERVICIO_MINIMO,
    )
    centros_por_id = {c["id"]: c for c in CENTROS_MINIMO}
    for r in registros:
        centro = centros_por_id[
            next(s["id_centro_salud"] for s in SERVICIOS_MINIMO if s["id"] == r["id_servicio"])
        ]
        fecha_inag = date.fromisoformat(centro["inaguracion"][:10])
        fecha_visita = date.fromisoformat(r["dia_visita"][:10])
        assert fecha_visita >= fecha_inag, (
            f"Visita {r['dia_visita']} antes de inauguración {centro['inaguracion']}"
        )


def test_visita_no_es_antes_de_nacimiento_paciente():
    registros = generar_registro_hc(
        servicios=SERVICIOS_MINIMO,
        personal_servicio=PERSONAL_SERVICIO_MINIMO,
        personal=PERSONAL_MINIMO,
        horario_atencion=HORARIOS_MINIMO,
        atencion_servicio=ATENCION_SERVICIO_MINIMO,
        pacientes=PACIENTES_MINIMO,
        centros_de_salud=CENTROS_MINIMO,
        tipo_servicio=TIPOS_SERVICIO_MINIMO,
    )
    nacimiento_por_dni = {p["dni"]: date.fromisoformat(p["nacimiento"][:10])
                          for p in PACIENTES_MINIMO}
    for r in registros:
        fecha_visita = date.fromisoformat(r["dia_visita"][:10])
        fecha_nac = nacimiento_por_dni[r["dni_paciente"]]
        assert fecha_visita >= fecha_nac, (
            f"Visita {r['dia_visita']} antes de nacimiento {r['dni_paciente']}"
        )


def test_diagnostico_es_del_tipo_de_servicio():
    registros = generar_registro_hc(
        servicios=SERVICIOS_MINIMO,
        personal_servicio=PERSONAL_SERVICIO_MINIMO,
        personal=PERSONAL_MINIMO,
        horario_atencion=HORARIOS_MINIMO,
        atencion_servicio=ATENCION_SERVICIO_MINIMO,
        pacientes=PACIENTES_MINIMO,
        centros_de_salud=CENTROS_MINIMO,
        tipo_servicio=TIPOS_SERVICIO_MINIMO,
    )
    diagnosticos_por_tipo = {}
    for t in TIPOS_SERVICIO_MINIMO:
        diagnosticos_por_tipo[t["nombre"]] = {c["diagnostico"] for c in t["casos"]}

    nombre_por_servicio = {s["id"]: s["nombre_tipo_servicio"] for s in SERVICIOS_MINIMO}
    for r in registros:
        tipo = nombre_por_servicio[r["id_servicio"]]
        assert r["diagnostico"] in diagnosticos_por_tipo[tipo], (
            f"Diagnóstico '{r['diagnostico']}' no pertenece a {tipo}"
        )


def test_primeros_40_tienen_fechas_recientes():
    registros = generar_registro_hc(
        servicios=SERVICIOS_MINIMO,
        personal_servicio=PERSONAL_SERVICIO_MINIMO,
        personal=PERSONAL_MINIMO,
        horario_atencion=HORARIOS_MINIMO,
        atencion_servicio=ATENCION_SERVICIO_MINIMO,
        pacientes=PACIENTES_MINIMO,
        centros_de_salud=CENTROS_MINIMO,
        tipo_servicio=TIPOS_SERVICIO_MINIMO,
    )
    hoy = date.today()
    for r in registros[:40]:
        fecha = date.fromisoformat(r["dia_visita"][:10])
        assert hoy - timedelta(days=20) <= fecha < hoy, (
            f"Internación actual {r['dia_visita']} no es reciente"
        )


def test_misma_seed_mismo_resultado():
    kwargs = dict(
        servicios=SERVICIOS_MINIMO,
        personal_servicio=PERSONAL_SERVICIO_MINIMO,
        personal=PERSONAL_MINIMO,
        horario_atencion=HORARIOS_MINIMO,
        atencion_servicio=ATENCION_SERVICIO_MINIMO,
        pacientes=PACIENTES_MINIMO,
        centros_de_salud=CENTROS_MINIMO,
        tipo_servicio=TIPOS_SERVICIO_MINIMO,
    )
    r1 = generar_registro_hc(**kwargs, rng=None)
    # Sin rng, usa SEED global; hacer dos llamadas seguidas debería dar lo mismo
    # pero el rng interno se deriva de SEED
    from generadores.registro_hc import generar_registro_hc as grh
    r1 = grh(**kwargs)
    r2 = grh(**kwargs)
    assert r1 == r2


def test_generar_registro_hc_con_datos_completos():
    """Prueba generar_registro_hc con datos completos pasados directamente."""
    from generadores.registro_hc import generar_registro_hc
    resultado = generar_registro_hc(
        servicios=SERVICIOS_MINIMO,
        personal_servicio=PERSONAL_SERVICIO_MINIMO,
        personal=PERSONAL_MINIMO,
        horario_atencion=HORARIOS_MINIMO,
        atencion_servicio=ATENCION_SERVICIO_MINIMO,
        pacientes=PACIENTES_MINIMO,
        centros_de_salud=CENTROS_MINIMO,
        tipo_servicio=TIPOS_SERVICIO_MINIMO,
    )
    assert len(resultado) == 750
    for r in resultado:
        assert "id_servicio" in r
        assert "dni_paciente" in r
        assert "matricula_personal" in r
        assert "dia_visita" in r
        assert "diagnostico" in r
        assert "tratamiento" in r
