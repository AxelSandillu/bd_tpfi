"""Generador de internaciones (internacion).

Genera 150 internaciones en memoria (reproducible con config.SEED):

- 150 registros de historia clínica distintos, todos de servicios cuyo tipo
  tiene `interna: true`.
- `fecha_ingreso` igual a `dia_visita` del registro (lo exige el trigger).
- 40 actuales: `fecha_egreso` NULL e ingreso reciente.
- 110 pasadas: egreso estrictamente posterior al ingreso, dentro de
  DURACION_INTERNACION_DIAS, y anterior a hoy.
- Un mismo paciente nunca tiene internaciones superpuestas (a lo sumo una
  activa, y las pasadas terminan antes de que empiece cualquier otra).

Depende de:
  - config.py (INTERNACIONES_ACTUALES, INTERNACIONES_PASADAS,
    INTERNACION_ACTUAL_DIAS, DURACION_INTERNACION_DIAS, SEED)
  - pools.py (Pool, PoolAgotadoError)
  - generadores.registro_hc (issue #14)
  - generadores.estructura_clinica (issue #12)
"""

import random
from datetime import date, timedelta

from config import (
    DURACION_INTERNACION_DIAS,
    INTERNACION_ACTUAL_DIAS,
    INTERNACIONES_ACTUALES,
    INTERNACIONES_PASADAS,
    SEED,
)
from pools import Pool, PoolAgotadoError

from generadores.registro_hc import _hoy

# Fin "infinito" de una internación activa para comparar intervalos.
_SIN_EGRESO = date.max


def _a_fecha(valor: str) -> date:
    """'YYYY-MM-DD' o 'YYYY-MM-DDTHH:MM:SS...' -> date."""
    return date.fromisoformat(valor[:10])


def _se_superpone(inicio: date, fin: date, ocupados: list[tuple[date, date]]) -> bool:
    """True si [inicio, fin] toca algún intervalo ya ocupado (extremos incluidos)."""
    return any(inicio <= o_fin and o_inicio <= fin for o_inicio, o_fin in ocupados)


