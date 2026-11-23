"""Test cases para el issue #17: Reparación automática y reporte.

Verifica:
- Sobre datos correctos no agrega nada.
- Con datos rotos a propósito (especialidades, horarios, FK a especialidad)
  repara solo agregando filas y el resultado pasa el validador.
- Completa los conteos por debajo del objetivo (personal_servicio,
  atencion_servicio, especializado_en, registro_hc, internacion 40/110).
- Nunca borra ni modifica lo existente, y no toca las tablas recibidas.
- Aborta con el detalle cuando no se puede reparar sin modificar/borrar, y
  cuando se agota el tope de iteraciones.
- Reporte por tabla: Excel | generado | diferencia.
- Es reproducible con la misma semilla.
"""

import copy
import random
from datetime import date, timedelta

import pytest

import reparar as modulo_reparar
from config import INTERNACION_ACTUAL_DIAS
from reparar import ReparacionFallida, Resultado, reparar, reporte
from validar import DIAS, validar

HOY = date(2026, 11, 22)  # domingo


# ---------------------------------------------------------------------------
# Dataset correcto, armado por código
# ---------------------------------------------------------------------------

def tablas_base() -> dict:
    """3 centros-servicios, 12 personas (2 sin servicio), 40 visitas, 6 internaciones."""
    t: dict = {}
    t["departamento"] = [{"id": 1, "nombre": "Paraná"}]
    t["ciudad"] = [{"id": 1, "id_departamento": 1, "nombre": "Paraná"}]
    t["barrio"] = [{"id": 1, "id_ciudad": 1, "nombre": "Barrio A"},
                   {"id": 2, "id_ciudad": 1, "nombre": "Barrio B"}]
    t["obra_social"] = [{"id": 1, "razon_social": "OSDE", "estado": True}]
    t["paciente"] = [
        {"dni": 30_000_000 + i, "id_obra_social": 1 if i % 2 else None, "nombre": f"Pac{i}",
         "apellido": f"Ape{i}", "nacimiento": "1980-01-01",
         "num_asociado": 1000 + i if i % 2 else None}
        for i in range(30)
    ]
    t["centro_de_salud"] = [
        {"id": 1, "id_barrio": 1, "nombre": "Centro 1", "direccion": "Calle 1 100",
         "inaguracion": "1990-01-01", "calle": "Calle 1", "altura": 100},
        {"id": 2, "id_barrio": 2, "nombre": "Centro 2", "direccion": "Calle 2 200",
         "inaguracion": "1990-01-01", "calle": "Calle 2", "altura": 200},
    ]
    t["tipo_servicio"] = [
        {"nombre": "Clinica A", "num_medicos": 2, "num_enfermeros": 2, "interna": True},
        {"nombre": "Clinica B", "num_medicos": 2, "num_enfermeros": 2, "interna": True},
        {"nombre": "Consultorio", "num_medicos": 2, "num_enfermeros": 2, "interna": False},
    ]
    t["especialidad"] = [{"nombre": f"Esp{i}"} for i in range(1, 5)]
    t["especialidad_requerida"] = [
        {"nombre_tipo_servicio": "Clinica A", "nombre_especialidad": "Esp1"},
        {"nombre_tipo_servicio": "Clinica B", "nombre_especialidad": "Esp2"},
        {"nombre_tipo_servicio": "Consultorio", "nombre_especialidad": "Esp3"},
    ]
    # Personas 0-5 médicos, 6-11 enfermeros. Las 5 y 11 no tienen servicio.
    t["personal"] = [
        {"matricula": f"5410300{i:05d}", "nombre": f"Per{i}", "apellido": f"Son{i}",
         "telefono": f"+5493433{i:06d}", "email": f"p{i}@example.com",
         "nacimiento": "1985-05-05", "rol": "Médico" if i < 6 else "Enfermero"}
        for i in range(12)
    ]
    mat = [p["matricula"] for p in t["personal"]]
    asignacion = {1: [0, 1, 6, 7], 2: [2, 3, 8, 9], 3: [4, 10]}
    esp_de_servicio = {1: "Esp1", 2: "Esp2", 3: "Esp3"}
    t["servicio"] = [
        {"id": 1, "id_centro_salud": 1, "nombre_tipo_servicio": "Clinica A",
         "matricula_encargado": mat[0]},
        {"id": 2, "id_centro_salud": 1, "nombre_tipo_servicio": "Clinica B",
         "matricula_encargado": mat[2]},
        {"id": 3, "id_centro_salud": 2, "nombre_tipo_servicio": "Consultorio",
         "matricula_encargado": mat[4]},
    ]
    t["personal_servicio"] = [
        {"id_servicio": s, "matricula_personal": mat[i]}
        for s, personas in asignacion.items() for i in personas
    ]
    t["especializado_en"] = [
        {"matricula_personal": mat[i], "nombre_especialidad": esp_de_servicio[s]}
        for s, personas in asignacion.items() for i in personas
    ]
    # 7 días x 2 franjas: id = 2*dia + 1 (mañana) y 2*dia + 2 (tarde).
    t["horario_atencion"] = [
        {"id": 2 * d + 1 + k, "apertura": ap, "cierre": ci, "dia": DIAS[d]}
        for d in range(7) for k, (ap, ci) in enumerate([("07:00", "13:00"), ("13:00", "19:00")])
    ]
    t["atencion_centro"] = [{"id_centro_salud": 1, "id_horario": 1},
                            {"id_centro_salud": 2, "id_horario": 2}]
    horarios_servicio = {1: [1, 3, 5], 2: [7, 9, 2], 3: [4, 6, 8]}
    t["atencion_servicio"] = [{"id_servicio": s, "id_horario": h}
                              for s, hs in horarios_servicio.items() for h in hs]

    dias_de = {s: {DIAS.index(next(x["dia"] for x in t["horario_atencion"] if x["id"] == h))
                   for h in hs} for s, hs in horarios_servicio.items()}
    medicos = {s: [mat[i] for i in personas if i < 6] for s, personas in asignacion.items()}

    registros = []
    for k in range(40):
        s = 1 + k % 3
        atras = 3 + k if k < 12 else 25 + 6 * (k - 12)  # las 12 primeras son recientes
        fecha = HOY - timedelta(days=atras)
        while fecha.weekday() not in dias_de[s]:
            fecha -= timedelta(days=1)
        registros.append({
            "id_servicio": s, "dni_paciente": 30_000_000 + k % 30,
            "matricula_personal": medicos[s][k % len(medicos[s])],
            "dia_visita": fecha.isoformat(),
            "diagnostico": f"Dx {s}", "tratamiento": f"Tx {s}",
        })
    t["registro_hc"] = registros

    def internacion(id_, k, egreso_dias):
        ingreso = date.fromisoformat(registros[k]["dia_visita"])
        return {"id": id_, "id_registro_hc": k + 1, "fecha_ingreso": registros[k]["dia_visita"],
                "fecha_egreso": None if egreso_dias is None
                else (ingreso + timedelta(days=egreso_dias)).isoformat()}

    # Registros 0 y 1 -> actuales; 3, 4, 6 y 7 -> pasadas (servicios 1 y 2 internan).
    t["internacion"] = [internacion(1, 0, None), internacion(2, 1, None),
                        internacion(3, 3, 2), internacion(4, 4, 2),
                        internacion(5, 6, 2), internacion(6, 7, 2)]
    return t


