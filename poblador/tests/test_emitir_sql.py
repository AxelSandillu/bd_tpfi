"""Pruebas unitarias del emisor SQL (issue #17)."""

from datetime import date, datetime, time

import pytest

from emitir_sql import (
    COLUMNAS_TABLAS,
    ORDEN_TABLAS,
    TABLAS_IDENTITY,
    _generar_insert,
    _generar_setval,
    _sql_fila,
    _sql_valor,
    emitir,
)


def test_orden_de_emision_es_el_acordado():
    assert ORDEN_TABLAS == (
        "departamento", "ciudad", "barrio", "obra_social", "paciente",
        "centro_de_salud", "personal", "especialidad", "especializado_en",
        "tipo_servicio", "especialidad_requerida", "horario_atencion",
        "atencion_centro", "servicio", "atencion_servicio", "personal_servicio",
        "registro_hc", "internacion",
    )


def test_se_definen_las_columnas_de_las_18_tablas():
    assert len(COLUMNAS_TABLAS) == 18
    assert COLUMNAS_TABLAS["tipo_servicio"] == ("nombre", "num_enfermeros", "num_medicos")
    assert "peso" not in COLUMNAS_TABLAS["tipo_servicio"]
    assert "interna" not in COLUMNAS_TABLAS["tipo_servicio"]
    assert "id" not in COLUMNAS_TABLAS["paciente"]


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (None, "NULL"),
        (True, "TRUE"),
        (False, "FALSE"),
        (42, "42"),
        (3.5, "3.5"),
        ("Entre Ríos", "'Entre Ríos'"),
        ("O'Brien", "'O''Brien'"),
        (date(2020, 2, 3), "'2020-02-03'"),
        (time(8, 30), "'08:30:00'"),
        (datetime(2020, 2, 3, 8, 30), "'2020-02-03 08:30:00'"),
    ],
)
def test_sql_valor_serializa_tipos(valor, esperado):
    assert _sql_valor(valor) == esperado


def test_sql_valor_rechaza_nul():
    with pytest.raises(ValueError, match="NUL"):
        _sql_valor("texto\x00invalido")


def test_sql_valor_rechaza_tipos_no_soportados():
    with pytest.raises(TypeError, match="no soportado"):
        _sql_valor([1, 2])


def test_sql_valor_rechaza_float_no_finito():
    with pytest.raises(ValueError, match="no finito"):
        _sql_valor(float("nan"))


def test_sql_fila_usa_columnas_reales_e_ignora_auxiliares():
    fila = {
        "nombre": "Clínica",
        "num_enfermeros": 3,
        "num_medicos": 2,
        "peso": 1.5,
        "interna": True,
        "casos": [],
    }
    assert _sql_fila("tipo_servicio", fila) == "('Clínica', 3, 2)"


def test_sql_fila_informa_columnas_faltantes():
    with pytest.raises(ValueError, match="Faltan columnas.*departamento"):
        _sql_fila("departamento", {"id": 1})


def test_insert_identity_incluye_overriding():
    sentencia = _generar_insert("departamento", [{"id": 1, "nombre": "Paraná"}], 500)[0]
    assert "OVERRIDING SYSTEM VALUE" in sentencia
    assert "INSERT INTO departamento (id, nombre)" in sentencia


def test_insert_paciente_no_incluye_overriding():
    fila = {
        "dni": 30123456,
        "id_obra_social": None,
        "nombre": "Ana",
        "apellido": "Pérez",
        "nacimiento": "1990-01-01",
        "num_asociado": None,
    }
    sentencia = _generar_insert("paciente", [fila], 500)[0]
    assert "OVERRIDING SYSTEM VALUE" not in sentencia
    assert "NULL" in sentencia


def test_insert_se_divide_en_lotes():
    filas = [{"nombre": f"Especialidad {i}"} for i in range(5)]
    sentencias = _generar_insert("especialidad", filas, 2)
    assert len(sentencias) == 3
    assert sum(sentencia.count("),") + 1 for sentencia in sentencias) == 5


