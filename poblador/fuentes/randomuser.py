"""Fuente de datos: randomuser.me.

Descarga personas (nombre, apellido, fecha de nacimiento, nacionalidad) de
randomuser.me, una llamada por nacionalidad, y las guarda en cache para
poder trabajar offline. La semilla de la API se deriva de config.SEED.

Solo se solicitan los campos inc=name,dob,nat; se descartan telefono,
direccion y demas campos.
"""

import json
import hashlib
import os
import time
from pathlib import Path

import requests

from config import (
    MAX_REINTENTOS,
    MARGEN_API,
    PESOS_NAT,
    SEED,
    URL_RANDOMUSER,
)

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class RandomUserError(Exception):
    """Error al consultar randomuser.me."""


def _cache_path(nat: str, seed: int) -> Path:
    return CACHE_DIR / f"randomuser_{nat}_{seed}.json"


def _api_seed(seed: int, nat: str) -> int:
    """Deriva una semilla para la API a partir de config.SEED y la nacionalidad."""
    digest = hashlib.sha256(f"{seed}:{nat}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % (2**31 - 1)


def _fetch_one(nat: str, cantidad: int, seed: int, timeout: int = 30) -> list[dict]:
    """Hace una llamada a randomuser.me para una nacionalidad con reintentos."""
    params = {
        "results": cantidad,
        "nat": nat,
        "inc": "name,dob,nat",
        "seed": _api_seed(seed, nat),
    }
    ultimo_error = None
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            resp = requests.get(URL_RANDOMUSER, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            resultados = data["results"]
            if not resultados:
                raise RandomUserError(
                    f"randomuser.me devolvió una lista vacía para nat={nat}"
                )
            return resultados
        except requests.RequestException as exc:
            ultimo_error = exc
            respuesta = getattr(exc, "response", None)
            status = getattr(respuesta, "status_code", None)
            # Un 4xx (excepto 429) indica una petición inválida: reintentar
            # exactamente lo mismo no va a corregirla.
            if (status is not None and 400 <= status < 500 and status != 429) or intento == MAX_REINTENTOS:
                break
        except (ValueError, KeyError) as exc:
            ultimo_error = exc
            if intento == MAX_REINTENTOS:
                break
        if intento < MAX_REINTENTOS:
            time.sleep(0.5 * intento)
    raise RandomUserError(
        f"No se pudo obtener datos de randomuser.me para nat={nat} tras "
        f"{MAX_REINTENTOS} intentos: {ultimo_error}"
    )


def _guardar_cache(nat: str, seed: int, resultados: list[dict]) -> None:
    cache_file = _cache_path(nat, seed)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"results": resultados}, f, ensure_ascii=False, indent=2)


def _cargar_cache(nat: str, seed: int) -> list[dict] | None:
    cache_file = _cache_path(nat, seed)
    if not cache_file.exists():
        return None
    with open(cache_file, encoding="utf-8") as f:
        datos = json.load(f)
    return datos["results"]


def verificar_nats_disponibles() -> set[str]:
    """Hace una llamada de prueba para verificar qué códigos nat ofrece la API.

    Devuelve el conjunto de codigos nat que la API acepta. Imprime una
    advertencia si algun codigo de config.PESOS_NAT no devuelve resultados.
    """
    disponibles: set[str] = set()
    for nat in PESOS_NAT:
        try:
            resultados = _fetch_one(nat, 1, SEED)
            nat_devuelto = resultados[0].get("nat", "") if resultados else ""
            if nat_devuelto and nat_devuelto.upper() == nat.upper():
                disponibles.add(nat)
            else:
                print(
                    f"Aviso: randomuser.me no retorno resultados para nat='{nat}' "
                    f"(definida en config.PESOS_NAT)."
                )
        except RandomUserError as exc:
            print(f"Aviso: no se pudo verificar nat='{nat}' de PESOS_NAT: {exc}")
    return disponibles


def obtener_personas(cantidad_total: int) -> list[dict]:
    """Entrega una lista de personas con nombre, apellido, nacimiento y nat.

    Calcula la cantidad por nacionalidad desde config.PESOS_NAT (con margen
    config.MARGEN_API). Descarga y guarda en cache la primera ejecucion. Las
    siguientes, incluso sin red, devuelven exactamente las mismas personas.
    """
    offline = os.environ.get("POBLADOR_OFFLINE") == "1"

    # No hacemos una llamada de verificación por nacionalidad: cada consulta
    # adicional aumenta el tiempo de ejecución y no aporta datos al generador.
    # La caché existente se reutiliza tanto online como offline.
    personas: list[dict] = []
    for nat, peso in PESOS_NAT.items():
        cantidad = max(1, int(cantidad_total * peso * MARGEN_API))

        resultados = _cargar_cache(nat, SEED)
        if resultados is None:
            if offline:
                raise RandomUserError(
                    f"Modo offline: falta cache/{_cache_path(nat, SEED).name}. "
                    "Ejecute primero una corrida online con la misma semilla."
                )
            resultados = _fetch_one(nat, cantidad, SEED)
            _guardar_cache(nat, SEED, resultados)

        for r in resultados[:cantidad]:
            personas.append(
                {
                    "nombre": r["name"]["first"],
                    "apellido": r["name"]["last"],
                    "nacimiento": r["dob"]["date"],
                    "nat": r["nat"],
                }
            )
    return personas