def objetivos_actuales(t: dict, **cambios) -> dict:
    """Objetivos = conteos actuales, con los cambios pedidos."""
    obj = {nombre: len(filas) for nombre, filas in t.items()}
    obj.update(cambios)
    return obj


def correr(t: dict, objetivos: dict | None = None, **kw) -> Resultado:
    kw.setdefault("hoy", HOY)
    kw.setdefault("seed", 1)
    return reparar(t, objetivos=objetivos if objetivos is not None else objetivos_actuales(t),
                   internaciones_actuales=2, internaciones_pasadas=4, **kw)


def sin_romper(original: dict, resultado: dict) -> None:
    """Solo se agregó: cada tabla original es prefijo exacto de la reparada."""
    for nombre, filas in original.items():
        assert resultado[nombre][:len(filas)] == filas, f"{nombre}: se modificó o borró algo"


# ---------------------------------------------------------------------------
# Fixture y casos sin cambios
# ---------------------------------------------------------------------------

def test_el_dataset_base_es_valido():
    assert validar(tablas_base(), hoy=HOY) == []


def test_datos_correctos_no_agregan_nada():
    t = tablas_base()
    r = correr(t)
    assert sum(r.agregadas.values()) == 0
    assert r.acciones == []
    assert r.tablas == t


def test_no_modifica_las_tablas_recibidas():
    t = tablas_base()
    t["especializado_en"] = t["especializado_en"][:-3]
    copia = copy.deepcopy(t)
    r = correr(t)
    assert t == copia  # ni listas ni filas
    assert r.tablas is not t
    assert len(r.tablas["especializado_en"]) > len(t["especializado_en"])