def generar_internaciones(
    registros_hc: list[dict],
    servicios: list[dict],
    tipo_servicio: list[dict],
    rng: random.Random | None = None,
) -> list[dict]:
    """Devuelve las internaciones (40 actuales + 110 pasadas).

    Cada internación: id, id_registro_hc, fecha_ingreso, fecha_egreso.

    El id de un registro es `registro["id"]` si existe; si no, su posición
    (1-based) en `registros_hc`, que es el id que le va a tocar al emitir el
    SQL con ids explícitos.

    Lanza PoolAgotadoError si no hay suficientes registros elegibles para
    completar las cantidades (el llamador puede reintentar con otra semilla).
    """
    if rng is None:
        rng = random.Random(SEED)

    n_actuales = INTERNACIONES_ACTUALES
    n_pasadas = INTERNACIONES_PASADAS
    dur_min, dur_max = DURACION_INTERNACION_DIAS
    rec_min, rec_max = INTERNACION_ACTUAL_DIAS
    hoy = _hoy()

    interna_por_tipo = {t["nombre"]: t.get("interna", False) for t in tipo_servicio}
    interna_por_servicio = {
        s["id"]: interna_por_tipo.get(s["nombre_tipo_servicio"], False)
        for s in servicios
    }

    # Registros elegibles: de servicios que internan, con su id y su fecha.
    elegibles: list[dict] = []
    for pos, r in enumerate(registros_hc, start=1):
        if not interna_por_servicio.get(r["id_servicio"], False):
            continue
        elegibles.append(
            {
                "id": r.get("id", pos),
                "dni": r["dni_paciente"],
                "visita": r["dia_visita"],
                "fecha": _a_fecha(r["dia_visita"]),
            }
        )

    # Intervalos ya ocupados por paciente.
    ocupados: dict[int, list[tuple[date, date]]] = {}
    internaciones: list[dict] = []
    usados: set[int] = set()  # ids de registro ya internados

    # --- 1. Actuales: ingreso reciente, sin egreso -------------------------
    pool_recientes = Pool(
        "registros_recientes_que_internan",
        [
            e
            for e in elegibles
            if hoy - timedelta(days=rec_max)
            <= e["fecha"]
            <= hoy - timedelta(days=rec_min)
        ],
        consumible=True,
        rng=rng,
    )
    actuales = 0
    while actuales < n_actuales and not pool_recientes.esta_vacio():
        e = pool_recientes.tomar_uno()
        if _se_superpone(e["fecha"], _SIN_EGRESO, ocupados.get(e["dni"], [])):
            continue
        ocupados.setdefault(e["dni"], []).append((e["fecha"], _SIN_EGRESO))
        usados.add(e["id"])
        internaciones.append(
            {
                "id_registro_hc": e["id"],
                "fecha_ingreso": e["visita"],
                "fecha_egreso": None,
            }
        )
        actuales += 1

    if actuales < n_actuales:
        raise PoolAgotadoError(
            f"Internaciones actuales: se necesitan {n_actuales} registros recientes "
            f"(últimos {rec_max} días) de servicios con interna=true y de pacientes "
            f"distintos, pero solo hay {actuales}. Revisar generar_registro_hc."
        )

    # --- 2. Pasadas: egreso posterior al ingreso y anterior a hoy ----------
    ultimo_egreso_posible = hoy - timedelta(days=1)
    pool_pasadas = Pool(
        "registros_no_internados",
        [e for e in elegibles if e["id"] not in usados],
        consumible=True,
        rng=rng,
    )
    pasadas = 0
    while pasadas < n_pasadas and not pool_pasadas.esta_vacio():
        e = pool_pasadas.tomar_uno()
        dias_max = min(dur_max, (ultimo_egreso_posible - e["fecha"]).days)
        if dias_max < dur_min:
            continue  # ingresó demasiado cerca de hoy para tener un egreso válido
        dias = rng.randint(dur_min, dias_max)
        egreso = e["fecha"] + timedelta(days=dias)
        if _se_superpone(e["fecha"], egreso, ocupados.get(e["dni"], [])):
            continue
        ocupados.setdefault(e["dni"], []).append((e["fecha"], egreso))
        usados.add(e["id"])
        internaciones.append(
            {
                "id_registro_hc": e["id"],
                "fecha_ingreso": e["visita"],
                "fecha_egreso": egreso.isoformat(),
            }
        )
        pasadas += 1

    if pasadas < n_pasadas:
        raise PoolAgotadoError(
            f"Internaciones pasadas: se necesitan {n_pasadas} registros elegibles "
            f"sin superposición, pero solo se lograron {pasadas}."
        )

    # Ids estables: por fecha de ingreso y, a igualdad, por id de registro.
    internaciones.sort(key=lambda i: (i["fecha_ingreso"], i["id_registro_hc"]))
    for n, internacion in enumerate(internaciones, start=1):
        internacion["id"] = n
    return [
        {
            "id": i["id"],
            "id_registro_hc": i["id_registro_hc"],
            "fecha_ingreso": i["fecha_ingreso"],
            "fecha_egreso": i["fecha_egreso"],
        }
        for i in internaciones
    ]


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def generar_internaciones_completo(
    datos_registro_hc: dict | None = None,
    datos_estructura: dict | None = None,
    seed: int | None = None,
) -> dict:
    """Genera internacion en memoria usando datos de issues previos.

    Args:
        datos_registro_hc: salida de generar_registro_hc_completo().
        datos_estructura: salida de generar_estructura_clinica().
        seed: semilla (si None, config.SEED).

    Devuelve dict con clave "internacion".
    """
    if seed is None:
        seed = SEED
    rng = random.Random(seed)

    if datos_estructura is None:
        from generadores.estructura_clinica import generar_estructura_clinica

        datos_estructura = generar_estructura_clinica(seed=seed)

    if datos_registro_hc is None:
        from generadores.registro_hc import generar_registro_hc_completo

        datos_registro_hc = generar_registro_hc_completo(
            datos_estructura=datos_estructura, seed=seed
        )

    internaciones = generar_internaciones(
        registros_hc=datos_registro_hc["registro_hc"],
        servicios=datos_estructura["servicio"],
        tipo_servicio=datos_estructura["tipo_servicio"],
        rng=rng,
    )
    return {"internacion": internaciones}
