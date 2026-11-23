"""Test cases para el issue #16: Validador independiente.

Verifica:
- Sobre datos correctos, validar() devuelve una lista vacía.
- Cada regla tiene al menos un test que la dispara con datos adulterados a
  propósito y comprueba tabla, fila y regla de la violación.
- El validador no modifica las tablas y no usa pools.
"""

import copy
from datetime import date
from pathlib import Path

import pytest

import validar as modulo_validar
from validar import REGLAS, Violacion, validar

HOY = date(2026, 11, 22)  # domingo


# ---------------------------------------------------------------------------
# Dataset correcto (chico, pero con todas las tablas y relaciones)
# ---------------------------------------------------------------------------

def tablas_ok() -> dict:
    return {
        "departamento": [{"id": 1, "nombre": "Paraná"}, {"id": 2, "nombre": "Colón"}],
        "ciudad": [
            {"id": 1, "id_departamento": 1, "nombre": "Paraná"},
            {"id": 2, "id_departamento": 2, "nombre": "Colón"},
        ],
        "barrio": [
            {"id": 1, "id_ciudad": 1, "nombre": "Centro Paraná"},
            {"id": 2, "id_ciudad": 2, "nombre": "Centro Colón"},
        ],
        "obra_social": [{"id": 1, "razon_social": "OSDE", "estado": True}],
        "paciente": [
            {"dni": 30000001, "id_obra_social": 1, "nombre": "Ana", "apellido": "Pérez",
             "nacimiento": "1980-01-15", "num_asociado": 1001},
            {"dni": 30000002, "id_obra_social": None, "nombre": "Beto", "apellido": "Gómez",
             "nacimiento": "2015-06-10", "num_asociado": None},
            {"dni": 30000003, "id_obra_social": None, "nombre": "Carla", "apellido": "Ruiz",
             "nacimiento": "1995-03-20", "num_asociado": None},
        ],
        "centro_de_salud": [
            {"id": 1, "id_barrio": 1, "nombre": "Centro de Salud Norte",
             "direccion": "San Martín 100", "inaguracion": "1990-01-01",
             "calle": "San Martín", "altura": 100},
            {"id": 2, "id_barrio": 2, "nombre": "Centro de Salud Sur",
             "direccion": "Belgrano 200", "inaguracion": "2000-05-05",
             "calle": "Belgrano", "altura": 200},
        ],
        "tipo_servicio": [
            {"id": 1, "nombre": "Pediatría general", "num_medicos": 1, "num_enfermeros": 1,
             "interna": True},
            {"id": 2, "nombre": "Cardiología", "num_medicos": 1, "num_enfermeros": 1,
             "interna": False},
        ],
        "especialidad": [{"nombre": "Pediatría"}, {"nombre": "Cardiología"}],
        "especialidad_requerida": [
            {"nombre_tipo_servicio": "Pediatría general", "nombre_especialidad": "Pediatría"},
            {"nombre_tipo_servicio": "Cardiología", "nombre_especialidad": "Cardiología"},
        ],
        "personal": [
            {"matricula": "541030000001", "nombre": "Mario", "apellido": "Díaz",
             "telefono": "+5493433000001", "email": "m1@example.com",
             "nacimiento": "1985-04-04", "rol": "Médico"},
            {"matricula": "541030000002", "nombre": "Elena", "apellido": "Sosa",
             "telefono": "+5493433000002", "email": "e1@example.com",
             "nacimiento": "1990-09-09", "rol": "Enfermero"},
            {"matricula": "541030000003", "nombre": "Raúl", "apellido": "Vega",
             "telefono": "+5493433000003", "email": "m2@example.com",
             "nacimiento": "1978-12-12", "rol": "Médico"},
            {"matricula": "541030000004", "nombre": "Lucía", "apellido": "Paz",
             "telefono": "+5493433000004", "email": "e2@example.com",
             "nacimiento": "1992-02-02", "rol": "Enfermero"},
        ],
        "especializado_en": [
            {"matricula_personal": "541030000001", "nombre_especialidad": "Pediatría"},
            {"matricula_personal": "541030000002", "nombre_especialidad": "Pediatría"},
            {"matricula_personal": "541030000003", "nombre_especialidad": "Cardiología"},
            {"matricula_personal": "541030000004", "nombre_especialidad": "Cardiología"},
        ],
        "horario_atencion": [
            {"id": 1, "apertura": "07:00", "cierre": "13:00", "dia": "Lunes"},
            {"id": 2, "apertura": "08:00", "cierre": "16:00", "dia": "Martes"},
            {"id": 3, "apertura": "13:00", "cierre": "19:00", "dia": "Miércoles"},
        ],
        "atencion_centro": [
            {"id_centro_salud": 1, "id_horario": 1},
            {"id_centro_salud": 2, "id_horario": 2},
        ],
        "servicio": [
            {"id": 1, "id_centro_salud": 1, "nombre_tipo_servicio": "Pediatría general",
             "matricula_encargado": "541030000001"},
            {"id": 2, "id_centro_salud": 1, "nombre_tipo_servicio": "Cardiología",
             "matricula_encargado": "541030000003"},
        ],
        "atencion_servicio": [
            {"id_servicio": 1, "id_horario": 1},
            {"id_servicio": 1, "id_horario": 2},
            {"id_servicio": 2, "id_horario": 3},
        ],
        "personal_servicio": [
            {"id_servicio": 1, "matricula_personal": "541030000001"},
            {"id_servicio": 1, "matricula_personal": "541030000002"},
            {"id_servicio": 2, "matricula_personal": "541030000003"},
            {"id_servicio": 2, "matricula_personal": "541030000004"},
        ],
        # Sin `id`: el id de cada registro es su posición (1, 2, 3...).
        # 2026-11-16 = lunes, 2026-11-17 = martes, 2026-11-04 = miércoles.
        "registro_hc": [
            {"id_servicio": 1, "dni_paciente": 30000001, "matricula_personal": "541030000001",
             "dia_visita": "2026-11-16", "diagnostico": "d", "tratamiento": "t"},
            {"id_servicio": 1, "dni_paciente": 30000002, "matricula_personal": "541030000001",
             "dia_visita": "2026-11-17 10:30:00", "diagnostico": "d", "tratamiento": "t"},
            {"id_servicio": 2, "dni_paciente": 30000001, "matricula_personal": "541030000003",
             "dia_visita": "2026-11-04", "diagnostico": "d", "tratamiento": "t"},
            {"id_servicio": 1, "dni_paciente": 30000001, "matricula_personal": "541030000001",
             "dia_visita": "2026-11-09", "diagnostico": "d", "tratamiento": "t"},
        ],
        "internacion": [
            # paciente 1: internada del 16 al 20 (pasada)
            {"id": 1, "id_registro_hc": 1, "fecha_ingreso": "2026-11-16",
             "fecha_egreso": "2026-11-20"},
            # paciente 2: actual (sin egreso)
            {"id": 2, "id_registro_hc": 2, "fecha_ingreso": "2026-11-17 10:30:00",
             "fecha_egreso": None},
        ],
    }


