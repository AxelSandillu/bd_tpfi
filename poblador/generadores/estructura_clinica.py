"""Generador de estructura clínica: servicios, horarios y asignaciones.

Genera en memoria (reproducible con config.SEED):

- tipo_servicio y especialidad_requerida ← data/tipos_servicio.json
- horario_atencion: 70 filas (7 días × 10 franjas, todas distintas)
- atencion_centro: un horario por centro (20)
- servicio: 70, pares (centro, tipo) únicos, todo centro con ≥1 servicio,
  tipos distribuidos según peso
- atencion_servicio: 160 (~2,3 por servicio)
- personal_servicio: 150. Primero un médico por servicio (encargado),
  luego se completa hasta los cupos. A cada persona se le otorgan las
  especialidades requeridas que le falten (genera filas de especializado_en).
- especializado_en: completar hasta 320 (300 base + 20 médicos con segunda).

Depende de:
  - config.py (TOTALES, FRANJAS_HORARIAS, etc.)
  - data/tipos_servicio.json (issue #3)
  - generadores.personal (issue #10)
  - generadores.geografia (issue #8)
  - generadores.pools (issue #11)
"""

import json
import random
from collections import defaultdict
from pathlib import Path

from config import (
    DIAS_SEMANA,
    FRANJAS_HORARIAS,
    SEED,
    TOTALES,
)


def _cargar_tipos_servicio(ruta: str | None = None) -> dict:
    if ruta is None:
        from config import RUTA_TIPOS_SERVICIO
        ruta = RUTA_TIPOS_SERVICIO
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. tipo_servicio y especialidad_requerida desde el JSON
# ---------------------------------------------------------------------------

def generar_tipo_servicio_y_especialidad_requerida(
    datos_json: dict | None = None,
) -> tuple[list[dict], list[dict]]:
    """Devuelve (tipo_servicio, especialidad_requerida) desde el JSON.

    tipo_servicio: id, nombre, num_medicos, num_enfermeros (20 filas)
    especialidad_requerida: nombre_tipo_servicio, nombre_especialidad (25 filas)
    """
    if datos_json is None:
        datos_json = _cargar_tipos_servicio()

    tipos = datos_json["tipos_servicio"]

    tipo_servicio = []
    for i, t in enumerate(tipos, start=1):
        tipo_servicio.append({
            "id": i,
            "nombre": t["nombre"],
            "num_medicos": t["num_medicos"],
            "num_enfermeros": t["num_enfermeros"],
            "especialidades_requeridas": t.get("especialidades_requeridas", []),
            "peso": t.get("peso", 1.0),
            "interna": t.get("interna", False),
        })

    especialidad_requerida = []
    for t in tipos:
        for esp in t["especialidades_requeridas"]:
            especialidad_requerida.append({
                "nombre_tipo_servicio": t["nombre"],
                "nombre_especialidad": esp,
            })

    return tipo_servicio, especialidad_requerida


# ---------------------------------------------------------------------------
# 2. horario_atencion: 70 = 7 días × 10 franjas
# ---------------------------------------------------------------------------

def generar_horario_atencion(rng: random.Random) -> list[dict]:
    """70 horarios: cada combinación (día, franja) es una fila distinta."""
    cantidad = TOTALES["horario_atencion"]
    horario = []
    id_ = 1
    for dia in DIAS_SEMANA:
        for apertura, cierre in FRANJAS_HORARIAS:
            horario.append({
                "id": id_,
                "apertura": apertura,
                "cierre": cierre,
                "dia": dia,
            })
            id_ += 1
    return horario[:cantidad]


# ---------------------------------------------------------------------------
# 3. atencion_centro: un horario por centro (20)
# ---------------------------------------------------------------------------

def generar_atencion_centro(
    centros: list[dict],
    horarios: list[dict],
    rng: random.Random,
) -> list[dict]:
    """Asigna un horario distinto a cada centro (20 filas)."""
    cantidad = TOTALES["atencion_centro"]
    atencion = []
    for i, centro in enumerate(centros[:cantidad], start=1):
        # Cada centro recibe un horario único del pool
        horario = horarios[(i - 1) % len(horarios)]
        atencion.append({
            "id_centro_salud": centro["id"],
            "id_horario": horario["id"],
        })
    return atencion


# ---------------------------------------------------------------------------
# 4. servicio: 70, pares (centro, tipo) únicos, distribuidos por peso
# ---------------------------------------------------------------------------

