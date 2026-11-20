"""Generador de geografía: departamentos, ciudades, barrios y centros de salud.

Produce, en memoria y con semilla reproducible (config.SEED):

- departamento: 15 de 17 de Entre Ríos (se descartan los 2 menos poblados,
  o los listados en config.DEPARTAMENTOS_EXCLUIDOS).
- ciudad: una por departamento (la cabecera).
- barrio: 20, distribuidos entre ciudades y con nombres únicos a nivel
  global (se califica con la ciudad si el nombre se repite).
- centro_de_salud: 20, uno por barrio. Calle y altura vienen de Georef;
  direccion = "calle altura" (máx. 30 caracteres). Inauguración estrictamente
  anterior a hoy.

Todos los IDs son secuenciales (se emiten con OVERRIDING SYSTEM VALUE).
"""

from datetime import date, timedelta
import random

from config import (
    DEPARTAMENTOS_EXCLUIDOS,
    FECHA_REFERENCIA,
    INAUGURACION_ENTRE,
    SEED,
    TOTALES,
)
from fuentes.catalogos import LIMITE_NOMBRE, centros_salud
from fuentes.geografia import (
    obtener_barrios,
    obtener_calles,
    obtener_departamentos,
    obtener_localidades,
)


def _fecha_aleatoria(ano_ini: int, ano_fin: int, limite: date, rng: random.Random) -> date:
    """Devuelve una fecha aleatoria entre ano_ini y ano_fin, estrictamente anterior a `limite`."""
    inicio = date(ano_ini, 1, 1)
    fin = min(date(ano_fin, 12, 31), limite - timedelta(days=1))
    if fin < inicio:
        return inicio
    dias = (fin - inicio).days
    return inicio + timedelta(days=rng.randint(0, dias))


def _nombre_barrio_unico(nombre_base: str, ciudad: str, usados: set[str]) -> str:
    """Devuelve un nombre de barrio único a nivel global (≤ 30 caracteres).

    Si el nombre base ya se usó, se califica con la ciudad (truncada) o se le
    añade un sufijo numérico.
    """
    if nombre_base not in usados:
        return nombre_base

    espacio = LIMITE_NOMBRE - len(nombre_base) - 1
    if espacio > 0:
        ciudad_corta = ciudad[:espacio]
        candidato = f"{nombre_base} {ciudad_corta}"
        if len(candidato) <= LIMITE_NOMBRE and candidato not in usados:
            return candidato

    for n in range(1, 100):
        candidato = f"{nombre_base} {n}"
        if len(candidato) <= LIMITE_NOMBRE and candidato not in usados:
            return candidato

    for n in range(1, 100):
        candidato = f"{nombre_base[:24]} {n}"
        if candidato not in usados:
            return candidato

    raise ValueError(f"No se pudo generar nombre único para barrio '{nombre_base}'")


# ---------------------------------------------------------------------------
# 1. Departamentos
# ---------------------------------------------------------------------------

def generar_departamentos(rng: random.Random) -> list[dict]:
    """Devuelve 15 departamentos de Entre Ríos (IDs 1..15)."""
    crudos = obtener_departamentos()  # [{"id": 3001, "nombre": "Paraná"}, ...]
    crudos = sorted(crudos, key=lambda d: d["nombre"])

    if DEPARTAMENTOS_EXCLUIDOS:
        excluidos = set(DEPARTAMENTOS_EXCLUIDOS)
        seleccionados = [d for d in crudos if d["nombre"] not in excluidos]
    elif len(crudos) > TOTALES["departamento"]:
        # Más de 15: excluir los 2 menos poblados (criterio determinista:
        # los 2 últimos de la lista ordenada por nombre).
        seleccionados = crudos[:-2]
    else:
        # Ya hay 15 o menos: usar todos sin excluir.
        seleccionados = list(crudos)

    cantidad = TOTALES["departamento"]
    seleccionados = seleccionados[:cantidad]

    resultado = []
    for i, d in enumerate(seleccionados, start=1):
        resultado.append({
            "id": i,
            "nombre": d["nombre"],
            "id_georef": d["id"],
        })
    return resultado


# ---------------------------------------------------------------------------
# 2. Ciudades (una por departamento, la cabecera)
# ---------------------------------------------------------------------------

def generar_ciudades(departamentos: list[dict], rng: random.Random) -> list[dict]:
    """Devuelve una ciudad (cabecera) por departamento. IDs 1..15."""
    cantidad = TOTALES["ciudad"]
    resultado = []

    for i, depto in enumerate(departamentos, start=1):
        localidades = obtener_localidades(depto["id_georef"]) or []

        cabecera = None
        for loc in localidades:
            if loc["nombre"] == depto["nombre"]:
                cabecera = loc
                break
        if cabecera is None and localidades:
            cabecera = localidades[0]

        if cabecera is None:
            cabecera = {"nombre": depto["nombre"], "id": None}

        resultado.append({
            "id": i,
            "id_departamento": depto["id"],
            "nombre": cabecera["nombre"],
            "id_georef": depto["id_georef"],
            "id_localidad": cabecera.get("id"),
        })

    return resultado[:cantidad]