# ---------------------------------------------------------------------------
# Arreglos por violación
# ---------------------------------------------------------------------------

def test_repara_especialidad_faltante_de_medico_y_enfermero():
    t = tablas_base()
    quitadas = [e for e in t["especializado_en"]
                if e["matricula_personal"] in (t["personal"][0]["matricula"],
                                               t["personal"][6]["matricula"])]
    t["especializado_en"] = [e for e in t["especializado_en"] if e not in quitadas]
    assert {v.regla for v in validar(t, hoy=HOY)} == {"especialidades_requeridas"}

    r = correr(t)
    assert validar(r.tablas, hoy=HOY) == []
    assert r.agregadas == {"especializado_en": 2}
    assert all(q in r.tablas["especializado_en"] for q in quitadas)
    sin_romper(t, r.tablas)


def test_repara_fk_a_especialidad_agregando_la_especialidad():
    t = tablas_base()
    t["especialidad"] = [e for e in t["especialidad"] if e["nombre"] != "Esp2"]
    assert any(v.regla == "fk" for v in validar(t, hoy=HOY))

    r = correr(t)
    assert validar(r.tablas, hoy=HOY) == []
    assert {"nombre": "Esp2"} in r.tablas["especialidad"]
    assert r.agregadas == {"especialidad": 1}
    sin_romper(t, r.tablas)


def test_repara_visita_en_dia_que_el_servicio_no_atiende():
    t = tablas_base()
    # El servicio 1 atiende lunes, martes y miércoles (mañana): se le quitan los tres.
    t["atencion_servicio"] = [a for a in t["atencion_servicio"] if a["id_servicio"] != 1]
    assert any(v.regla == "visita_en_horario" for v in validar(t, hoy=HOY))

    r = correr(t)
    assert validar(r.tablas, hoy=HOY) == []
    nuevas = r.tablas["atencion_servicio"][len(t["atencion_servicio"]):]
    assert nuevas and all(a["id_servicio"] == 1 for a in nuevas)
    assert set(r.agregadas) == {"atencion_servicio"}
    sin_romper(t, r.tablas)


def test_no_agrega_horarios_de_mas_para_visitas_del_mismo_dia():
    t = tablas_base()
    t["atencion_servicio"] = [a for a in t["atencion_servicio"] if a["id_servicio"] != 1]
    r = correr(t)
    visitas_s1 = [x for x in t["registro_hc"] if x["id_servicio"] == 1]
    dias_visitados = {DIAS[date.fromisoformat(x["dia_visita"]).weekday()] for x in visitas_s1}
    assert r.agregadas["atencion_servicio"] == len(dias_visitados)