def _distribuir_servicios_por_peso(
    tipos: list[dict],
    total: int,
    rng: random.Random,
) -> list[str]:
    """Devuelve una lista de `total` nombres de tipo según pesos proporcionales."""
    pesos = [t.get("peso", 1.0) for t in tipos]
    suma_pesos = sum(pesos)
    if suma_pesos <= 0:
        pesos = [1.0] * len(tipos)
        suma_pesos = len(tipos)

    cuotas = []
    acumulado = 0
    for i, p in enumerate(pesos):
        exacto = p * total / suma_pesos
        cuota = int(exacto)
        cuotas.append((cuota, exacto - cuota, i))
    # Distribuir el resto por fracción más grande
    restante = total - sum(c[0] for c in cuotas)
    cuotas.sort(key=lambda x: -x[1])
    for i in range(restante):
        cuotas[i] = (cuotas[i][0] + 1, cuotas[i][1], cuotas[i][2])

    resultado = []
    for cuota, _, idx in cuotas:
        nombre_tipo = tipos[idx]["nombre"]
        resultado.extend([nombre_tipo] * cuota)
    rng.shuffle(resultado)
    return resultado


def generar_servicio(
    centros: list[dict],
    tipo_servicio: list[dict],
    rng: random.Random,
) -> list[dict]:
    """70 servicios con pares (centro, tipo) únicos.

    Todo centro tiene al menos un servicio. Tipos distribuidos según peso.
    Devuelve servicios con id, id_centro_salud, nombre_tipo_servicio,
    matricula_encargado (None por ahora, se llena en personal_servicio).
    """
    cantidad = TOTALES["servicio"]
    n_centros = len(centros)
    n_tipos = len(tipo_servicio)

    # Cada centro debe tener al menos un servicio
    tipos_por_peso = _distribuir_servicios_por_peso(tipo_servicio, cantidad, rng)

    # Construir pares (centro, tipo) únicos
    pares_usados = set()
    servicios = []

    # Primero asegurar un servicio por centro
    for i, centro in enumerate(centros):
        if len(servicios) >= cantidad:
            break
        # Elegir un tipo que no forme par repetido con este centro
        tipos_disponibles = [
            t for t in tipos_por_peso
            if (centro["id"], t) not in pares_usados
        ]
        if not tipos_disponibles:
            continue
        tipo = rng.choice(tipos_disponibles)
        pares_usados.add((centro["id"], tipo))
        servicios.append({
            "id": len(servicios) + 1,
            "id_centro_salud": centro["id"],
            "nombre_tipo_servicio": tipo,
            "matricula_encargado": None,
        })

    # Completar hasta 70 con pares únicos restantes
    mientras = 0
    while len(servicios) < cantidad and mientras < 1000:
        mientras += 1
        centro = rng.choice(centros)
        tipo = rng.choice(tipos_por_peso)
        if (centro["id"], tipo) in pares_usados:
            continue
        pares_usados.add((centro["id"], tipo))
        servicios.append({
            "id": len(servicios) + 1,
            "id_centro_salud": centro["id"],
            "nombre_tipo_servicio": tipo,
            "matricula_encargado": None,
        })

    return servicios


# ---------------------------------------------------------------------------
# 5. atencion_servicio: 160 (~2,3 por servicio)
# ---------------------------------------------------------------------------

def generar_atencion_servicio(
    servicios: list[dict],
    horarios: list[dict],
    rng: random.Random,
) -> list[dict]:
    """Genera pares (servicio, horario) únicos hasta el total configurado."""
    cantidad = TOTALES["atencion_servicio"]
    if not servicios or not horarios:
        return []

    id_horarios = [h["id"] for h in horarios]
    capacidad = len(servicios) * len(id_horarios)
    if cantidad > capacidad:
        raise ValueError(
            f"No se pueden generar {cantidad} atenciones únicas: "
            f"solo hay {capacidad} combinaciones servicio-horario disponibles"
        )

    # Distribución equilibrada: cada servicio recibe 2 o 3 horarios, sin repetir.
    base, sobrante = divmod(cantidad, len(servicios))
    atencion = []
    for i, servicio in enumerate(servicios):
        n = base + (1 if i < sobrante else 0)
        seleccionados = rng.sample(id_horarios, n)
        atencion.extend(
            {"id_servicio": servicio["id"], "id_horario": id_horario}
            for id_horario in seleccionados
        )

    return atencion


# ---------------------------------------------------------------------------
# 6. personal_servicio: 150 (médico encargado primero, luego cupos)
#    especializado_en: especialidades requeridas otorgadas
# ---------------------------------------------------------------------------