def violaciones(tablas: dict) -> list[Violacion]:
    return validar(tablas, hoy=HOY)


def assert_dispara(tablas: dict, tabla: str, fila: int, regla: str) -> list[Violacion]:
    """Comprueba que validar() informa exactamente esa tabla, fila y regla."""
    v = violaciones(tablas)
    assert any((x.tabla, x.fila, x.regla) == (tabla, fila, regla) for x in v), (
        f"No se informó ({tabla}, fila {fila}, {regla}). Violaciones: "
        + "\n".join(str(x) for x in v)
    )
    return v


# ---------------------------------------------------------------------------
# Datos correctos
# ---------------------------------------------------------------------------

def test_datos_correctos_devuelven_lista_vacia():
    assert violaciones(tablas_ok()) == []


def test_tablas_ausentes_se_toman_como_vacias():
    assert validar({}, hoy=HOY) == []


def test_validar_no_modifica_las_tablas():
    t = tablas_ok()
    copia = copy.deepcopy(t)
    t["paciente"][0]["nombre"] = "x" * 40  # fuerza violaciones
    copia["paciente"][0]["nombre"] = "x" * 40
    validar(t, hoy=HOY)
    assert t == copia


def test_acepta_ids_explicitos_en_registro_hc():
    t = tablas_ok()
    for r, id_ in zip(t["registro_hc"], (10, 20, 30, 40)):
        r["id"] = id_
    t["internacion"][0]["id_registro_hc"] = 10
    t["internacion"][1]["id_registro_hc"] = 20
    assert violaciones(t) == []


