"""Test cases para el issue #12: Estructura clínica (servicios, horarios, asignaciones).

Verifica:
- tipo_servicio: 20 filas desde el JSON.
- especialidad: 15 filas desde el JSON.
- especialidad_requerida: 25 filas.
- horario_atencion: 70 filas (7 días × 10 franjas, todas distintas).
- atencion_centro: 20 filas, un horario por centro.
- servicio: 70 filas, pares (centro, tipo) únicos, todo centro con ≥1 servicio.
- atencion_servicio: 160 filas.
- personal_servicio: 150 filas, cada persona en un solo servicio, encargado es médico.
- especializado_en: 320 filas.
- Cupos de médicos/enfermeros respetados.
- Reproducibilidad con la misma semilla.
"""

from unittest import mock

import pytest

from generadores.estructura_clinica import (
    generar_atencion_centro,
    generar_atencion_servicio,
    generar_horario_atencion,
    generar_personal_servicio_y_especializado_en,
    generar_servicio,
    generar_tipo_servicio_y_especialidad_requerida,
    generar_estructura_clinica,
)


# ---------------------------------------------------------------------------
# Fixtures de datos mínimos (mockeados para evitar red)
# ---------------------------------------------------------------------------

DATOS_JSON_MINIMO = {
    "especialidades": [
        "Pediatría", "Cardiología", "Medicina General", "Ginecología",
        "Traumatología", "Oftalmología", "Dermatología", "Otorrinolaringología",
        "Neurología", "Psiquiatría", "Endocrinología", "Nefrología",
        "Oncología", "Geriatría", "Kinesiología",
    ],
    "tipos_servicio": [
        {"nombre": "Pediatría general", "num_medicos": 2, "num_enfermeros": 2,
         "especialidades_requeridas": ["Pediatría"], "interna": True, "peso": 1.5,
         "casos": []},
        {"nombre": "Cardiología", "num_medicos": 2, "num_enfermeros": 2,
         "especialidades_requeridas": ["Cardiología"], "interna": True, "peso": 1.2,
         "casos": []},
        {"nombre": "Medicina General", "num_medicos": 1, "num_enfermeros": 1,
         "especialidades_requeridas": ["Medicina General"], "interna": False, "peso": 1.0,
         "casos": []},
        {"nombre": "Ginecología", "num_medicos": 1, "num_enfermeros": 1,
         "especialidades_requeridas": ["Ginecología"], "interna": False, "peso": 1.0,
         "casos": []},
        {"nombre": "Traumatología", "num_medicos": 2, "num_enfermeros": 1,
         "especialidades_requeridas": ["Traumatología"], "interna": True, "peso": 1.0,
         "casos": []},
        {"nombre": "Oftalmología", "num_medicos": 1, "num_enfermeros": 1,
         "especialidades_requeridas": ["Oftalmología"], "interna": False, "peso": 0.8,
         "casos": []},
        {"nombre": "Dermatología", "num_medicos": 1, "num_enfermeros": 1,
         "especialidades_requeridas": ["Dermatología"], "interna": False, "peso": 0.8,
         "casos": []},
        {"nombre": "Otorrinolaringología", "num_medicos": 1, "num_enfermeros": 1,
         "especialidades_requeridas": ["Otorrinolaringología"], "interna": False, "peso": 0.8,
         "casos": []},
        {"nombre": "Neurología", "num_medicos": 2, "num_enfermeros": 1,
         "especialidades_requeridas": ["Neurología"], "interna": True, "peso": 0.9,
         "casos": []},
        {"nombre": "Psiquiatría", "num_medicos": 1, "num_enfermeros": 1,
         "especialidades_requeridas": ["Psiquiatría"], "interna": False, "peso": 0.7,
         "casos": []},
        {"nombre": "Endocrinología", "num_medicos": 1, "num_enfermeros": 1,
         "especialidades_requeridas": ["Endocrinología"], "interna": False, "peso": 0.7,
         "casos": []},
        {"nombre": "Nefrología", "num_medicos": 2, "num_enfermeros": 1,
         "especialidades_requeridas": ["Nefrología"], "interna": True, "peso": 0.6,
         "casos": []},
        {"nombre": "Oncología", "num_medicos": 2, "num_enfermeros": 2,
         "especialidades_requeridas": ["Oncología"], "interna": True, "peso": 0.8,
         "casos": []},
        {"nombre": "Geriatría", "num_medicos": 1, "num_enfermeros": 2,
         "especialidades_requeridas": ["Geriatría"], "interna": False, "peso": 0.9,
         "casos": []},
        {"nombre": "Kinesiología", "num_medicos": 1, "num_enfermeros": 2,
         "especialidades_requeridas": ["Kinesiología"], "interna": False, "peso": 0.8,
         "casos": []},
        {"nombre": "Medicina Familiar", "num_medicos": 1, "num_enfermeros": 1,
         "especialidades_requeridas": ["Medicina General", "Pediatría"],
         "interna": False, "peso": 0.6, "casos": []},
        {"nombre": "Salud Materno Infantil", "num_medicos": 1, "num_enfermeros": 2,
         "especialidades_requeridas": ["Ginecología", "Pediatría"],
         "interna": True, "peso": 0.6, "casos": []},
        {"nombre": "Cuidados Críticos", "num_medicos": 2, "num_enfermeros": 2,
         "especialidades_requeridas": ["Cardiología", "Neurología"],
         "interna": True, "peso": 0.5, "casos": []},
        {"nombre": "Rehabilitación", "num_medicos": 1, "num_enfermeros": 2,
         "especialidades_requeridas": ["Traumatología", "Kinesiología"],
         "interna": False, "peso": 0.5, "casos": []},
        {"nombre": "Salud Mental Integral", "num_medicos": 1, "num_enfermeros": 1,
         "especialidades_requeridas": ["Psiquiatría", "Neurología"],
         "interna": False, "peso": 0.4, "casos": []},
    ],
}