def generar_personal_servicio_y_especializado_en(
    servicios: list[dict],
    tipo_servicio: list[dict],
    especialidad_requerida: list[dict],
    personal: list[dict],
    especialidades: list[dict],
    rng: random.Random,
) -> tuple[list[dict], list[dict]]:
    """150 personal_servicio + especializado_en derivado.

    Respeta por separado los cupos de médicos y enfermeros de cada servicio.
    Cada persona se asigna como máximo a un servicio.
    """
    cantidad_personal_servicio = TOTALES["personal_servicio"]
    n_medicos_total = TOTALES.get("personal_medicos", 100)
    n_enfermeros_total = TOTALES.get("personal_enfermeros", 200)

    tipos_por_nombre = {t["nombre"]: t for t in tipo_servicio}
    especialidad_en_servicios = defaultdict(int)
    for er in especialidad_requerida:
        especialidad_en_servicios[er["nombre_especialidad"]] += 1

    def escasez_servicio(servicio):
        tipo = tipos_por_nombre.get(servicio["nombre_tipo_servicio"])
        if not tipo:
            return 0
        requeridas = tipo.get("especialidades_requeridas", [])
        return min(
            (especialidad_en_servicios.get(e, 0) for e in requeridas),
            default=999,
        )

    servicios_ordenados = sorted(servicios, key=escasez_servicio)
    medicos = [p for p in personal if p["rol"] == "Médico"]
    enfermeros = [p for p in personal if p["rol"] == "Enfermero"]
    rng.shuffle(medicos)
    rng.shuffle(enfermeros)

    personal_servicio = []
    especialidades_por_persona: dict[str, set[str]] = defaultdict(set)
    asignados_por_servicio: dict[int, dict[str, int]] = defaultdict(
        lambda: {"Médico": 0, "Enfermero": 0}
    )
    matriculas_asignadas = set()

    def asignar(servicio, persona, rol):
        matricula = persona["matricula"]
        personal_servicio.append({
            "id_servicio": servicio["id"],
            "matricula_personal": matricula,
        })
        matriculas_asignadas.add(matricula)
        asignados_por_servicio[servicio["id"]][rol] += 1
        tipo = tipos_por_nombre[servicio["nombre_tipo_servicio"]]
        especialidades_por_persona[matricula].update(
            tipo.get("especialidades_requeridas", [])
        )
        return matricula

    # Fase 1: asegurar un médico encargado por servicio, dentro de su cupo.
    for servicio in servicios_ordenados:
        if len(personal_servicio) >= cantidad_personal_servicio:
            break
        tipo = tipos_por_nombre[servicio["nombre_tipo_servicio"]]
        if tipo["num_medicos"] < 1:
            continue
        if medicos:
            medico = medicos.pop()
            matricula = asignar(servicio, medico, "Médico")
            servicio["matricula_encargado"] = matricula

    # Fase 2: completar primero los cupos de enfermería, nunca superarlos.
    for servicio in servicios_ordenados:
        tipo = tipos_por_nombre[servicio["nombre_tipo_servicio"]]
        while (
            len(personal_servicio) < cantidad_personal_servicio
            and enfermeros
            and asignados_por_servicio[servicio["id"]]["Enfermero"] < tipo["num_enfermeros"]
        ):
            asignar(servicio, enfermeros.pop(), "Enfermero")

    # Fase 3: completar los cupos médicos restantes.
    for servicio in servicios_ordenados:
        tipo = tipos_por_nombre[servicio["nombre_tipo_servicio"]]
        while (
            len(personal_servicio) < cantidad_personal_servicio
            and medicos
            and asignados_por_servicio[servicio["id"]]["Médico"] < tipo["num_medicos"]
        ):
            asignar(servicio, medicos.pop(), "Médico")

    # Fase 4: si aún falta personal, completar cupos de enfermería disponibles.
    for servicio in servicios_ordenados:
        tipo = tipos_por_nombre[servicio["nombre_tipo_servicio"]]
        while (
            len(personal_servicio) < cantidad_personal_servicio
            and enfermeros
            and asignados_por_servicio[servicio["id"]]["Enfermero"] < tipo["num_enfermeros"]
        ):
            asignar(servicio, enfermeros.pop(), "Enfermero")

    if len(personal_servicio) != cantidad_personal_servicio:
        raise ValueError(
            f"No fue posible asignar {cantidad_personal_servicio} personas respetando "
            f"los cupos por servicio; se asignaron {len(personal_servicio)}. "
            "Revisá los cupos de data/tipos_servicio.json."
        )

    # ------------------------------------------------------------------
    # 7. especializado_en: completar hasta 320
    # ------------------------------------------------------------------
    especializado_en = []
    objetivo = TOTALES["especializado_en"]

    def _agregar_ee(matricula: str, esp: str) -> bool:
        """Agrega una fila si no es duplicado y no se superó el objetivo."""
        if len(especializado_en) >= objetivo:
            return False
        ya_tiene = any(
            ee["matricula_personal"] == matricula and ee["nombre_especialidad"] == esp
            for ee in especializado_en
        )
        if ya_tiene:
            return False
        especializado_en.append({
            "matricula_personal": matricula,
            "nombre_especialidad": esp,
        })
        return True

    # Primero las otorgadas por servicios (obligatorias por trigger)
    for matricula, esps in especialidades_por_persona.items():
        # Los set no garantizan un orden estable entre procesos de Python:
        # PYTHONHASHSEED puede cambiarlo aunque la semilla del generador sea igual.
        # Ordenar evita que el SQL alterne las filas de una misma persona.
        for esp in sorted(esps):
            if len(especializado_en) >= objetivo:
                break
            _agregar_ee(matricula, esp)
        if len(especializado_en) >= objetivo:
            break

    # Contar cuántas tiene cada persona ya
    conteo_por_persona = defaultdict(int)
    for ee in especializado_en:
        conteo_por_persona[ee["matricula_personal"]] += 1

    nombres_especialidades = []
    for e in especialidades:
        if isinstance(e, dict):
            nombres_especialidades.append(e["nombre"])
        else:
            nombres_especialidades.append(e)

    # Cada persona debe tener al menos una (si no se superó el objetivo)
    todas_matriculas = [p["matricula"] for p in personal]
    for m in todas_matriculas:
        if len(especializado_en) >= objetivo:
            break
        if conteo_por_persona[m] == 0:
            esp = rng.choice(nombres_especialidades)
            _agregar_ee(m, esp)
            conteo_por_persona[m] += 1

    # 20 médicos con segunda especialidad (si no se superó el objetivo)
    medicos_con_segunda = 0
    for p in personal:
        if len(especializado_en) >= objetivo:
            break
        if p["rol"] != "Médico":
            continue
        if conteo_por_persona[p["matricula"]] >= 1 and medicos_con_segunda < 20:
            actuales = {
                ee["nombre_especialidad"]
                for ee in especializado_en
                if ee["matricula_personal"] == p["matricula"]
            }
            disponibles = [e for e in nombres_especialidades if e not in actuales]
            if disponibles:
                esp = rng.choice(disponibles)
                _agregar_ee(p["matricula"], esp)
                conteo_por_persona[p["matricula"]] += 1
                medicos_con_segunda += 1

    # Completar al azar hasta 320 (si aún no se alcanzó)
    while len(especializado_en) < objetivo:
        m = rng.choice(todas_matriculas)
        esp = rng.choice(nombres_especialidades)
        _agregar_ee(m, esp)

    return personal_servicio, especializado_en


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def generar_estructura_clinica(
    personal: list[dict] | None = None,
    centros: list[dict] | None = None,
    datos_json: dict | None = None,
    seed: int | None = None,
) -> dict:
    """Genera toda la estructura clínica en memoria.

    Args:
        personal: salida de generar_personal() (si None, se genera).
        centros: salida de generar_centros_de_salud() (si None, se genera).
        datos_json: contenido de tipos_servicio.json (si None, se carga).
        seed: semilla (si None, config.SEED).

    Devuelve dict con: tipo_servicio, especialidad, especialidad_requerida,
    horario_atencion, atencion_centro, servicio, atencion_servicio,
    personal_servicio, especializado_en.
    """
    if seed is None:
        seed = SEED
    rng = random.Random(seed)

    if datos_json is None:
        datos_json = _cargar_tipos_servicio()

    especialidades = [
        {"nombre": e} for e in datos_json["especialidades"]
    ]

    tipo_servicio, especialidad_requerida = generar_tipo_servicio_y_especialidad_requerida(
        datos_json
    )
    horario_atencion = generar_horario_atencion(rng)

    if centros is None:
        from generadores.geografia import generar_geografia
        geo = generar_geografia(seed=seed)
        centros = geo["centro_de_salud"]

    atencion_centro = generar_atencion_centro(centros, horario_atencion, rng)
    servicio = generar_servicio(centros, tipo_servicio, rng)
    atencion_servicio = generar_atencion_servicio(servicio, horario_atencion, rng)

    if personal is None:
        from generadores.personal import generar_personal
        personal = generar_personal(rng)

    personal_servicio, especializado_en = generar_personal_servicio_y_especializado_en(
        servicio, tipo_servicio, especialidad_requerida, personal, especialidades, rng
    )

    return {
        "tipo_servicio": tipo_servicio,
        "especialidad": especialidades,
        "especialidad_requerida": especialidad_requerida,
        "horario_atencion": horario_atencion,
        "atencion_centro": atencion_centro,
        "servicio": servicio,
        "atencion_servicio": atencion_servicio,
        "personal_servicio": personal_servicio,
        "especializado_en": especializado_en,
        "personal": personal,
    }