def test_violacion_tiene_tabla_fila_regla_y_detalle():
    t = tablas_ok()
    t["paciente"][1]["nombre"] = "x" * 31
    (v,) = violaciones(t)
    assert (v.tabla, v.fila, v.regla) == ("paciente", 1, "largo_maximo")
    assert "nombre" in v.detalle
    assert "paciente" in str(v) and "fila 1" in str(v) and "largo_maximo" in str(v)


def test_todas_las_reglas_declaradas_tienen_test():
    """Guarda: si se agrega una regla a REGLAS hay que agregarle un test acá."""
    fuente = Path(__file__).read_text(encoding="utf-8")
    # Se busca solo en lo que viene después de este test, para que la propia
    # lista de reglas de este archivo no cuente como cobertura.
    despues = fuente.rsplit("def test_el_validador_no_usa_pools_ni_generadores", 1)[1]
    sin_test = [r for r in REGLAS if f'"{r}"' not in despues]
    assert not sin_test, f"Reglas sin test: {sin_test}"


def test_el_validador_no_usa_pools_ni_generadores():
    fuente = Path(modulo_validar.__file__).read_text(encoding="utf-8")
    for prohibido in ("import pools", "from pools", "import generadores",
                      "from generadores", "from fuentes", "import fuentes"):
        assert prohibido not in fuente, f"validar.py no debe tener '{prohibido}'"


# ---------------------------------------------------------------------------
# UNIQUE
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tabla, columna, fila_a_cambiar, valor", [
    ("departamento", "nombre", 1, "Paraná"),
    ("departamento", "id", 1, 1),
    ("ciudad", "nombre", 1, "Paraná"),
    ("barrio", "nombre", 1, "Centro Paraná"),
    ("paciente", "dni", 1, 30000001),
    ("paciente", "num_asociado", 2, 1001),
    ("centro_de_salud", "nombre", 1, "Centro de Salud Norte"),
    ("tipo_servicio", "nombre", 1, "Pediatría general"),
    ("personal", "matricula", 1, "541030000001"),
    ("personal", "telefono", 1, "+5493433000001"),
    ("personal", "email", 1, "m1@example.com"),
    ("especialidad", "nombre", 1, "Pediatría"),
    ("servicio", "id", 1, 1),
    ("horario_atencion", "id", 1, 1),
    ("internacion", "id", 1, 1),
])
def test_unique(tabla, columna, fila_a_cambiar, valor):
    t = tablas_ok()
    t[tabla][fila_a_cambiar][columna] = valor
    assert_dispara(t, tabla, fila_a_cambiar, "unique")


def test_unique_clave_compuesta():
    t = tablas_ok()
    t["especializado_en"].append(dict(t["especializado_en"][0]))
    assert_dispara(t, "especializado_en", 4, "unique")

    t = tablas_ok()
    t["atencion_servicio"].append({"id_servicio": 1, "id_horario": 1})
    assert_dispara(t, "atencion_servicio", 3, "unique")

    t = tablas_ok()
    t["atencion_centro"].append({"id_centro_salud": 1, "id_horario": 1})
    assert_dispara(t, "atencion_centro", 2, "unique")

    t = tablas_ok()
    t["especialidad_requerida"].append(dict(t["especialidad_requerida"][0]))
    assert_dispara(t, "especialidad_requerida", 2, "unique")

    t = tablas_ok()
    t["personal_servicio"].append(dict(t["personal_servicio"][0]))
    assert_dispara(t, "personal_servicio", 4, "unique")


def test_unique_id_repetido_en_registro_hc():
    t = tablas_ok()
    t["registro_hc"][0]["id"] = 5
    t["registro_hc"][1]["id"] = 5
    assert_dispara(t, "registro_hc", 1, "unique")


def test_null_no_viola_unique():
    t = tablas_ok()  # dos pacientes con num_asociado None
    assert not [v for v in violaciones(t) if v.regla == "unique"]


# ---------------------------------------------------------------------------
# Largos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tabla, columna", [
    ("departamento", "nombre"), ("ciudad", "nombre"), ("barrio", "nombre"),
    ("obra_social", "razon_social"), ("paciente", "nombre"), ("paciente", "apellido"),
    ("centro_de_salud", "nombre"), ("centro_de_salud", "direccion"),
    ("centro_de_salud", "calle"), ("tipo_servicio", "nombre"),
    ("personal", "nombre"), ("personal", "apellido"), ("especialidad", "nombre"),
])
def test_largo_maximo_30(tabla, columna):
    t = tablas_ok()
    t[tabla][0][columna] = "x" * 31
    assert_dispara(t, tabla, 0, "largo_maximo")