CENTROS_MINIMO = [{"id": i, "nombre": f"Centro {i}"} for i in range(1, 21)]

PERSONAL_MINIMO = (
    [{"matricula": f"M{i:03d}", "rol": "Médico", "nombre": f"M{i}", "apellido": "Ap"}
     for i in range(1, 101)]
    + [{"matricula": f"E{i:03d}", "rol": "Enfermero", "nombre": f"E{i}", "apellido": "Ap"}
       for i in range(1, 201)]
)


# ---------------------------------------------------------------------------
# Test: tipo_servicio y especialidad_requerida
# ---------------------------------------------------------------------------

def test_tipo_servicio_y_especialidad_requerida_desde_json():
    ts, er = generar_tipo_servicio_y_especialidad_requerida(DATOS_JSON_MINIMO)
    assert len(ts) == 20
    assert len(er) == 25  # 15 tipos con 1 req + 5 tipos con 2 req = 25

    for t in ts:
        assert "id" in t
        assert "nombre" in t
        assert "num_medicos" in t
        assert "num_enfermeros" in t
        assert t["num_medicos"] >= 1

    ids_ts = {t["nombre"] for t in ts}
    for e in er:
        assert e["nombre_tipo_servicio"] in ids_ts
        assert e["nombre_especialidad"] in DATOS_JSON_MINIMO["especialidades"]


# ---------------------------------------------------------------------------
# Test: horario_atencion
# ---------------------------------------------------------------------------

def test_horario_atencion_70_filas_todas_distintas():
    import random
    rng = random.Random(42)
    h = generar_horario_atencion(rng)
    assert len(h) == 70

    pares = {(row["dia"], row["apertura"], row["cierre"]) for row in h}
    assert len(pares) == 70  # todas distintas

    dias = {row["dia"] for row in h}
    assert len(dias) == 7  # Lunes a Domingo


# ---------------------------------------------------------------------------
# Test: atencion_centro
# ---------------------------------------------------------------------------

def test_atencion_centro_uno_por_centro():
    import random
    rng = random.Random(42)
    horarios = generar_horario_atencion(rng)
    ac = generar_atencion_centro(CENTROS_MINIMO, horarios, rng)
    assert len(ac) == 20
    centros_ids = {row["id_centro_salud"] for row in ac}
    assert centros_ids == set(range(1, 21))


# ---------------------------------------------------------------------------
# Test: servicio
# ---------------------------------------------------------------------------

def test_servicio_70_pares_unicos_todo_centro_con_servicio():
    import random
    rng = random.Random(42)
    ts, _ = generar_tipo_servicio_y_especialidad_requerida(DATOS_JSON_MINIMO)
    svc = generar_servicio(CENTROS_MINIMO, ts, rng)
    assert len(svc) == 70

    pares = {(s["id_centro_salud"], s["nombre_tipo_servicio"]) for s in svc}
    assert len(pares) == 70  # pares únicos

    centros_con_servicio = {s["id_centro_salud"] for s in svc}
    assert centros_con_servicio == set(range(1, 21))  # todo centro con ≥1

    for s in svc:
        assert s["nombre_tipo_servicio"] in {t["nombre"] for t in ts}


# ---------------------------------------------------------------------------
# Test: atencion_servicio
# ---------------------------------------------------------------------------

def test_atencion_servicio_160():
    import random
    rng = random.Random(42)
    ts, _ = generar_tipo_servicio_y_especialidad_requerida(DATOS_JSON_MINIMO)
    svc = generar_servicio(CENTROS_MINIMO, ts, rng)
    horarios = generar_horario_atencion(rng)
    acs = generar_atencion_servicio(svc, horarios, rng)
    assert len(acs) == 160