def test_repara_visita_con_hora_fuera_de_la_franja():
    t = tablas_base()
    # Servicio 1 atiende el lunes de 07:00 a 13:00; la visita es el lunes a las 15:00.
    lunes = next(x for x in t["registro_hc"]
                 if x["id_servicio"] == 1 and date.fromisoformat(x["dia_visita"]).weekday() == 0)
    nueva = dict(lunes, dia_visita=lunes["dia_visita"] + " 15:00:00")
    t["registro_hc"] = t["registro_hc"] + [nueva]
    assert any(v.regla == "visita_en_horario" for v in validar(t, hoy=HOY))

    r = correr(t)
    assert validar(r.tablas, hoy=HOY) == []
    agregadas = r.tablas["atencion_servicio"][len(t["atencion_servicio"]):]
    assert [a["id_horario"] for a in agregadas] == [2]  # lunes de 13:00 a 19:00
    sin_romper(t, r.tablas)


# ---------------------------------------------------------------------------
# Completar conteos
# ---------------------------------------------------------------------------

def test_completa_especializado_en():
    t = tablas_base()
    r = correr(t, objetivos_actuales(t, especializado_en=len(t["especializado_en"]) + 3))
    assert len(r.tablas["especializado_en"]) == len(t["especializado_en"]) + 3
    assert validar(r.tablas, hoy=HOY) == []
    roles = {p["matricula"]: p["rol"] for p in t["personal"]}
    nuevas = r.tablas["especializado_en"][len(t["especializado_en"]):]
    assert all(roles[e["matricula_personal"]] == "Médico" for e in nuevas)
    sin_romper(t, r.tablas)


def test_completa_atencion_servicio():
    t = tablas_base()
    r = correr(t, objetivos_actuales(t, atencion_servicio=len(t["atencion_servicio"]) + 4))
    assert len(r.tablas["atencion_servicio"]) == len(t["atencion_servicio"]) + 4
    assert validar(r.tablas, hoy=HOY) == []
    sin_romper(t, r.tablas)


def test_completa_personal_servicio_otorgando_las_especialidades_que_faltan():
    t = tablas_base()
    r = correr(t, objetivos_actuales(t, personal_servicio=len(t["personal_servicio"]) + 2))
    assert len(r.tablas["personal_servicio"]) == len(t["personal_servicio"]) + 2
    asignadas = {p["matricula_personal"] for p in r.tablas["personal_servicio"]}
    assert t["personal"][5]["matricula"] in asignadas
    assert t["personal"][11]["matricula"] in asignadas
    assert validar(r.tablas, hoy=HOY) == []  # cupos y especialidades al día
    assert r.agregadas["especializado_en"] == 2  # una por cada nueva asignación
    sin_romper(t, r.tablas)


def test_completa_registro_hc():
    t = tablas_base()
    r = correr(t, objetivos_actuales(t, registro_hc=len(t["registro_hc"]) + 10))
    assert len(r.tablas["registro_hc"]) == len(t["registro_hc"]) + 10
    assert validar(r.tablas, hoy=HOY) == []
    nuevos = r.tablas["registro_hc"][len(t["registro_hc"]):]
    assert all(date.fromisoformat(x["dia_visita"]) < HOY for x in nuevos)
    sin_romper(t, r.tablas)


def test_completa_internaciones_primero_sobre_registros_existentes():
    t = tablas_base()
    t["internacion"] = t["internacion"][1:5]  # quita 1 actual y 1 pasada
    r = correr(t, objetivos_actuales(t, internacion=6))
    internaciones = r.tablas["internacion"]
    assert len(internaciones) == 6
    assert sum(1 for n in internaciones if n["fecha_egreso"] is None) == 2
    assert validar(r.tablas, hoy=HOY) == []
    # Había registros elegibles: no se crearon registros nuevos (se prefiere agregar menos filas).
    assert len(r.tablas["registro_hc"]) == len(t["registro_hc"])
    assert r.agregadas == {"internacion": 2}
    sin_romper(t, r.tablas)


