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
    """160 filas (id_servicio, id_horario), ~2,3 por servicio."""
    cantidad = TOTALES["atencion_servicio"]
    atencion = []
    id_horarios = [h["id"] for h in horarios]

    # ~2,3 horarios por servicio distribuidos
    base = cantidad // len(servicios)
    sobrante = cantidad % len(servicios)

    for i, servicio in enumerate(servicios):
        n = base + (1 if i < sobrante else 0)
        for _ in range(n):
            atencion.append({
                "id_servicio": servicio["id"],
                "id_horario": rng.choice(id_horarios),
            })

    return atencion[:cantidad]


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

    Reglas:
    - Primero un médico por servicio (encargado)
    - Luego completar hasta cupos (num_medicos/num_enfermeros por tipo)
    - Máximo 150 total, 100 médicos, 200 enfermeros
    - Cada persona en un solo servicio
    - A cada persona se le otorgan las especialidades requeridas que falten
    - Armado de especialidad más escasa a más abundante
    """
    cantidad_personal_servicio = TOTALES["personal_servicio"]
    n_medicos_total = 100  # config.MEDICOS
    n_enfermeros_total = 200  # config.ENFERMEROS

    # Indexar tipos por nombre
    tipos_por_nombre = {t["nombre"]: t for t in tipo_servicio}

    # Contar cuántos servicios requieren cada especialidad (escasez)
    especialidad_en_servicios = defaultdict(int)
    for er in especialidad_requerida:
        especialidad_en_servicios[er["nombre_especialidad"]] += 1

    # Ordenar servicios por especialidad requerida más escasa primero
    def escasez_servicio(s):
        tipo = tipos_por_nombre.get(s["nombre_tipo_servicio"])
        if not tipo:
            return 0
        esps = tipo.get("especialidades_requeridas", [])
        if not esps:
            return 999
        return min(especialidad_en_servicios.get(e, 0) for e in esps)

    servicios_ordenados = sorted(servicios, key=escasez_servicio)

    # Separar personal por rol
    medicos = [p for p in personal if p["rol"] == "Médico"]
    enfermeros = [p for p in personal if p["rol"] == "Enfermero"]
    rng.shuffle(medicos)
    rng.shuffle(enfermeros)

    # Contadores de asignados
    medicos_asignados = 0
    enfermeros_asignados = 0

    # Registro de qué especialidades tiene cada persona (para no duplicar)
    especialidades_por_persona: dict[str, set[str]] = defaultdict(set)

    # Contar cuántas especialidades requiere cada servicio
    especialidades_requeridas_por_tipo: dict[str, list[str]] = {}
    for t in tipo_servicio:
        especialidades_requeridas_por_tipo[t["nombre"]] = list(
            t.get("especialidades_requeridas", [])
        )

    # Asignar personal a servicios
    personal_servicio = []
    servicios_completados = 0

    for servicio in servicios_ordenados:
        if len(personal_servicio) >= cantidad_personal_servicio:
            break

        tipo_nombre = servicio["nombre_tipo_servicio"]
        tipo = tipos_por_nombre[tipo_nombre]
        cupo_medicos = tipo["num_medicos"]
        cupo_enfermeros = tipo["num_enfermeros"]
        req_esps = especialidades_requeridas_por_tipo[tipo_nombre]

        # 1. Un médico por servicio (encargado)
        if medicos_asignados < n_medicos_total and medicos:
            medico = medicos.pop()
            personal_servicio.append({
                "id_servicio": servicio["id"],
                "matricula_personal": medico["matricula"],
            })
            servicio["matricula_encargado"] = medico["matricula"]
            medicos_asignados += 1
            # Otorgar especialidades requeridas al médico
            for esp in req_esps:
                if esp not in especialidades_por_persona[medico["matricula"]]:
                    especialidades_por_persona[medico["matricula"]].add(esp)

        # 2. Completar cupos de enfermeros
        while (
            len(personal_servicio) < cantidad_personal_servicio
            and enfermeros_asignados < n_enfermeros_total
            and enfermeros
            and sum(
                1 for ps in personal_servicio
                if ps["id_servicio"] == servicio["id"]
            ) < cupo_medicos + cupo_enfermeros
        ):
            enfermero = enfermeros.pop()
            personal_servicio.append({
                "id_servicio": servicio["id"],
                "matricula_personal": enfermero["matricula"],
            })
            enfermeros_asignados += 1
            for esp in req_esps:
                if esp not in especialidades_por_persona[enfermero["matricula"]]:
                    especialidades_por_persona[enfermero["matricula"]].add(esp)

        servicios_completados += 1

    # Si no alcanzamos 150, intentar con médicos restantes
    while (
        len(personal_servicio) < cantidad_personal_servicio
        and medicos_asignados < n_medicos_total
        and medicos
    ):
        # Buscar un servicio con cupo de médico disponible
        for servicio in servicios:
            tipo = tipos_por_nombre[servicio["nombre_tipo_servicio"]]
            actual_medicos = sum(
                1 for ps in personal_servicio
                if ps["id_servicio"] == servicio["id"]
                and any(p["matricula"] == ps["matricula_personal"] and p["rol"] == "Médico"
                        for p in personal)
            )
            # Simplificado: asignar a servicios con menos de cupo total
            actual_total = sum(1 for ps in personal_servicio if ps["id_servicio"] == servicio["id"])
            if actual_total < tipo["num_medicos"] + tipo["num_enfermeros"]:
                medico = medicos.pop()
                personal_servicio.append({
                    "id_servicio": servicio["id"],
                    "matricula_personal": medico["matricula"],
                })
                medicos_asignados += 1
                for esp in tipo.get("especialidades_requeridas", []):
                    if esp not in especialidades_por_persona[medico["matricula"]]:
                        especialidades_por_persona[medico["matricula"]].add(esp)
                break
        else:
            break

    # Si aún faltan, usar enfermeros restantes
    while (
        len(personal_servicio) < cantidad_personal_servicio
        and enfermeros_asignados < n_enfermeros_total
        and enfermeros
    ):
        for servicio in servicios:
            tipo = tipos_por_nombre[servicio["nombre_tipo_servicio"]]
            actual_total = sum(1 for ps in personal_servicio if ps["id_servicio"] == servicio["id"])
            if actual_total < tipo["num_medicos"] + tipo["num_enfermeros"]:
                enfermero = enfermeros.pop()
                personal_servicio.append({
                    "id_servicio": servicio["id"],
                    "matricula_personal": enfermero["matricula"],
                })
                enfermeros_asignados += 1
                for esp in tipo.get("especialidades_requeridas", []):
                    if esp not in especialidades_por_persona[enfermero["matricula"]]:
                        especialidades_por_persona[enfermero["matricula"]].add(esp)
                break
        else:
            break

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
        for esp in esps:
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