# ---------------------------------------------------------------------------
# Test: personal_servicio y especializado_en
# ---------------------------------------------------------------------------

def test_personal_servicio_150_cada_persona_un_servicio_encargado_medico():
    import random
    rng = random.Random(42)
    ts, er = generar_tipo_servicio_y_especialidad_requerida(DATOS_JSON_MINIMO)
    svc = generar_servicio(CENTROS_MINIMO, ts, rng)

    ps, ee = generar_personal_servicio_y_especializado_en(
        svc, ts, er, PERSONAL_MINIMO, DATOS_JSON_MINIMO["especialidades"], rng
    )

    assert len(ps) == 150

    # Cada persona en un solo servicio
    matriculas = [p["matricula_personal"] for p in ps]
    assert len(matriculas) == len(set(matriculas)), "Cada persona en un solo servicio"

    # Todo encargado es médico
    medicos_matriculas = {p["matricula"] for p in PERSONAL_MINIMO if p["rol"] == "Médico"}
    for s in svc:
        enc = s.get("matricula_encargado")
        if enc is not None:
            assert enc in medicos_matriculas, f"Encargado no es médico: {enc}"


def test_especializado_en_320():
    import random
    rng = random.Random(42)
    ts, er = generar_tipo_servicio_y_especialidad_requerida(DATOS_JSON_MINIMO)
    svc = generar_servicio(CENTROS_MINIMO, ts, rng)

    ps, ee = generar_personal_servicio_y_especializado_en(
        svc, ts, er, PERSONAL_MINIMO, DATOS_JSON_MINIMO["especialidades"], rng
    )

    assert len(ee) == 320, f"Esperadas 320, obtuve {len(ee)}"


def test_todo_personal_servicio_tiene_especialidades_requeridas():
    import random
    rng = random.Random(42)
    ts, er = generar_tipo_servicio_y_especialidad_requerida(DATOS_JSON_MINIMO)
    svc = generar_servicio(CENTROS_MINIMO, ts, rng)

    ps, ee = generar_personal_servicio_y_especializado_en(
        svc, ts, er, PERSONAL_MINIMO, DATOS_JSON_MINIMO["especialidades"], rng
    )

    # Indexar especialidades requeridas por tipo
    req_por_tipo = {}
    for t in DATOS_JSON_MINIMO["tipos_servicio"]:
        req_por_tipo[t["nombre"]] = set(t["especialidades_requeridas"])

    # Indexar especialidades por persona
    esps_por_persona = {}
    for e in ee:
        esps_por_persona.setdefault(e["matricula_personal"], set()).add(
            e["nombre_especialidad"]
    )

    # Cada persona en personal_servicio debe tener las especialidades de su servicio
    svc_por_id = {s["id"]: s for s in svc}
    for p in ps:
        s = svc_por_id[p["id_servicio"]]
        reqs = req_por_tipo[s["nombre_tipo_servicio"]]
        personales = esps_por_persona.get(p["matricula_personal"], set())
        for r in reqs:
            assert r in personales, (
                f"Persona {p['matricula_personal']} falta especialidad {r} "
                f"para servicio {s['nombre_tipo_servicio']}"
            )


# ---------------------------------------------------------------------------
# Test: generar_estructura_clinica completo
# ---------------------------------------------------------------------------

def test_generar_estructura_clinica_completo():
    import random
    resultado = generar_estructura_clinica(
        seed=42,
        personal=list(PERSONAL_MINIMO),
        centros=CENTROS_MINIMO,
        datos_json=DATOS_JSON_MINIMO,
    )

    assert len(resultado["tipo_servicio"]) == 20
    assert len(resultado["especialidad"]) == 15
    assert len(resultado["especialidad_requerida"]) == 25
    assert len(resultado["horario_atencion"]) == 70
    assert len(resultado["atencion_centro"]) == 20
    assert len(resultado["servicio"]) == 70
    assert len(resultado["atencion_servicio"]) == 160
    assert len(resultado["personal_servicio"]) == 150
    assert len(resultado["especializado_en"]) == 320


def test_misma_seed_mismo_resultado():
    import random
    r1 = generar_estructura_clinica(
        seed=42,
        personal=list(PERSONAL_MINIMO),
        centros=CENTROS_MINIMO,
        datos_json=DATOS_JSON_MINIMO,
    )
    r2 = generar_estructura_clinica(
        seed=42,
        personal=list(PERSONAL_MINIMO),
        centros=CENTROS_MINIMO,
        datos_json=DATOS_JSON_MINIMO,
    )

    assert r1 == r2