def test_internaciones_actuales_son_recientes_y_pasadas_cierran_antes_de_hoy():
    t = tablas_base()
    t["internacion"] = []
    r = correr(t, objetivos_actuales(t, internacion=6))
    desde = HOY - timedelta(days=INTERNACION_ACTUAL_DIAS[1])
    for n in r.tablas["internacion"]:
        ingreso = date.fromisoformat(n["fecha_ingreso"][:10])
        if n["fecha_egreso"] is None:
            assert ingreso >= desde
        else:
            assert ingreso < date.fromisoformat(n["fecha_egreso"][:10]) < HOY
    assert validar(r.tablas, hoy=HOY) == []


def test_internaciones_crea_registros_nuevos_si_no_hay_elegibles():
    t = tablas_base()
    # ids explícitos para poder sacar registros sin correr las posiciones.
    for pos, r in enumerate(t["registro_hc"], start=1):
        r["id"] = pos
    internados = {n["id_registro_hc"] for n in t["internacion"]}
    interna = {1: True, 2: True, 3: False}
    t["registro_hc"] = [r for r in t["registro_hc"]
                        if r["id"] in internados or not interna[r["id_servicio"]]]
    t["internacion"] = t["internacion"][2:]  # quedan 4 pasadas; faltan las 2 actuales
    # Los registros de las 2 actuales quitadas (ids 1 y 2) se sacan también: no quedan candidatos.
    t["registro_hc"] = [r for r in t["registro_hc"] if r["id"] not in {1, 2}]
    registros_antes = len(t["registro_hc"])

    r = correr(t, objetivos_actuales(t, internacion=6))
    assert sum(1 for n in r.tablas["internacion"] if n["fecha_egreso"] is None) == 2
    assert len(r.tablas["registro_hc"]) == registros_antes + 2  # 1 registro nuevo por internación
    assert r.agregadas == {"registro_hc": 2, "internacion": 2}
    ids = [x["id"] for x in r.tablas["registro_hc"]]
    assert len(ids) == len(set(ids))  # ids nuevos sin repetir
    assert validar(r.tablas, hoy=HOY) == []
    sin_romper(t, r.tablas)


def test_registros_nuevos_sin_id_explicito_usan_la_posicion_como_id():
    """Sin columna `id`, el registro nuevo va al final y su id es su posición."""
    t = tablas_base()
    t["registro_hc"] = t["registro_hc"][:3]  # recortar por el final no corre posiciones
    t["internacion"] = []
    assert not any("id" in r for r in t["registro_hc"])

    r = correr(t, objetivos_actuales(t, internacion=6))
    assert len(r.tablas["internacion"]) == 6
    assert len(r.tablas["registro_hc"]) > 3                      # hubo que crear registros
    assert not any("id" in x for x in r.tablas["registro_hc"])   # y siguen sin `id`
    total = len(r.tablas["registro_hc"])
    assert all(1 <= n["id_registro_hc"] <= total for n in r.tablas["internacion"])
    assert validar(r.tablas, hoy=HOY) == []
    sin_romper(t, r.tablas)


def test_no_agrega_nada_si_el_objetivo_ya_se_alcanzo_o_se_supero():
    t = tablas_base()
    r = correr(t, objetivos_actuales(t, registro_hc=5, especializado_en=1, atencion_servicio=1,
                                     personal_servicio=1))
    assert sum(r.agregadas.values()) == 0


def test_tabla_sin_objetivo_no_se_completa():
    t = tablas_base()
    obj = objetivos_actuales(t)
    del obj["registro_hc"], obj["internacion"]
    t["internacion"] = t["internacion"][:2]
    r = correr(t, obj)
    assert len(r.tablas["internacion"]) == 2 and len(r.tablas["registro_hc"]) == 40


# ---------------------------------------------------------------------------
# Varios problemas a la vez
# ---------------------------------------------------------------------------