def test_setval_se_genera_para_las_nueve_tablas_identity():
    sentencias = _generar_setval()
    assert len(TABLAS_IDENTITY) == 9
    assert len(sentencias) == 9
    assert all("pg_get_serial_sequence" in sentencia for sentencia in sentencias)
    assert all("MAX(id)" in sentencia for sentencia in sentencias)


def test_emitir_crea_un_archivo_con_transaccion_y_orden(tmp_path):
    destino = tmp_path / "02_seed.sql"
    datos = {
        "departamento": [{"id": 1, "nombre": "Paraná", "id_georef": 3001}],
        "paciente": [{
            "dni": 30123456,
            "id_obra_social": None,
            "nombre": "Ana",
            "apellido": "O'Brien",
            "nacimiento": "1990-01-01",
            "num_asociado": None,
        }],
        "especialidad": [{"nombre": "Pediatría"}],
    }

    resultado = emitir(datos, destino, tamano_lote=1)
    contenido = resultado.read_text(encoding="utf-8")

    assert resultado == destino
    assert contenido.startswith("-- Archivo generado")
    assert contenido.count("BEGIN;") == 1
    assert contenido.count("COMMIT;") == 1
    assert "'O''Brien'" in contenido
    assert "id_georef" not in contenido
    assert contenido.index("INSERT INTO departamento") < contenido.index("INSERT INTO paciente")
    assert contenido.index("INSERT INTO paciente") < contenido.index("INSERT INTO especialidad")
    assert contenido.rstrip().endswith("COMMIT;")


def test_emitir_admite_tablas_ausentes_como_vacias(tmp_path):
    destino = emitir({}, tmp_path / "vacio.sql")
    contenido = destino.read_text(encoding="utf-8")
    assert "BEGIN;" in contenido
    assert "COMMIT;" in contenido
    assert "INSERT INTO" not in contenido


def test_emitir_valida_tamano_de_lote(tmp_path):
    with pytest.raises(ValueError, match="tamano_lote"):
        emitir({}, tmp_path / "no.sql", tamano_lote=0)


def test_emitir_valida_tipo_de_entrada(tmp_path):
    with pytest.raises(TypeError, match="diccionario"):
        emitir([], tmp_path / "no.sql")


def test_emitir_valida_que_cada_tabla_sea_una_lista(tmp_path):
    with pytest.raises(TypeError, match="departamento"):
        emitir({"departamento": {}}, tmp_path / "no.sql")


def test_emitir_asigna_ids_a_registros_hc_si_el_generador_no_los_provee(tmp_path):
    destino = tmp_path / "02_seed.sql"
    fila = {
        "id_servicio": 1,
        "dni_paciente": 30123456,
        "matricula_personal": "541030123456",
        "dia_visita": "2025-01-01 09:00:00",
        "diagnostico": "Control",
        "tratamiento": "Seguimiento",
    }
    emitir({"registro_hc": [fila]}, destino)
    contenido = destino.read_text(encoding="utf-8")
    assert "INSERT INTO registro_hc (id, id_servicio" in contenido
    assert "OVERRIDING SYSTEM VALUE" in contenido
    assert "(1, 1, 30123456" in contenido
    assert "id" not in fila  # El emisor no modifica el dato original.


def test_emitir_asigna_ids_a_internaciones_si_faltan(tmp_path):
    destino = tmp_path / "02_seed.sql"
    fila = {
        "id_registro_hc": 1,
        "fecha_ingreso": "2025-01-01 09:00:00",
        "fecha_egreso": None,
    }
    emitir({"internacion": [fila]}, destino)
    contenido = destino.read_text(encoding="utf-8")
    assert "INSERT INTO internacion (id, id_registro_hc" in contenido
    assert "(1, 1, '2025-01-01 09:00:00', NULL)" in contenido
    assert "id" not in fila
