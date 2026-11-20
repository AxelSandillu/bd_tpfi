"""Fuentes geográficas: Georef AR y Overpass API.

Obtiene departamentos, localidades y calles de Entre Ríos (Georef) y barrios
(Overpass). Todo se cachea en disco y, si la API falla o devuelve muy pocos
resultados, se usa una lista curada en data/geografia_fallback.json para que
el programa funcione completamente offline.
"""

import json
import time
from pathlib import Path

import requests

from config import (
    GEOREF_ENDPOINT_CALLES,
    GEOREF_ENDPOINT_DEPARTAMENTOS,
    GEOREF_ENDPOINT_LOCALIDADES,
    GEOREF_MIN_RESULTADOS,
    MAX_REINTENTOS,
    OVERPASS_QUERY_BARRIOS,
    PROVINCIA_ENTRE_RIOS,
    URL_GEOREF,
    URL_OVERPASS,
)

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

FALLBACK_PATH = Path("data") / "geografia_fallback.json"


class GeografiaError(Exception):
    """Error al obtener datos geográficos."""


# ---------------------------------------------------------------------------
# Cache en disco
# ---------------------------------------------------------------------------

def _cache_path(nombre: str) -> Path:
    return CACHE_DIR / f"geografia_{nombre}.json"


def _cargar_cache(nombre: str):
    cache_file = _cache_path(nombre)
    if not cache_file.exists():
        return None
    with open(cache_file, encoding="utf-8") as f:
        return json.load(f)


def _guardar_cache(nombre: str, datos) -> None:
    cache_file = _cache_path(nombre)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# HTTP con reintentos
# ---------------------------------------------------------------------------

def _fetch_json(url: str, params=None, timeout: int = 30):
    """Hace una petición GET con reintentos. Lanza GeografiaError si falla."""
    ultimo_error = None
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            ultimo_error = exc
            if intento < MAX_REINTENTOS:
                time.sleep(0.5 * intento)
    raise GeografiaError(
        f"No se pudo consultar {url} tras {MAX_REINTENTOS} intentos: {ultimo_error}"
    )