def test_repara_varios_problemas_juntos_y_reporta_los_desvios():
    t = tablas_base()
    t["especializado_en"] = t["especializado_en"][:-4]
    t["atencion_servicio"] = [a for a in t["atencion_servicio"] if a["id_servicio"] != 2]
    t["internacion"] = t["internacion"][:-2]
    obj = objetivos_actuales(t, internacion=6, atencion_servicio=9, especializado_en=12)

    r = correr(t, obj)
    assert validar(r.tablas, hoy=HOY) == []
    assert len(r.tablas["internacion"]) == 6
    sin_romper(t, r.tablas)

    texto = r.reporte()
    linea = next(l for l in texto.splitlines() if l.startswith("especializado_en"))
    assert linea.split()[1:3] == ["12", str(len(r.tablas["especializado_en"]))]
    assert "Filas agregadas por la reparación" in texto
    assert r.iteraciones >= 2


# ---------------------------------------------------------------------------
# Lo que no se puede reparar: aborta con detalle
# ---------------------------------------------------------------------------

def test_aborta_si_la_violacion_exige_modificar_o_borrar():
    t = tablas_base()
    t["paciente"][3]["nombre"] = "x" * 40                       # largo
    t["atencion_servicio"].append(dict(t["atencion_servicio"][0]))  # PK repetida
    with pytest.raises(ReparacionFallida) as info:
        correr(t)
    e = info.value
    reglas = {(v.regla, v.tabla) for v in e.violaciones}
    assert reglas == {("largo_maximo", "paciente"), ("unique", "atencion_servicio")}
    mensaje = str(e)
    assert "largo_maximo en paciente" in mensaje and "unique en atencion_servicio" in mensaje
    assert "[paciente fila 3]" in mensaje          # ejemplo con tabla y fila
    assert "No se emite el SQL" in mensaje
    assert e.iteraciones >= 1


def test_arregla_lo_reparable_y_aborta_solo_por_lo_demas():
    t = tablas_base()
    t["especializado_en"] = t["especializado_en"][:-2]   # reparable
    t["paciente"][0]["nombre"] = "x" * 40               # no reparable
    with pytest.raises(ReparacionFallida) as info:
        correr(t)
    assert {v.regla for v in info.value.violaciones} == {"largo_maximo"}
    # lo reparable sí se alcanzó a arreglar en el resultado parcial
    assert info.value.parcial.agregadas["especializado_en"] == 2


def test_aborta_si_ningun_horario_existente_atiende_ese_dia():
    t = tablas_base()
    t["horario_atencion"] = [h for h in t["horario_atencion"] if h["dia"] != "Lunes"]
    # Los horarios 1 y 2 eran los del lunes: también se sacan de donde se referencian.
    t["atencion_servicio"] = [a for a in t["atencion_servicio"] if a["id_horario"] not in (1, 2)]
    t["atencion_centro"] = [a for a in t["atencion_centro"] if a["id_horario"] not in (1, 2)]
    with pytest.raises(ReparacionFallida) as info:
        correr(t)
    assert {v.regla for v in info.value.violaciones} == {"visita_en_horario"}


def test_fk_a_una_tabla_con_datos_propios_no_se_inventa():
    t = tablas_base()
    t["paciente"][0]["id_obra_social"] = 99
    with pytest.raises(ReparacionFallida) as info:
        correr(t)
    assert {(v.regla, v.tabla) for v in info.value.violaciones} == {("fk", "paciente")}


def test_fecha_futura_no_se_puede_reparar():
    t = tablas_base()
    t["registro_hc"][5]["dia_visita"] = (HOY + timedelta(days=3)).isoformat()
    with pytest.raises(ReparacionFallida) as info:
        correr(t)
    assert "fecha_anterior_a_hoy" in {v.regla for v in info.value.violaciones}