# ---------------------------------------------------------------------------
# 3. Barrios (20, nombres únicos a nivel global)
# ---------------------------------------------------------------------------

def generar_barrios(ciudades: list[dict], rng: random.Random) -> list[dict]:
    """Devuelve 20 barrios distribuidos entre las ciudades. IDs 1..20."""
    cantidad = TOTALES["barrio"]
    crudos = obtener_barrios() or []  # [{"nombre": ..., "lat": ..., "lon": ...}, ...]

    n_ciudades = len(ciudades)
    base = cantidad // n_ciudades
    sobrante = cantidad % n_ciudades
    ciudades_con_extra = set(rng.sample(range(n_ciudades), sobrante)) if sobrante else set()

    asignaciones = []  # (idx_ciudad, nombre_crudo)
    idx = 0
    for i in range(n_ciudades):
        n_barrios = base + (1 if i in ciudades_con_extra else 0)
        for _ in range(n_barrios):
            if idx < len(crudos):
                asignaciones.append((i, crudos[idx]["nombre"]))
                idx += 1

    # Si no hay suficientes barrios crudos, generar genéricos
    while len(asignaciones) < cantidad:
        i = rng.randrange(n_ciudades)
        asignaciones.append((i, f"Barrio {len(asignaciones) + 1}"))

    usados: set[str] = set()
    resultado = []
    for i, (idx_ciudad, nombre_crudo) in enumerate(asignaciones, start=1):
        ciudad_nombre = ciudades[idx_ciudad]["nombre"]
        nombre_final = _nombre_barrio_unico(nombre_crudo, ciudad_nombre, usados)
        usados.add(nombre_final)
        resultado.append({
            "id": i,
            "id_ciudad": ciudades[idx_ciudad]["id"],
            "nombre": nombre_final,
        })

    return resultado


# ---------------------------------------------------------------------------
# 4. Centros de salud (20, uno por barrio)
# ---------------------------------------------------------------------------

def generar_centros_de_salud(
    barrios: list[dict],
    ciudades_por_id: dict[int, dict],
    rng: random.Random,
) -> list[dict]:
    """Devuelve 20 centros de salud, uno por barrio. IDs 1..20."""
    cantidad = TOTALES["centro_de_salud"]
    nombres = centros_salud(cantidad)

    hoy = FECHA_REFERENCIA if FECHA_REFERENCIA is not None else date.today()
    ano_ini, ano_fin = INAUGURACION_ENTRE

    resultado = []
    for i, barrio in enumerate(barrios[:cantidad], start=1):
        ciudad = ciudades_por_id[barrio["id_ciudad"]]
        id_depto_georef = ciudad["id_georef"]
        id_localidad = ciudad.get("id_localidad")

        # Obtener calles de la localidad (o del departamento como fallback)
        calles = []
        if id_localidad is not None:
            try:
                calles = obtener_calles(id_depto_georef, id_localidad) or []
            except Exception:
                calles = []
        if not calles:
            try:
                calles = obtener_calles(id_depto_georef) or []
            except Exception:
                calles = []

        if calles:
            calle = rng.choice(calles)
            calle_nombre = calle["nombre"]
            altura = rng.randint(1, 9999)
        else:
            calle_nombre = "Calle Falsa"
            altura = 123

        direccion = f"{calle_nombre} {altura}"
        if len(direccion) > LIMITE_NOMBRE:
            max_calle = LIMITE_NOMBRE - len(str(altura)) - 1
            if max_calle > 0:
                calle_nombre = calle_nombre[:max_calle]
                direccion = f"{calle_nombre} {altura}"
            else:
                direccion = f"Calle {altura}"[:LIMITE_NOMBRE]

        fecha_inag = _fecha_aleatoria(ano_ini, ano_fin, hoy, rng)

        resultado.append({
            "id": i,
            "id_barrio": barrio["id"],
            "nombre": nombres[i - 1],
            "direccion": direccion,
            "inaguracion": fecha_inag.isoformat(),
            "calle": calle_nombre,
            "altura": altura,
        })

    return resultado


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def generar_geografia(seed: int | None = None) -> dict[str, list[dict]]:
    """Genera los 4 grupos de datos geográficos y los devuelve en un dict."""
    if seed is None:
        seed = SEED
    rng = random.Random(seed)

    departamentos = generar_departamentos(rng)
    ciudades = generar_ciudades(departamentos, rng)
    barrios = generar_barrios(ciudades, rng)
    ciudades_por_id = {c["id"]: c for c in ciudades}
    centros = generar_centros_de_salud(barrios, ciudades_por_id, rng)

    return {
        "departamento": departamentos,
        "ciudad": ciudades,
        "barrio": barrios,
        "centro_de_salud": centros,
    }
