"""Fuentes geográficas: API Georef v2 y Overpass API.

Los resultados se guardan en cache. En modo offline se utilizan los archivos
cacheados y, si faltan, el conjunto curado incluido en data/geografia_fallback.json.
"""

import json
import os
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
OFFLINE_ENV = "POBLADOR_OFFLINE"


class GeografiaError(Exception):
    """Error al obtener datos geográficos."""


def _offline() -> bool:
    return os.environ.get(OFFLINE_ENV) == "1"


def _cache_path(nombre: str) -> Path:
    return CACHE_DIR / f"geografia_{nombre}.json"


def _cargar_cache(nombre: str):
    cache_file = _cache_path(nombre)
    if not cache_file.exists():
        return None
    with cache_file.open(encoding="utf-8") as archivo:
        return json.load(archivo)


def _guardar_cache(nombre: str, datos) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with _cache_path(nombre).open("w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)


def _es_error_cliente(exc: requests.RequestException) -> bool:
    """Los 4xx (salvo 429) no se solucionan repitiendo la misma petición."""
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status is not None and 400 <= status < 500 and status != 429


def _fetch_json(url: str, params=None, timeout: int = 30):
    """GET con reintentos acotados; falla rápido ante errores HTTP 4xx."""
    ultimo_error = None
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            respuesta = requests.get(url, params=params, timeout=timeout)
            respuesta.raise_for_status()
            return respuesta.json()
        except requests.RequestException as exc:
            ultimo_error = exc
            if _es_error_cliente(exc) or intento == MAX_REINTENTOS:
                break
        except ValueError as exc:
            ultimo_error = exc
            if intento == MAX_REINTENTOS:
                break
        time.sleep(0.5 * intento)
    raise GeografiaError(f"No se pudo consultar {url}: {ultimo_error}") from ultimo_error


def _fetch_overpass(timeout: int = 60):
    """POST a Overpass con reintentos y corte ante errores HTTP 4xx."""
    ultimo_error = None
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            respuesta = requests.post(
                URL_OVERPASS, data=OVERPASS_QUERY_BARRIOS, timeout=timeout
            )
            respuesta.raise_for_status()
            return respuesta.json()
        except requests.RequestException as exc:
            ultimo_error = exc
            if _es_error_cliente(exc) or intento == MAX_REINTENTOS:
                break
        except ValueError as exc:
            ultimo_error = exc
            if intento == MAX_REINTENTOS:
                break
        time.sleep(0.5 * intento)
    raise GeografiaError(f"No se pudo consultar Overpass: {ultimo_error}") from ultimo_error


def _cargar_fallback():
    if not FALLBACK_PATH.is_file():
        raise GeografiaError(
            f"No existe el fallback geográfico: {FALLBACK_PATH.resolve()}"
        )
    with FALLBACK_PATH.open(encoding="utf-8") as archivo:
        return json.load(archivo)


def _lista_respuesta(datos: dict, clave: str) -> list[dict]:
    """Extrae la colección de Georef y tolera el envoltorio resultados si aparece."""
    coleccion = datos.get(clave)
    if coleccion is None and isinstance(datos.get("resultados"), dict):
        coleccion = datos["resultados"].get(clave)
    return coleccion if isinstance(coleccion, list) else []


def _id_relacionado(registro: dict, relacion: str):
    """Obtiene el ID de una relación tanto anidada como aplanada por la API."""
    valor = registro.get(relacion)
    if isinstance(valor, dict):
        return valor.get("id")
    return registro.get(f"{relacion}_id", valor)


def _usar_fallback_departamentos():
    resultado = _cargar_fallback()["departamentos"]
    _guardar_cache("departamentos", resultado)
    return resultado


def obtener_departamentos():
    """Devuelve departamentos de Entre Ríos en formato id/nombre."""
    cache = _cargar_cache("departamentos")
    if cache is not None:
        return cache
    if _offline():
        return _usar_fallback_departamentos()

    try:
        datos = _fetch_json(
            f"{URL_GEOREF}{GEOREF_ENDPOINT_DEPARTAMENTOS}",
            params={"provincia": PROVINCIA_ENTRE_RIOS, "campos": "id,nombre", "max": 100},
        )
        departamentos = _lista_respuesta(datos, "departamentos")
        if len(departamentos) < GEOREF_MIN_RESULTADOS:
            raise GeografiaError(
                f"Georef devolvió {len(departamentos)} departamentos; "
                f"se esperaban al menos {GEOREF_MIN_RESULTADOS}"
            )
        resultado = [
            {"id": d["id"], "nombre": d["nombre"]} for d in departamentos
        ]
        _guardar_cache("departamentos", resultado)
        return resultado
    except (GeografiaError, KeyError, TypeError):
        return _usar_fallback_departamentos()


def obtener_localidades(id_departamento: int):
    """Devuelve localidades de un departamento con su FK geográfica."""
    cache_key = f"localidades_{id_departamento}"
    cache = _cargar_cache(cache_key)
    if cache is not None:
        return cache

    fallback = [
        loc for loc in _cargar_fallback()["localidades"]
        if str(loc["id_departamento"]) == str(id_departamento)
    ]
    if _offline():
        _guardar_cache(cache_key, fallback)
        return fallback

    try:
        datos = _fetch_json(
            f"{URL_GEOREF}{GEOREF_ENDPOINT_LOCALIDADES}",
            params={
                "departamento": id_departamento,
                "campos": "id,nombre,departamento.id",
                "max": 200,
            },
        )
        localidades = _lista_respuesta(datos, "localidades")
        if len(localidades) < GEOREF_MIN_RESULTADOS:
            raise GeografiaError(
                f"Georef devolvió {len(localidades)} localidades para el "
                f"departamento {id_departamento}"
            )
        resultado = [
            {
                "id": loc["id"],
                "nombre": loc["nombre"],
                "id_departamento": _id_relacionado(loc, "departamento") or id_departamento,
            }
            for loc in localidades
        ]
        _guardar_cache(cache_key, resultado)
        return resultado
    except (GeografiaError, KeyError, TypeError):
        _guardar_cache(cache_key, fallback)
        return fallback


def obtener_calles(id_departamento: int, id_localidad: int | None = None):
    """Devuelve calles de un departamento y, opcionalmente, de una localidad."""
    cache_key = f"calles_{id_departamento}_{id_localidad or 'todos'}"
    cache = _cargar_cache(cache_key)
    if cache is not None:
        return cache

    fallback = [
        calle for calle in _cargar_fallback()["calles"]
        if str(calle["id_departamento"]) == str(id_departamento)
        and (id_localidad is None or str(calle.get("id_localidad")) == str(id_localidad))
    ]
    if _offline():
        _guardar_cache(cache_key, fallback)
        return fallback

    params = {
        "departamento": id_departamento,
        "campos": "id,nombre,departamento.id,localidad.id",
        "max": 500,
    }
    if id_localidad is not None:
        params["localidad"] = id_localidad

    try:
        datos = _fetch_json(f"{URL_GEOREF}{GEOREF_ENDPOINT_CALLES}", params=params)
        calles = _lista_respuesta(datos, "calles")
        if len(calles) < GEOREF_MIN_RESULTADOS:
            raise GeografiaError(
                f"Georef devolvió {len(calles)} calles para el departamento "
                f"{id_departamento}"
            )
        resultado = [
            {
                "id": calle["id"],
                "nombre": calle["nombre"],
                "id_departamento": _id_relacionado(calle, "departamento") or id_departamento,
                "id_localidad": _id_relacionado(calle, "localidad"),
            }
            for calle in calles
        ]
        _guardar_cache(cache_key, resultado)
        return resultado
    except (GeografiaError, KeyError, TypeError):
        _guardar_cache(cache_key, fallback)
        return fallback


def obtener_barrios():
    """Devuelve barrios de Entre Ríos; offline usa el fallback local."""
    cache = _cargar_cache("barrios")
    if cache is not None:
        return cache
    if _offline():
        resultado = _cargar_fallback()["barrios"]
        _guardar_cache("barrios", resultado)
        return resultado

    try:
        datos = _fetch_overpass()
        barrios = []
        for elemento in datos.get("elements", []):
            tags = elemento.get("tags", {})
            nombre = tags.get("name")
            if not nombre:
                continue
            lat = elemento.get("lat")
            lon = elemento.get("lon")
            if lat is None or lon is None:
                centro = elemento.get("center", {})
                lat, lon = centro.get("lat"), centro.get("lon")
            if lat is not None and lon is not None:
                barrios.append({"nombre": nombre, "lat": lat, "lon": lon})
        if len(barrios) < GEOREF_MIN_RESULTADOS:
            raise GeografiaError(
                f"Overpass devolvió {len(barrios)} barrios; se esperaban al menos "
                f"{GEOREF_MIN_RESULTADOS}"
            )
        _guardar_cache("barrios", barrios)
        return barrios
    except (GeografiaError, KeyError, TypeError):
        resultado = _cargar_fallback()["barrios"]
        _guardar_cache("barrios", resultado)
        return resultado