def test_aborta_al_agotar_el_tope_de_iteraciones(monkeypatch):
    """Un arreglo que siempre agrega filas pero nunca resuelve termina en el tope."""
    def arreglo_inutil(ctx, v):
        ctx.agregar("especialidad", {"nombre": f"X{ctx.total_agregado()}"}, "relleno inútil")
        return True

    monkeypatch.setitem(modulo_reparar._REPARADORES, "especialidades_requeridas", arreglo_inutil)
    t = tablas_base()
    t["especializado_en"] = t["especializado_en"][:-1]
    with pytest.raises(ReparacionFallida) as info:
        correr(t, max_iteraciones=3)
    assert info.value.iteraciones == 3
    assert "tope de 3 iteraciones" in str(info.value)
    assert {v.regla for v in info.value.violaciones} == {"especialidades_requeridas"}


def test_el_tope_por_defecto_viene_de_config(monkeypatch):
    monkeypatch.setattr(modulo_reparar, "MAX_ITERACIONES_REPARACION", 2)
    monkeypatch.setitem(modulo_reparar._REPARADORES, "especialidades_requeridas",
                        lambda ctx, v: ctx.agregar("especialidad", {"nombre": "Y"}, "x") or True)
    t = tablas_base()
    t["especializado_en"] = t["especializado_en"][:-1]
    with pytest.raises(ReparacionFallida) as info:
        correr(t)
    assert info.value.iteraciones == 2


def test_el_mensaje_limita_los_ejemplos_por_regla():
    t = tablas_base()
    for p in t["paciente"][:6]:
        p["nombre"] = "x" * 40
    with pytest.raises(ReparacionFallida) as info:
        correr(t)
    assert "largo_maximo en paciente: 6 fila(s)" in str(info.value)
    assert "... y 3 más" in str(info.value)
    assert len(info.value.violaciones) == 6  # el detalle completo está en la excepción


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

def test_reporte_muestra_excel_generado_y_diferencia():
    tablas = {"departamento": [{}] * 15, "especializado_en": [{}] * 327, "paciente": [{}] * 398}
    obj = {"departamento": 15, "especializado_en": 320, "paciente": 400}
    texto = reporte(tablas, obj, {"especializado_en": 7})
    lineas = texto.splitlines()
    assert lineas[0].split() == ["Tabla", "Excel", "Generado", "Dif."]
    assert next(l for l in lineas if l.startswith("departamento")).split() == ["departamento", "15", "15", "0"]
    assert next(l for l in lineas if l.startswith("especializado_en")).split() == [
        "especializado_en", "320", "327", "+7"]
    assert next(l for l in lineas if l.startswith("paciente")).split() == ["paciente", "400", "398", "-2"]
    assert next(l for l in lineas if l.startswith("Total")).split() == ["Total", "735", "740", "+5"]
    assert "especializado_en +7" in texto


def test_reporte_sin_reparaciones_lo_dice():
    assert "no agregó filas" in reporte({"departamento": [{}]}, {"departamento": 1})


def test_reporte_informa_actuales_y_pasadas():
    t = tablas_base()
    assert "Internaciones: 2 actuales + 4 pasadas" in reporte(t, objetivos_actuales(t))


def test_reporte_usa_los_totales_de_config_por_defecto():
    from config import TOTALES
    texto = reporte({})
    for nombre in TOTALES:
        assert nombre in texto


# ---------------------------------------------------------------------------
# Reproducibilidad
# ---------------------------------------------------------------------------

def _caso_roto():
    t = tablas_base()
    t["internacion"] = t["internacion"][1:5]
    t["atencion_servicio"] = [a for a in t["atencion_servicio"] if a["id_servicio"] != 1]
    return t, objetivos_actuales(t, internacion=6, registro_hc=50, especializado_en=12)


def test_misma_semilla_mismo_resultado():
    t, obj = _caso_roto()
    a = correr(t, obj, seed=5)
    b = correr(t, obj, seed=5)
    assert a.tablas == b.tablas and a.acciones == b.acciones


def test_distinta_semilla_puede_cambiar_lo_que_se_agrega():
    t, obj = _caso_roto()
    a = correr(t, obj, seed=1).tablas
    b = correr(t, obj, seed=2).tablas
    assert a != b
    assert validar(a, hoy=HOY) == [] and validar(b, hoy=HOY) == []