def test_largo_exacto_30_es_valido():
    t = tablas_ok()
    t["paciente"][0]["nombre"] = "x" * 30
    assert not [v for v in violaciones(t) if v.regla == "largo_maximo"]


def test_largo_maximo_en_telefono_y_email():
    t = tablas_ok()
    t["personal"][0]["email"] = "a" * 20 + "@example.com"  # 32 caracteres
    assert_dispara(t, "personal", 0, "largo_maximo")


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("matricula", [
    "541030000X01",   # letra
    "5460300000",     # tercer dígito 6 (el tipo de documento va de 1 a 5)
    "540030000001",   # tercer dígito 0
    "54",             # muy corta
    "",               # vacía
])
def test_regex_matricula(matricula):
    t = tablas_ok()
    t["personal"][0]["matricula"] = matricula
    assert_dispara(t, "personal", 0, "regex_matricula")


@pytest.mark.parametrize("telefono", [
    "abc12345678",       # letras
    "+54 934 (33) x",    # carácter inválido
    "123456",            # menos de 7 caracteres
    "+5493433000001234", # más de 15 caracteres
    "() - ()- -",        # cumple el patrón pero sin 7 dígitos
    None,
])
def test_regex_telefono(telefono):
    t = tablas_ok()
    t["personal"][0]["telefono"] = telefono
    assert_dispara(t, "personal", 0, "regex_telefono")


@pytest.mark.parametrize("email", [
    "sin-arroba.example.com", "a@b", "a@@example.com", "a b@example.com",
    "@example.com", "a@example.c", None,
])
def test_regex_email(email):
    t = tablas_ok()
    t["personal"][0]["email"] = email
    assert_dispara(t, "personal", 0, "regex_email")


def test_telefono_con_espacios_y_guiones_es_valido():
    t = tablas_ok()
    t["personal"][0]["telefono"] = "+54 343 300-0001"
    assert not [v for v in violaciones(t) if v.regla == "regex_telefono"]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

def test_enum_invalido():
    t = tablas_ok()
    t["personal"][0]["rol"] = "Administrativo"
    assert_dispara(t, "personal", 0, "enum_invalido")

    t = tablas_ok()
    t["horario_atencion"][0]["dia"] = "Funday"
    assert_dispara(t, "horario_atencion", 0, "enum_invalido")


# ---------------------------------------------------------------------------
# FK
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tabla, fila, columna, valor", [
    ("ciudad", 0, "id_departamento", 99),
    ("barrio", 0, "id_ciudad", 99),
    ("paciente", 0, "id_obra_social", 99),
    ("centro_de_salud", 0, "id_barrio", 99),
    ("servicio", 0, "id_centro_salud", 99),
    ("servicio", 0, "nombre_tipo_servicio", "Inexistente"),
    ("servicio", 0, "matricula_encargado", "549900000000"),
    ("personal_servicio", 0, "id_servicio", 99),
    ("personal_servicio", 0, "matricula_personal", "549900000000"),
    ("registro_hc", 0, "id_servicio", 99),
    ("registro_hc", 0, "dni_paciente", 11111111),
    ("registro_hc", 0, "matricula_personal", "549900000000"),
    ("internacion", 0, "id_registro_hc", 999),
    ("especializado_en", 0, "matricula_personal", "549900000000"),
    ("especializado_en", 0, "nombre_especialidad", "Inexistente"),
    ("especialidad_requerida", 0, "nombre_tipo_servicio", "Inexistente"),
    ("especialidad_requerida", 0, "nombre_especialidad", "Inexistente"),
    ("atencion_centro", 0, "id_centro_salud", 99),
    ("atencion_centro", 0, "id_horario", 99),
    ("atencion_servicio", 0, "id_servicio", 99),
    ("atencion_servicio", 0, "id_horario", 99),
])
def test_fk_sin_resolver(tabla, fila, columna, valor):
    t = tablas_ok()
    t[tabla][fila][columna] = valor
    assert_dispara(t, tabla, fila, "fk")