def _fetch_overpass(timeout: int = 60):
    """Consulta la API de Overpass con reintentos."""
    ultimo_error = None
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            resp = requests.post(URL_OVERPASS, data=OVERPASS_QUERY_BARRIOS, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            ultimo_error = exc
            if intento < MAX_REINTENTOS:
                time.sleep(0.5 * intento)
    raise GeografiaError(
        f"No se pudo consultar Overpass tras {MAX_REINTENTOS} intentos: {ultimo_error}"
    )


# ---------------------------------------------------------------------------
# Fallback curado
# ---------------------------------------------------------------------------

def _cargar_fallback():
    with open(FALLBACK_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Georef
# ---------------------------------------------------------------------------

def obtener_departamentos():
    """Devuelve la lista de departamentos de Entre Ríos (id, nombre)."""
    cache = _cargar_cache("departamentos")
    if cache is not None:
        return cache

    try:
        datos = _fetch_json(
            f"{URL_GEOREF}{GEOREF_ENDPOINT_DEPARTAMENTOS}",
            params={"provincia": PROVINCIA_ENTRE_RIOS, "campos": "id,nombre", "max": 100},
        )
        departamentos = datos.get("departamentos", [])
        if len(departamentos) < GEOREF_MIN_RESULTADOS:
            raise GeografiaError(
                f"Georef devolvió pocos departamentos ({len(departamentos)}), "
                f"se esperaban al menos {GEOREF_MIN_RESULTADOS}"
            )
        resultado = [{"id": d["id"], "nombre": d["nombre"]} for d in departamentos]
        _guardar_cache("departamentos", resultado)
        return resultado
    except GeografiaError:
        fallback = _cargar_fallback()["departamentos"]
        _guardar_cache("departamentos", fallback)
        return fallback


def obtener_localidades(id_departamento: int):
    """Devuelve las localidades de un departamento (id, nombre, id_departamento)."""
    cache_key = f"localidades_{id_departamento}"
    cache = _cargar_cache(cache_key)
    if cache is not None:
        return cache

    try:
        datos = _fetch_json(
            f"{URL_GEOREF}{GEOREF_ENDPOINT_LOCALIDADES}",
            params={
                "departamento": id_departamento,
                "campos": "id,nombre,departamento.id",
                "max": 200,
            },
        )
        localidades = datos.get("localidades", [])
        if len(localidades) < GEOREF_MIN_RESULTADOS:
            raise GeografiaError(
                f"Georef devolvió pocas localidades ({len(localidades)}) para "
                f"el departamento {id_departamento}"
            )
        resultado = [
            {
                "id": loc["id"],
                "nombre": loc["nombre"],
                "id_departamento": loc["departamento"]["id"],
            }
            for loc in localidades
        ]
        _guardar_cache(cache_key, resultado)
        return resultado
    except GeografiaError:
        fallback = [
            loc
            for loc in _cargar_fallback()["localidades"]
            if loc["id_departamento"] == id_departamento
        ]
        _guardar_cache(cache_key, fallback)
        return fallback


def obtener_calles(id_departamento: int, id_localidad: int | None = None):
    """Devuelve las calles de un departamento (y opcionalmente de una localidad)."""
    cache_key = f"calles_{id_departamento}_{id_localidad or 'todos'}"
    cache = _cargar_cache(cache_key)
    if cache is not None:
        return cache

    params = {
        "departamento": id_departamento,
        "campos": "id,nombre,departamento.id,localidad.id",
        "max": 500,
    }
    if id_localidad is not None:
        params["localidad"] = id_localidad

    try:
        datos = _fetch_json(f"{URL_GEOREF}{GEOREF_ENDPOINT_CALLES}", params=params)
        calles = datos.get("calles", [])
        if len(calles) < GEOREF_MIN_RESULTADOS:
            raise GeografiaError(
                f"Georef devolvió pocas calles ({len(calles)}) para el "
                f"departamento {id_departamento}"
            )
        resultado = [
            {
                "id": c["id"],
                "nombre": c["nombre"],
                "id_departamento": c["departamento"]["id"],
                "id_localidad": c.get("localidad", {}).get("id"),
            }
            for c in calles
        ]
        _guardar_cache(cache_key, resultado)
        return resultado
    except GeografiaError:
        fallback = [
            c
            for c in _cargar_fallback()["calles"]
            if c["id_departamento"] == id_departamento
            and (id_localidad is None or c.get("id_localidad") == id_localidad)
        ]
        _guardar_cache(cache_key, fallback)
        return fallback


# ---------------------------------------------------------------------------
# Overpass (barrios)
# ---------------------------------------------------------------------------

def obtener_barrios():
    """Devuelve barrios (place=suburb|neighbourhood|quarter) de Entre Ríos."""
    cache = _cargar_cache("barrios")
    if cache is not None:
        return cache

    try:
        datos = _fetch_overpass()
        elementos = datos.get("elements", [])
        barrios = []
        for el in elementos:
            tags = el.get("tags", {})
            nombre = tags.get("name")
            if not nombre:
                continue
            lat = el.get("lat")
            lon = el.get("lon")
            if lat is None or lon is None:
                centro = el.get("center", {})
                lat = centro.get("lat")
                lon = centro.get("lon")
            barrios.append({"nombre": nombre, "lat": lat, "lon": lon})
        if len(barrios) < GEOREF_MIN_RESULTADOS:
            raise GeografiaError(
                f"Overpass devolvió pocos barrios ({len(barrios)}), se esperaban "
                f"al menos {GEOREF_MIN_RESULTADOS}"
            )
        _guardar_cache("barrios", barrios)
        return barrios
    except GeografiaError:
        fallback = _cargar_fallback()["barrios"]
        _guardar_cache("barrios", fallback)
        return fallback
