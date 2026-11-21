"""Generador de registros de historia clínica (registro_hc).

Genera 750 registros en memoria (reproducible con config.SEED):

- servicio → horario del servicio (define día y hora) → médico de ese
  servicio → paciente.
- La fecha es posterior a la inauguración del centro y al nacimiento del
  paciente, dentro de la ventana de visitas configurada.
- Diagnóstico y tratamiento salen de los `casos` del tipo de servicio.
- Primero se generan los 40 registros de internaciones actuales, con fechas
  recientes.

Depende de:
  - config.py (TOTALES, VENTANA_VISITAS_ANIOS, INTERNACIONES_ACTUALES,
    INTERNACION_ACTUAL_DIAS, SEED)
  - data/tipos_servicio.json (casos por tipo de servicio)
  - generadores.estructura_clinica (issue #12)
  - generadores.personal (issue #10)
  - generadores.pacientes (issue #9)
  - generadores.geografia (issue #8)
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path

from config import (
    SEED,
    TOTALES,
    VENTANA_VISITAS_ANIOS,
    INTERNACIONES_ACTUALES,
    INTERNACION_ACTUAL_DIAS,
)


def _cargar_tipos_servicio(ruta: str | None = None) -> dict:
    if ruta is None:
        from config import RUTA_TIPOS_SERVICIO
        ruta = RUTA_TIPOS_SERVICIO
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _hoy() -> date:
    from config import FECHA_REFERENCIA
    if FECHA_REFERENCIA is not None:
        return FECHA_REFERENCIA
    return date.today()


def _dia_siguiente(dia_objetivo: str, desde: date) -> date:
    """Devuelve la primera fecha >= `desde` cuyo nombre de día sea `dia_objetivo`."""
    DIAS_ES = {
        "Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3,
        "Viernes": 4, "Sábado": 5, "Domingo": 6,
    }
    target = DIAS_ES[dia_objetivo]
    d = desde
    while d.weekday() != target:
        d += timedelta(days=1)
    return d


def _fecha_aleatoria_dentro_ventana(
    fecha_minima: date,
    rng: random.Random,
) -> date:
    """Fecha aleatoria dentro de la ventana de visitas, anterior a hoy."""
    hoy = _hoy()
    inicio = max(fecha_minima, hoy - timedelta(days=365 * VENTANA_VISITAS_ANIOS))
    fin = hoy - timedelta(days=1)
    if fin < inicio:
        return inicio
    dias = (fin - inicio).days
    return inicio + timedelta(days=rng.randint(0, dias))


def _fecha_reciente(rng: random.Random) -> date:
    """Fecha reciente dentro de INTERNACION_ACTUAL_DIAS."""
    hoy = _hoy()
    dias_min, dias_max = INTERNACION_ACTUAL_DIAS
    atras = rng.randint(dias_min, dias_max)
    return hoy - timedelta(days=atras)


def generar_registro_hc(
    servicios: list[dict],
    personal_servicio: list[dict],
    personal: list[dict],
    horario_atencion: list[dict],
    atencion_servicio: list[dict],
    pacientes: list[dict],
    centros_de_salud: list[dict],
    tipo_servicio: list[dict],
    rng: random.Random | None = None,
) -> list[dict]:
    """Devuelve 750 registros de registro_hc.

    Cada registro: id, id_servicio, dni_paciente, matricula_personal,
    dia_visita, diagnostico, tratamiento.

    Reglas:
    - El médico debe trabajar en el servicio (está en personal_servicio).
    - La fecha cae en un día que coincida con horario.dia y dentro de
      apertura-cierre.
    - Fecha posterior a inauguración del centro y al nacimiento del paciente.
    - Dentro de los últimos VENTANA_VISITAS_ANIOS años y anterior a hoy.
    - Diagnóstico y tratamiento de un caso del tipo de servicio.
    - Los primeros INTERNACIONES_ACTUALES (40) son fechas recientes.
    """
    if rng is None:
        rng = random.Random(SEED)

    cantidad = TOTALES["registro_hc"]
    n_actuales = INTERNACIONES_ACTUALES

    # Indexar estructuras
    tipos_por_nombre = {t["nombre"]: t for t in tipo_servicio}
    centros_por_id = {c["id"]: c for c in centros_de_salud}
    horarios_por_id = {h["id"]: h for h in horario_atencion}

    # Horarios por servicio
    horarios_por_servicio: dict[int, list[dict]] = {}
    for a in atencion_servicio:
        horarios_por_servicio.setdefault(a["id_servicio"], []).append(
            horarios_por_id[a["id_horario"]]
        )

    # Médicos por servicio (matrícula)
    medicos_por_servicio: dict[int, list[str]] = {}
    medicos_set = {p["matricula"] for p in personal if p["rol"] == "Médico"}
    for ps in personal_servicio:
        if ps["matricula_personal"] in medicos_set:
            medicos_por_servicio.setdefault(ps["id_servicio"], []).append(
                ps["matricula_personal"]
            )

    # DNI de pacientes disponibles
    dnis_pacientes = [p["dni"] for p in pacientes]
    nacimientos_por_dni = {p["dni"]: date.fromisoformat(p["nacimiento"][:10])
                           for p in pacientes}

    hoy = _hoy()
    registros: list[dict] = []

    # Servicios que tienen horarios y médicos asignados (válidos para generar)
    servicios_validos = [
        s for s in servicios
        if s["id"] in horarios_por_servicio
        and s["id"] in medicos_por_servicio
        and medicos_por_servicio[s["id"]]
    ]
    if not servicios_validos:
        return registros

    def _crear_registro(servicio: dict, fecha: date) -> dict:
        tipo = tipos_por_nombre[servicio["nombre_tipo_servicio"]]
        caso = rng.choice(tipo["casos"])
        medico = rng.choice(medicos_por_servicio[servicio["id"]])
        paciente = rng.choice(dnis_pacientes)

        return {
            "id_servicio": servicio["id"],
            "dni_paciente": paciente,
            "matricula_personal": medico,
            "dia_visita": fecha.isoformat(),
            "diagnostico": caso["diagnostico"],
            "tratamiento": caso["tratamiento"],
        }

    def _fecha_valida(horario: dict, centro: dict, paciente_dni: int) -> date:
        """Fecha dentro de la ventana, posterior a inauguración y nacimiento."""
        fecha_inag = date.fromisoformat(centro["inaguracion"][:10])
        fecha_nac = nacimientos_por_dni[paciente_dni]
        fecha_min = max(fecha_inag, fecha_nac,
                        hoy - timedelta(days=365 * VENTANA_VISITAS_ANIOS))
        fecha = _fecha_aleatoria_dentro_ventana(fecha_min, rng)
        fecha = _dia_siguiente(horario["dia"], fecha)
        if fecha < fecha_inag or fecha < fecha_nac:
            fecha = _dia_siguiente(horario["dia"], max(fecha_inag, fecha_nac))
        return fecha

    # 1. Primero los registros de internaciones actuales (fechas recientes)
    for _ in range(n_actuales):
        servicio = rng.choice(servicios_validos)
        h_list = horarios_por_servicio[servicio["id"]]
        horario = rng.choice(h_list)
        paciente = rng.choice(dnis_pacientes)
        centro = centros_por_id[servicio["id_centro_salud"]]
        fecha_inag = date.fromisoformat(centro["inaguracion"][:10])
        fecha_nac = nacimientos_por_dni[paciente]
        fecha_min = max(fecha_inag, fecha_nac, hoy - timedelta(days=20))
        fecha = _fecha_reciente(rng)
        if fecha < fecha_min:
            fecha = fecha_min
        fecha = _dia_siguiente(horario["dia"], fecha)
        # No superar hoy
        if fecha >= hoy:
            fecha = hoy - timedelta(days=1)
            fecha = _dia_siguiente(horario["dia"], fecha_min)
        registros.append(_crear_registro(servicio, fecha))

    # 2. El resto (750 - 40 = 710) con fechas en ventana de visitas
    while len(registros) < cantidad:
        servicio = rng.choice(servicios_validos)
        h_list = horarios_por_servicio[servicio["id"]]
        horario = rng.choice(h_list)
        paciente = rng.choice(dnis_pacientes)
        fecha = _fecha_valida(horario, centros_por_id[servicio["id_centro_salud"]], paciente)
        registros.append(_crear_registro(servicio, fecha))

    return registros[:cantidad]


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def generar_registro_hc_completo(
    datos_estructura: dict | None = None,
    datos_pacientes: list[dict] | None = None,
    datos_geografia: dict | None = None,
    datos_json: dict | None = None,
    seed: int | None = None,
) -> dict:
    """Genera registro_hc en memoria usando datos de issues previos.

    Args:
        datos_estructura: salida de generar_estructura_clinica().
        datos_pacientes: salida de generar_pacientes().
        datos_geografia: salida de generar_geografia().
        datos_json: contenido de tipos_servicio.json.
        seed: semilla (si None, config.SEED).

    Devuelve dict con clave "registro_hc".
    """
    if seed is None:
        seed = SEED
    rng = random.Random(seed)

    if datos_estructura is None:
        from generadores.estructura_clinica import generar_estructura_clinica
        datos_estructura = generar_estructura_clinica(seed=seed)

    if datos_pacientes is None:
        from generadores.pacientes import generar_pacientes
        from generadores.obras_sociales import generar_obras_sociales
        obras = generar_obras_sociales(rng)
        datos_pacientes = generar_pacientes(obras, rng)

    if datos_geografia is None:
        from generadores.geografia import generar_geografia
        datos_geografia = generar_geografia(seed=seed)

    if datos_json is None:
        datos_json = _cargar_tipos_servicio()

    registros = generar_registro_hc(
        servicios=datos_estructura["servicio"],
        personal_servicio=datos_estructura["personal_servicio"],
        personal=datos_estructura["personal"],
        horario_atencion=datos_estructura["horario_atencion"],
        atencion_servicio=datos_estructura["atencion_servicio"],
        pacientes=datos_pacientes,
        centros_de_salud=datos_geografia["centro_de_salud"],
        tipo_servicio=datos_estructura["tipo_servicio"],
        rng=rng,
    )

    return {
        "registro_hc": registros,
    }