def test_fk_nullable_con_none_es_valida():
    t = tablas_ok()  # paciente 2 sin obra social, y se pone un servicio sin encargado
    t["servicio"][1]["matricula_encargado"] = None
    assert not [v for v in violaciones(t) if v.regla == "fk"]


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tabla, fila, columna", [
    ("centro_de_salud", 0, "inaguracion"),
    ("paciente", 0, "nacimiento"),
    ("personal", 0, "nacimiento"),
    ("registro_hc", 0, "dia_visita"),
    ("internacion", 0, "fecha_ingreso"),
    ("internacion", 0, "fecha_egreso"),
])
@pytest.mark.parametrize("valor", ["2026-11-22", "2026-11-23", "2030-01-01T10:00:00"])
def test_fecha_no_anterior_a_hoy(tabla, fila, columna, valor):
    t = tablas_ok()
    t[tabla][fila][columna] = valor
    assert_dispara(t, tabla, fila, "fecha_anterior_a_hoy")


def test_ayer_es_anterior_a_hoy():
    t = tablas_ok()
    t["paciente"][0]["nacimiento"] = "2026-11-21"
    assert not [v for v in violaciones(t) if v.regla == "fecha_anterior_a_hoy"]


def test_fecha_invalida():
    t = tablas_ok()
    t["paciente"][0]["nacimiento"] = "no-es-una-fecha"
    assert_dispara(t, "paciente", 0, "fecha_invalida")


def test_acepta_fechas_como_objetos_date():
    t = tablas_ok()
    t["paciente"][0]["nacimiento"] = date(1980, 1, 15)
    assert violaciones(t) == []


def test_personal_menor_de_18():
    t = tablas_ok()
    t["personal"][0]["nacimiento"] = "2010-01-01"
    assert_dispara(t, "personal", 0, "personal_mayor_de_18")


def test_personal_justo_de_18_es_valido():
    t = tablas_ok()
    t["personal"][0]["nacimiento"] = "2008-11-22"  # cumple 18 hoy
    assert not [v for v in violaciones(t) if v.regla == "personal_mayor_de_18"]
    t["personal"][0]["nacimiento"] = "2008-11-23"  # los cumple mañana
    assert_dispara(t, "personal", 0, "personal_mayor_de_18")


# ---------------------------------------------------------------------------
# Servicios: (centro, tipo), encargado, cupos
# ---------------------------------------------------------------------------

def test_centro_tipo_unico():
    t = tablas_ok()
    t["servicio"][1]["nombre_tipo_servicio"] = "Pediatría general"  # mismo centro y tipo
    assert_dispara(t, "servicio", 1, "centro_tipo_unico")


def test_mismo_tipo_en_otro_centro_es_valido():
    t = tablas_ok()
    t["servicio"][1]["id_centro_salud"] = 2
    t["servicio"][1]["nombre_tipo_servicio"] = "Pediatría general"
    assert not [v for v in violaciones(t) if v.regla == "centro_tipo_unico"]


def test_encargado_debe_ser_medico():
    t = tablas_ok()
    t["servicio"][0]["matricula_encargado"] = "541030000002"  # enfermero del servicio 1
    assert_dispara(t, "servicio", 0, "encargado_medico")


def test_encargado_debe_trabajar_en_el_servicio():
    t = tablas_ok()
    t["servicio"][0]["matricula_encargado"] = "541030000003"  # médico del servicio 2
    assert_dispara(t, "servicio", 0, "encargado_en_servicio")


def test_cupo_medicos():
    t = tablas_ok()
    # Un segundo médico en el servicio 1 (tope 1). Se le dan las especialidades
    # requeridas para aislar la regla de cupos.
    t["personal"].append({"matricula": "541030000005", "nombre": "Pablo", "apellido": "Luna",
                          "telefono": "+5493433000005", "email": "m3@example.com",
                          "nacimiento": "1980-08-08", "rol": "Médico"})
    t["especializado_en"].append({"matricula_personal": "541030000005",
                                  "nombre_especialidad": "Pediatría"})
    t["personal_servicio"].append({"id_servicio": 1, "matricula_personal": "541030000005"})
    assert_dispara(t, "servicio", 0, "cupo_medicos")
    assert not [v for v in violaciones(t) if v.regla == "cupo_enfermeros"]


def test_cupo_enfermeros():
    t = tablas_ok()
    t["personal"].append({"matricula": "541030000006", "nombre": "Sara", "apellido": "Ibarra",
                          "telefono": "+5493433000006", "email": "e3@example.com",
                          "nacimiento": "1993-03-03", "rol": "Enfermero"})
    t["especializado_en"].append({"matricula_personal": "541030000006",
                                  "nombre_especialidad": "Pediatría"})
    t["personal_servicio"].append({"id_servicio": 1, "matricula_personal": "541030000006"})
    assert_dispara(t, "servicio", 0, "cupo_enfermeros")
    assert not [v for v in violaciones(t) if v.regla == "cupo_medicos"]


def test_estar_justo_en_el_tope_es_valido():
    # El dataset correcto ya tiene 1 médico y 1 enfermero con tope 1 y 1.
    assert not [v for v in violaciones(tablas_ok()) if v.regla.startswith("cupo_")]


# ---------------------------------------------------------------------------
# personal_servicio: un servicio por persona y especialidades
# ---------------------------------------------------------------------------

def test_un_servicio_por_persona():
    t = tablas_ok()
    t["personal_servicio"].append({"id_servicio": 2, "matricula_personal": "541030000001"})
    assert_dispara(t, "personal_servicio", 4, "un_servicio_por_persona")


@pytest.mark.parametrize("matricula, fila", [
    ("541030000001", 0),  # médico
    ("541030000002", 1),  # enfermero: también debe tener las especialidades
])
def test_especialidades_requeridas(matricula, fila):
    t = tablas_ok()
    t["especializado_en"] = [
        e for e in t["especializado_en"] if e["matricula_personal"] != matricula
    ]
    assert_dispara(t, "personal_servicio", fila, "especialidades_requeridas")


def test_tener_especialidades_de_mas_es_valido():
    t = tablas_ok()
    t["especializado_en"].append({"matricula_personal": "541030000001",
                                  "nombre_especialidad": "Cardiología"})
    assert not [v for v in violaciones(t) if v.regla == "especialidades_requeridas"]


# ---------------------------------------------------------------------------
# registro_hc: médico del servicio y horario
# ---------------------------------------------------------------------------

def test_registro_atendido_por_enfermero():
    t = tablas_ok()
    t["registro_hc"][0]["matricula_personal"] = "541030000002"
    assert_dispara(t, "registro_hc", 0, "registro_medico_del_servicio")


def test_registro_atendido_por_medico_de_otro_servicio():
    t = tablas_ok()
    t["registro_hc"][0]["matricula_personal"] = "541030000003"  # médico del servicio 2
    assert_dispara(t, "registro_hc", 0, "registro_medico_del_servicio")


def test_visita_en_dia_que_el_servicio_no_atiende():
    t = tablas_ok()
    t["registro_hc"][0]["dia_visita"] = "2026-11-18"  # miércoles; servicio 1: lunes y martes
    assert_dispara(t, "registro_hc", 0, "visita_en_horario")


def test_visita_fuera_de_la_franja_horaria():
    t = tablas_ok()
    t["registro_hc"][1]["dia_visita"] = "2026-11-17 17:00:00"  # martes, franja 08:00-16:00
    assert_dispara(t, "registro_hc", 1, "visita_en_horario")
    t["registro_hc"][1]["dia_visita"] = "2026-11-17 07:59:00"
    assert_dispara(t, "registro_hc", 1, "visita_en_horario")


def test_visita_en_los_bordes_de_la_franja_es_valida():
    t = tablas_ok()
    for hora in ("08:00:00", "16:00:00"):
        t["registro_hc"][1]["dia_visita"] = f"2026-11-17 {hora}"
        assert not [v for v in violaciones(t) if v.regla == "visita_en_horario"]


def test_visita_de_servicio_sin_horarios():
    t = tablas_ok()
    t["atencion_servicio"] = [a for a in t["atencion_servicio"] if a["id_servicio"] != 2]
    assert_dispara(t, "registro_hc", 2, "visita_en_horario")


def test_visita_solo_con_fecha_se_valida_por_dia_de_semana():
    t = tablas_ok()  # registro 0: fecha sin hora, lunes, franja 07:00-13:00
    assert not [v for v in violaciones(t) if v.regla == "visita_en_horario"]


# ---------------------------------------------------------------------------
# internacion
# ---------------------------------------------------------------------------

def test_ingreso_igual_a_visita():
    t = tablas_ok()
    t["internacion"][0]["fecha_ingreso"] = "2026-11-15"
    assert_dispara(t, "internacion", 0, "ingreso_igual_a_visita")


def test_ingreso_igual_a_visita_compara_tambien_la_hora():
    t = tablas_ok()
    t["internacion"][1]["fecha_ingreso"] = "2026-11-17 11:30:00"
    assert_dispara(t, "internacion", 1, "ingreso_igual_a_visita")


def test_egreso_anterior_al_ingreso():
    t = tablas_ok()
    t["internacion"][0]["fecha_egreso"] = "2026-11-15"
    assert_dispara(t, "internacion", 0, "egreso_posterior_a_ingreso")


def test_egreso_igual_al_ingreso_es_valido():
    t = tablas_ok()  # el trigger exige egreso >= ingreso
    t["internacion"][0]["fecha_egreso"] = "2026-11-16"
    assert not [v for v in violaciones(t) if v.regla == "egreso_posterior_a_ingreso"]


def test_registro_internado_dos_veces():
    t = tablas_ok()
    t["internacion"].append({"id": 3, "id_registro_hc": 1, "fecha_ingreso": "2026-11-16",
                             "fecha_egreso": None})
    assert_dispara(t, "internacion", 2, "internacion_registro_unico")


def test_internacion_en_servicio_que_no_interna():
    t = tablas_ok()
    # registro 3 es del servicio 2 (Cardiología, interna=False)
    t["internacion"].append({"id": 3, "id_registro_hc": 3, "fecha_ingreso": "2026-11-04",
                             "fecha_egreso": "2026-11-06"})
    assert_dispara(t, "internacion", 2, "internacion_servicio_interna")


def test_internacion_sin_solapamiento_pasada_y_pasada():
    t = tablas_ok()
    # Paciente 30000001: otra internación (registro 4, 9/11) que dura hasta el 17/11,
    # o sea que pisa a la del registro 1 (16 al 20 de noviembre).
    t["internacion"].append({"id": 3, "id_registro_hc": 4, "fecha_ingreso": "2026-11-09",
                             "fecha_egreso": "2026-11-17"})
    v = assert_dispara(t, "internacion", 0, "internacion_sin_solapamiento")
    assert not [x for x in v if x.tabla == "internacion" and x.fila == 2
                and x.regla == "internacion_sin_solapamiento"]


def test_internacion_sin_solapamiento_con_una_activa():
    t = tablas_ok()
    # Paciente 30000002 está internado desde el 17/11 (activa, fila 1). Otra
    # internación suya del 10/11 al 18/11 llega hasta después de ese ingreso.
    t["registro_hc"].append({"id_servicio": 1, "dni_paciente": 30000002,
                             "matricula_personal": "541030000001",
                             "dia_visita": "2026-11-10", "diagnostico": "d", "tratamiento": "t"})
    t["internacion"].append({"id": 3, "id_registro_hc": 5, "fecha_ingreso": "2026-11-10",
                             "fecha_egreso": "2026-11-18"})
    assert_dispara(t, "internacion", 1, "internacion_sin_solapamiento")


def test_dos_internaciones_activas_del_mismo_paciente():
    t = tablas_ok()
    t["registro_hc"].append({"id_servicio": 1, "dni_paciente": 30000002,
                             "matricula_personal": "541030000001",
                             "dia_visita": "2026-11-10", "diagnostico": "d", "tratamiento": "t"})
    t["internacion"].append({"id": 3, "id_registro_hc": 5, "fecha_ingreso": "2026-11-10",
                             "fecha_egreso": None})
    assert_dispara(t, "internacion", 1, "internacion_sin_solapamiento")


def test_internaciones_consecutivas_sin_pisarse_son_validas():
    t = tablas_ok()
    # Paciente 30000001: ya tiene 16/11 al 20/11; la nueva va del 9/11 al 15/11.
    t["registro_hc"].append({"id_servicio": 1, "dni_paciente": 30000001,
                             "matricula_personal": "541030000001",
                             "dia_visita": "2026-11-09", "diagnostico": "d", "tratamiento": "t"})
    t["internacion"].append({"id": 3, "id_registro_hc": 5, "fecha_ingreso": "2026-11-09",
                             "fecha_egreso": "2026-11-15"})
    assert violaciones(t) == []
