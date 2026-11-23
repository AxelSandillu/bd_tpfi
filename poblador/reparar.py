"""Reparador automático: bucle validar -> reparar (issue #17).

Reglas del reparador (PLANIFICACION.md §10):

- SOLO AGREGA filas. Nunca borra ni modifica una fila existente. Trabaja sobre
  una copia de las listas de cada tabla (las filas se comparten, no se tocan),
  así que las tablas que recibe quedan intactas.
- Tope de iteraciones (config.MAX_ITERACIONES_REPARACION). Si se agota, o si
  una pasada no logra avanzar, lanza ReparacionFallida con el detalle de lo no
  resuelto. Como no devuelve tablas, el llamador no puede emitir el SQL con
  violaciones pendientes.
- Al terminar informa el total por tabla contra el Excel (reporte()).

Qué repara (cada regla del validador tiene a lo sumo un arreglo que solo agrega):

    especialidades_requeridas  -> agrega la fila de especializado_en que falta
    fk (especialidad)          -> agrega la especialidad referenciada
    visita_en_horario          -> vincula al servicio un horario de ese día
                                  (y que cubra la hora, si la visita la trae)

Y completa los conteos que quedaron por debajo del objetivo del Excel:
personal_servicio, atencion_servicio, especializado_en, registro_hc e
internacion (40 actuales + 110 pasadas).

Qué NO puede reparar (porque exigiría modificar o borrar): UNIQUE repetidos,
largos, formatos, enums, fechas futuras, cupos excedidos, solapamientos, etc.
Esas violaciones abortan el programa con su detalle.

Sobre "preferir arreglos que no cambian conteos": sin modificar ni borrar no
existe un arreglo que deje los conteos igual, así que se interpreta como
"preferir el arreglo que agrega menos filas y reutiliza lo que ya existe".
Por ejemplo, una internación faltante se arma primero sobre un registro_hc que
ya existe (1 fila) y solo si no hay ninguno elegible se crea un registro nuevo
(2 filas). Si un arreglo hace pasar una tabla del objetivo, el desvío se informa
en el reporte para pasarlo a mano al Excel.
"""

import random
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, time, timedelta

from config import (
    DURACION_INTERNACION_DIAS,
    EJEMPLOS_POR_REGLA_EN_MENSAJE,
    INTERNACION_ACTUAL_DIAS,
    INTERNACIONES_ACTUALES,
    INTERNACIONES_PASADAS,
    MAX_INTENTOS_ELEMENTO_NUEVO,
    MAX_ITERACIONES_REPARACION,
    SEED,
    TOTALES,
    VENTANA_VISITAS_ANIOS,
)

# _instante y _hora son utilidades internas de validar.py (parseo de fechas y
# horas); se reutilizan para que ambos módulos lean las fechas igual.
from validar import CLAVES_FORANEAS, DIAS, Violacion, _hora, _instante, validar

ROL_MEDICO = "Médico"


# ---------------------------------------------------------------------------
# Resultado y error
# ---------------------------------------------------------------------------


@dataclass
class Resultado:
    """Salida de una reparación exitosa (sin violaciones pendientes)."""

    tablas: dict[str, list[dict]]
    agregadas: Counter  # tabla -> filas agregadas por la reparación
    iteraciones: int
    acciones: list[str] = field(default_factory=list)  # una línea por fila agregada
    objetivos: dict[str, int] = field(default_factory=dict)

    def reporte(self) -> str:
        return reporte(self.tablas, self.objetivos, self.agregadas)


class ReparacionFallida(Exception):
    """Quedan violaciones que el reparador no pudo resolver sin modificar o borrar.

    Atributos:
        violaciones: las violaciones pendientes (lista de Violacion).
        iteraciones: iteraciones realizadas.
        parcial: Resultado con lo que sí se alcanzó a agregar (solo para
            diagnóstico; NO debe usarse para emitir el SQL).
    """

    def __init__(
        self,
        mensaje: str,
        violaciones: list[Violacion],
        iteraciones: int,
        parcial: Resultado,
    ):
        super().__init__(mensaje)
        self.violaciones = violaciones
        self.iteraciones = iteraciones
        self.parcial = parcial


# ---------------------------------------------------------------------------
# Contexto de trabajo
# ---------------------------------------------------------------------------


def _hoy() -> date:
    import config

    return (
        config.FECHA_REFERENCIA if config.FECHA_REFERENCIA is not None else date.today()
    )


class _Ctx:
    """Estado de una reparación: tablas de trabajo, objetivos, azar y bitácora."""

    def __init__(self, tablas, objetivos, actuales, pasadas, rng, hoy):
        # Copia de las listas: agregar a una no toca la lista del llamador.
        self.t: dict[str, list[dict]] = {k: list(v) for k, v in tablas.items()}
        self.objetivos = objetivos
        self.actuales = actuales
        self.pasadas = pasadas
        self.rng = rng
        self.hoy = hoy
        self.agregadas: Counter = Counter()
        self.acciones: list[str] = []

    def filas(self, tabla: str) -> list[dict]:
        return self.t.setdefault(tabla, [])

    def agregar(self, tabla: str, fila: dict, accion: str) -> None:
        self.filas(tabla).append(fila)
        self.agregadas[tabla] += 1
        self.acciones.append(f"{tabla}: {accion}")

    def total_agregado(self) -> int:
        return sum(self.agregadas.values())


# --- índices (se recalculan al usarlos: las tablas son chicas) -----------------


def _registros_por_id(ctx: _Ctx) -> dict:
    """{id: fila}. Sin columna `id`, el id es la posición (1-based), igual que en el validador."""
    return {
        r.get("id", pos): r for pos, r in enumerate(ctx.filas("registro_hc"), start=1)
    }


def _proximo_id_registro(ctx: _Ctx):
    """Id para un registro nuevo, o None si las filas no llevan `id` (vale la posición)."""
    filas = ctx.filas("registro_hc")
    if any("id" in r for r in filas):
        return max(r.get("id", 0) for r in filas) + 1
    return None


def _proximo_id(ctx: _Ctx, tabla: str) -> int:
    return max((f.get("id", 0) for f in ctx.filas(tabla)), default=0) + 1


def _interna_por_servicio(ctx: _Ctx) -> dict:
    tipos = {t["nombre"]: t.get("interna", False) for t in ctx.filas("tipo_servicio")}
    return {
        s["id"]: tipos.get(s["nombre_tipo_servicio"], False)
        for s in ctx.filas("servicio")
    }


def _medicos_por_servicio(ctx: _Ctx) -> dict:
    roles = {p["matricula"]: p["rol"] for p in ctx.filas("personal")}
    out: dict = {}
    for ps in ctx.filas("personal_servicio"):
        if roles.get(ps["matricula_personal"]) == ROL_MEDICO:
            out.setdefault(ps["id_servicio"], []).append(ps["matricula_personal"])
    return out


def _horarios_por_servicio(ctx: _Ctx) -> dict:
    horarios = {h["id"]: h for h in ctx.filas("horario_atencion")}
    out: dict = {}
    for a in ctx.filas("atencion_servicio"):
        h = horarios.get(a["id_horario"])
        if h is not None:
            out.setdefault(a["id_servicio"], []).append(h)
    return out


def _intervalos_por_paciente(ctx: _Ctx) -> dict:
    """{dni: [(ingreso, egreso)]} con fechas; una internación activa dura hasta date.max."""
    registros = _registros_por_id(ctx)
    out: dict = {}
    for n in ctx.filas("internacion"):
        r = registros.get(n["id_registro_hc"])
        ingreso = _instante(n.get("fecha_ingreso"))
        if r is None or ingreso is None:
            continue
        egreso = _instante(n.get("fecha_egreso"))
        out.setdefault(r["dni_paciente"], []).append(
            (ingreso.date(), egreso.date() if egreso else date.max)
        )
    return out


def _se_superpone(intervalos: list, inicio: date, fin: date) -> bool:
    return any(inicio <= f and i <= fin for i, f in intervalos)


# ---------------------------------------------------------------------------
# Arreglos por violación (solo agregan)
# ---------------------------------------------------------------------------
# Cada función recibe (ctx, violación) y devuelve True si la violación quedó
# resuelta (agregando filas, o porque un arreglo anterior ya la resolvió) y
# False si no hay forma de resolverla sin modificar o borrar.


def _reparar_especialidades_requeridas(ctx: _Ctx, v: Violacion) -> bool:
    ps = ctx.filas("personal_servicio")[v.fila]
    tipo = next(
        (
            s["nombre_tipo_servicio"]
            for s in ctx.filas("servicio")
            if s["id"] == ps["id_servicio"]
        ),
        None,
    )
    if tipo is None:
        return False
    requeridas = {
        er["nombre_especialidad"]
        for er in ctx.filas("especialidad_requerida")
        if er["nombre_tipo_servicio"] == tipo
    }
    tiene = {
        ee["nombre_especialidad"]
        for ee in ctx.filas("especializado_en")
        if ee["matricula_personal"] == ps["matricula_personal"]
    }
    for esp in sorted(requeridas - tiene):
        ctx.agregar(
            "especializado_en",
            {
                "matricula_personal": ps["matricula_personal"],
                "nombre_especialidad": esp,
            },
            f"se otorga {esp!r} a {ps['matricula_personal']} (la exige el servicio "
            f"{ps['id_servicio']}, tipo {tipo})",
        )
    return True


def _reparar_fk_especialidad(ctx: _Ctx, v: Violacion) -> bool:
    """Una FK a `especialidad` sin resolver se arregla agregando esa especialidad
    (su única columna es el nombre, así que no hay nada que inventar). Las demás
    FK referencian filas con datos propios que no se pueden fabricar."""
    fila = ctx.filas(v.tabla)[v.fila]
    resuelta = True
    for tabla, columna, ref_tabla, _ in CLAVES_FORANEAS:
        if tabla != v.tabla:
            continue
        valor = fila.get(columna)
        existentes = {f.get("nombre") for f in ctx.filas(ref_tabla)}
        if valor is None or valor in existentes:
            continue
        if ref_tabla == "especialidad" and isinstance(valor, str):
            ctx.agregar(
                "especialidad",
                {"nombre": valor},
                f"se agrega la especialidad {valor!r} que referencia {tabla}.{columna}",
            )
        else:
            resuelta = False
    return resuelta


def _horarios_que_cubren(ctx: _Ctx, id_servicio, instante) -> list[dict]:
    """Horarios aún no vinculados al servicio que sirven para esa visita."""
    dia = DIAS[instante.weekday()]
    vinculados = {
        a["id_horario"]
        for a in ctx.filas("atencion_servicio")
        if a["id_servicio"] == id_servicio
    }
    con_hora = instante.time() != time.min
    out = []
    for h in sorted(ctx.filas("horario_atencion"), key=lambda h: h["id"]):
        if h["dia"] != dia or h["id"] in vinculados:
            continue
        if con_hora:
            apertura, cierre = _hora(h["apertura"]), _hora(h["cierre"])
            if (
                apertura is None
                or cierre is None
                or not (apertura <= instante.time() <= cierre)
            ):
                continue
        out.append(h)
    return out


def _visita_cubierta(ctx: _Ctx, id_servicio, instante) -> bool:
    dia = DIAS[instante.weekday()]
    con_hora = instante.time() != time.min
    for h in _horarios_por_servicio(ctx).get(id_servicio, []):
        if h["dia"] != dia:
            continue
        if not con_hora:
            return True
        apertura, cierre = _hora(h["apertura"]), _hora(h["cierre"])
        if (
            apertura is not None
            and cierre is not None
            and apertura <= instante.time() <= cierre
        ):
            return True
    return False


def _reparar_visita_en_horario(ctx: _Ctx, v: Violacion) -> bool:
    r = ctx.filas("registro_hc")[v.fila]
    instante = _instante(r.get("dia_visita"))
    if instante is None:
        return False
    id_servicio = r["id_servicio"]
    if _visita_cubierta(ctx, id_servicio, instante):  # ya la resolvió otro arreglo
        return True
    candidatos = _horarios_que_cubren(ctx, id_servicio, instante)
    if not candidatos:
        return False  # ningún horario existente atiende ese día/hora
    h = ctx.rng.choice(candidatos)
    ctx.agregar(
        "atencion_servicio",
        {"id_servicio": id_servicio, "id_horario": h["id"]},
        f"el servicio {id_servicio} pasa a atender el horario {h['id']} "
        f"({h['dia']} {h['apertura']}-{h['cierre']}) para cubrir la visita "
        f"{r['dia_visita']!r}",
    )
    return True


_REPARADORES = {
    "especialidades_requeridas": _reparar_especialidades_requeridas,
    "fk": _reparar_fk_especialidad,
    "visita_en_horario": _reparar_visita_en_horario,
}


# ---------------------------------------------------------------------------
# Completar conteos que quedaron por debajo del objetivo del Excel
# ---------------------------------------------------------------------------


def _completar_personal_servicio(ctx: _Ctx) -> None:
    objetivo = ctx.objetivos.get("personal_servicio")
    if objetivo is None:
        return
    faltan = objetivo - len(ctx.filas("personal_servicio"))
    if faltan <= 0:
        return

    asignados = {ps["matricula_personal"] for ps in ctx.filas("personal_servicio")}
    libres = [p for p in ctx.filas("personal") if p["matricula"] not in asignados]
    ctx.rng.shuffle(libres)
    tipos = {t["nombre"]: t for t in ctx.filas("tipo_servicio")}
    roles = {p["matricula"]: p["rol"] for p in ctx.filas("personal")}
    cantidad: Counter = Counter(
        (ps["id_servicio"], roles.get(ps["matricula_personal"]))
        for ps in ctx.filas("personal_servicio")
    )
    requeridas: dict = {}
    for er in ctx.filas("especialidad_requerida"):
        requeridas.setdefault(er["nombre_tipo_servicio"], set()).add(
            er["nombre_especialidad"]
        )
    especialidades: dict = {}
    for ee in ctx.filas("especializado_en"):
        especialidades.setdefault(ee["matricula_personal"], set()).add(
            ee["nombre_especialidad"]
        )
    servicios = ctx.filas("servicio")

    agregados = 0
    for persona in libres:
        if agregados >= faltan:
            break
        campo = "num_medicos" if persona["rol"] == ROL_MEDICO else "num_enfermeros"
        opciones = []
        for s in servicios:
            tipo = tipos.get(s["nombre_tipo_servicio"])
            if tipo is None or cantidad[(s["id"], persona["rol"])] >= tipo.get(
                campo, 0
            ):
                continue
            sin_tener = requeridas.get(tipo["nombre"], set()) - especialidades.get(
                persona["matricula"], set()
            )
            opciones.append((len(sin_tener), ctx.rng.random(), s, sin_tener))
        if not opciones:
            continue
        # Se prefiere el servicio al que la persona le falten menos especialidades.
        _, _, servicio, sin_tener = min(opciones, key=lambda o: (o[0], o[1]))
        for esp in sorted(sin_tener):
            ctx.agregar(
                "especializado_en",
                {
                    "matricula_personal": persona["matricula"],
                    "nombre_especialidad": esp,
                },
                f"se otorga {esp!r} a {persona['matricula']} para asignarla al servicio "
                f"{servicio['id']}",
            )
            especialidades.setdefault(persona["matricula"], set()).add(esp)
        ctx.agregar(
            "personal_servicio",
            {"id_servicio": servicio["id"], "matricula_personal": persona["matricula"]},
            f"se asigna {persona['matricula']} ({persona['rol']}) al servicio {servicio['id']}",
        )
        cantidad[(servicio["id"], persona["rol"])] += 1
        agregados += 1


def _completar_atencion_servicio(ctx: _Ctx) -> None:
    objetivo = ctx.objetivos.get("atencion_servicio")
    if objetivo is None:
        return
    faltan = objetivo - len(ctx.filas("atencion_servicio"))
    if faltan <= 0:
        return
    existentes = {
        (a["id_servicio"], a["id_horario"]) for a in ctx.filas("atencion_servicio")
    }
    candidatos = [
        (s["id"], h["id"])
        for s in ctx.filas("servicio")
        for h in ctx.filas("horario_atencion")
        if (s["id"], h["id"]) not in existentes
    ]
    ctx.rng.shuffle(candidatos)
    for id_servicio, id_horario in candidatos[:faltan]:
        ctx.agregar(
            "atencion_servicio",
            {"id_servicio": id_servicio, "id_horario": id_horario},
            f"el servicio {id_servicio} suma el horario {id_horario}",
        )


def _completar_especializado_en(ctx: _Ctx) -> None:
    objetivo = ctx.objetivos.get("especializado_en")
    if objetivo is None:
        return
    faltan = objetivo - len(ctx.filas("especializado_en"))
    if faltan <= 0:
        return
    todas = sorted(e["nombre"] for e in ctx.filas("especialidad"))
    tiene: dict = {}
    for ee in ctx.filas("especializado_en"):
        tiene.setdefault(ee["matricula_personal"], set()).add(ee["nombre_especialidad"])
    medicos = [p["matricula"] for p in ctx.filas("personal") if p["rol"] == ROL_MEDICO]
    ctx.rng.shuffle(medicos)

    while faltan > 0:
        progreso = False
        # Primero los médicos con menos especialidades (la segunda de cada uno).
        for matricula in sorted(medicos, key=lambda m: len(tiene.get(m, ()))):
            if faltan <= 0:
                break
            libres = [e for e in todas if e not in tiene.get(matricula, set())]
            if not libres:
                continue
            esp = ctx.rng.choice(libres)
            tiene.setdefault(matricula, set()).add(esp)
            ctx.agregar(
                "especializado_en",
                {"matricula_personal": matricula, "nombre_especialidad": esp},
                f"se otorga {esp!r} a {matricula} como especialidad adicional",
            )
            faltan -= 1
            progreso = True
        if not progreso:
            break


# --- registros e internaciones ------------------------------------------------


def _servicios_con_medico_y_horario(ctx: _Ctx, solo_interna: bool) -> list[dict]:
    medicos = _medicos_por_servicio(ctx)
    horarios = _horarios_por_servicio(ctx)
    interna = _interna_por_servicio(ctx)
    return [
        s
        for s in ctx.filas("servicio")
        if medicos.get(s["id"])
        and horarios.get(s["id"])
        and (interna[s["id"]] or not solo_interna)
    ]


def _caso_para(ctx: _Ctx, servicio: dict):
    """(diagnostico, tratamiento) coherente con el tipo del servicio, o None."""
    tipo = next(
        (
            t
            for t in ctx.filas("tipo_servicio")
            if t["nombre"] == servicio["nombre_tipo_servicio"]
        ),
        None,
    )
    if tipo is not None and tipo.get("casos"):
        caso = ctx.rng.choice(tipo["casos"])
        return caso["diagnostico"], caso["tratamiento"]
    # Sin catálogo de casos en las tablas: se reutiliza un par que ya exista
    # en un registro de un servicio del mismo tipo.
    mismos = {
        s["id"]
        for s in ctx.filas("servicio")
        if s["nombre_tipo_servicio"] == servicio["nombre_tipo_servicio"]
    }
    pares = [
        (r["diagnostico"], r["tratamiento"])
        for r in ctx.filas("registro_hc")
        if r["id_servicio"] in mismos
    ]
    return ctx.rng.choice(pares) if pares else None


def _armar_registro(ctx: _Ctx, servicios: list[dict], reciente: bool):
    """Arma (sin agregar) un registro válido: (fila, fecha, dni) o None si el sorteo no cierra."""
    rng, hoy = ctx.rng, ctx.hoy
    servicio = rng.choice(servicios)
    horario = rng.choice(_horarios_por_servicio(ctx)[servicio["id"]])
    paciente = rng.choice(ctx.filas("paciente"))
    centro = next(
        (
            c
            for c in ctx.filas("centro_de_salud")
            if c["id"] == servicio["id_centro_salud"]
        ),
        None,
    )
    nacimiento, inauguracion = (
        _instante(paciente.get("nacimiento")),
        (_instante(centro.get("inaguracion")) if centro else None),
    )
    if nacimiento is None or inauguracion is None:
        return None

    if reciente:
        desde = hoy - timedelta(days=INTERNACION_ACTUAL_DIAS[1])
        hasta = hoy - timedelta(days=INTERNACION_ACTUAL_DIAS[0])
    else:
        desde = hoy - timedelta(days=365 * VENTANA_VISITAS_ANIOS)
        hasta = hoy - timedelta(days=1)
    # Estrictamente posterior a la inauguración y al nacimiento.
    desde = max(
        desde,
        inauguracion.date() + timedelta(days=1),
        nacimiento.date() + timedelta(days=1),
    )
    dia = DIAS.index(horario["dia"])
    fechas = [
        desde + timedelta(days=d)
        for d in range((hasta - desde).days + 1)
        if (desde + timedelta(days=d)).weekday() == dia
    ]
    caso = _caso_para(ctx, servicio)
    if not fechas or caso is None:
        return None

    fecha = rng.choice(fechas)
    fila = {
        "id_servicio": servicio["id"],
        "dni_paciente": paciente["dni"],
        "matricula_personal": rng.choice(_medicos_por_servicio(ctx)[servicio["id"]]),
        "dia_visita": fecha.isoformat(),
        "diagnostico": caso[0],
        "tratamiento": caso[1],
    }
    id_nuevo = _proximo_id_registro(ctx)
    if id_nuevo is not None:
        fila = {"id": id_nuevo, **fila}
    return fila, fecha, paciente["dni"]


def _completar_registros(ctx: _Ctx) -> None:
    objetivo = ctx.objetivos.get("registro_hc")
    if objetivo is None:
        return
    servicios = _servicios_con_medico_y_horario(ctx, solo_interna=False)
    if not servicios or not ctx.filas("paciente"):
        return
    intentos = 0
    while (
        len(ctx.filas("registro_hc")) < objetivo
        and intentos < MAX_INTENTOS_ELEMENTO_NUEVO * 10
    ):
        intentos += 1
        armado = _armar_registro(ctx, servicios, reciente=False)
        if armado is None:
            continue
        fila, fecha, dni = armado
        ctx.agregar(
            "registro_hc",
            fila,
            f"visita nueva del {fila['dia_visita']} (servicio {fila['id_servicio']}, "
            f"paciente {dni})",
        )


def _duracion_pasada(ctx: _Ctx, fecha: date):
    """Fecha de egreso estrictamente posterior al ingreso y anterior a hoy, o None."""
    dur_min, dur_max = DURACION_INTERNACION_DIAS
    dias_max = min(dur_max, (ctx.hoy - timedelta(days=1) - fecha).days)
    if dias_max < dur_min:
        return None
    return fecha + timedelta(days=ctx.rng.randint(dur_min, dias_max))


def _agregar_internacion(ctx: _Ctx, id_registro, fecha_ingreso, egreso, dni) -> None:
    ctx.agregar(
        "internacion",
        {
            "id": _proximo_id(ctx, "internacion"),
            "id_registro_hc": id_registro,
            "fecha_ingreso": fecha_ingreso,
            "fecha_egreso": egreso.isoformat() if egreso else None,
        },
        f"internación {'actual' if egreso is None else 'pasada'} del paciente {dni} "
        f"sobre el registro {id_registro}",
    )


def _internacion_sobre_registro_existente(ctx: _Ctx, actual: bool) -> bool:
    """Arreglo preferido: internar un registro que ya existe (agrega 1 fila)."""
    internados = {n["id_registro_hc"] for n in ctx.filas("internacion")}
    interna = _interna_por_servicio(ctx)
    intervalos = _intervalos_por_paciente(ctx)
    candidatos = [
        (i, r)
        for i, r in sorted(_registros_por_id(ctx).items(), key=lambda x: str(x[0]))
        if i not in internados and interna.get(r["id_servicio"], False)
    ]
    ctx.rng.shuffle(candidatos)
    for id_registro, r in candidatos:
        visita = _instante(r.get("dia_visita"))
        if visita is None or visita.date() >= ctx.hoy:
            continue
        fecha = visita.date()
        if actual:
            if not (
                ctx.hoy - timedelta(days=INTERNACION_ACTUAL_DIAS[1])
                <= fecha
                <= ctx.hoy - timedelta(days=INTERNACION_ACTUAL_DIAS[0])
            ):
                continue
            egreso, fin = None, date.max
        else:
            egreso = _duracion_pasada(ctx, fecha)
            if egreso is None:
                continue
            fin = egreso
        if _se_superpone(intervalos.get(r["dni_paciente"], []), fecha, fin):
            continue
        _agregar_internacion(
            ctx, id_registro, r["dia_visita"], egreso, r["dni_paciente"]
        )
        return True
    return False


def _internacion_con_registro_nuevo(ctx: _Ctx, actual: bool) -> bool:
    """Último recurso: crea un registro nuevo y lo interna (agrega 2 filas)."""
    servicios = _servicios_con_medico_y_horario(ctx, solo_interna=True)
    if not servicios or not ctx.filas("paciente"):
        return False
    intervalos = _intervalos_por_paciente(ctx)
    for _ in range(MAX_INTENTOS_ELEMENTO_NUEVO):
        armado = _armar_registro(ctx, servicios, reciente=actual)
        if armado is None:
            continue
        fila, fecha, dni = armado
        if actual:
            egreso, fin = None, date.max
        else:
            egreso = _duracion_pasada(ctx, fecha)
            if egreso is None:
                continue
            fin = egreso
        if _se_superpone(intervalos.get(dni, []), fecha, fin):
            continue
        ctx.agregar(
            "registro_hc",
            fila,
            f"visita nueva del {fila['dia_visita']} para poder internar al "
            f"paciente {dni} (servicio {fila['id_servicio']})",
        )
        id_registro = fila.get("id", len(ctx.filas("registro_hc")))
        _agregar_internacion(ctx, id_registro, fila["dia_visita"], egreso, dni)
        return True
    return False


def _completar_internaciones(ctx: _Ctx) -> None:
    if "internacion" not in ctx.objetivos:
        return
    filas = ctx.filas("internacion")
    n_actuales = sum(1 for n in filas if n.get("fecha_egreso") is None)
    n_pasadas = len(filas) - n_actuales
    for actual, faltan in (
        (True, ctx.actuales - n_actuales),
        (False, ctx.pasadas - n_pasadas),
    ):
        for _ in range(max(0, faltan)):
            if not (
                _internacion_sobre_registro_existente(ctx, actual)
                or _internacion_con_registro_nuevo(ctx, actual)
            ):
                break


def _completar_conteos(ctx: _Ctx) -> None:
    # Orden: lo que otros completan después usa estas tablas.
    _completar_personal_servicio(ctx)
    _completar_atencion_servicio(ctx)
    _completar_especializado_en(ctx)
    _completar_registros(ctx)
    _completar_internaciones(
        ctx
    )  # al final: puede reutilizar los registros recién agregados


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def reparar(
    tablas: dict[str, list[dict]],
    *,
    objetivos: dict[str, int] | None = None,
    internaciones_actuales: int | None = None,
    internaciones_pasadas: int | None = None,
    seed: int | None = None,
    hoy: date | None = None,
    max_iteraciones: int | None = None,
) -> Resultado:
    """Repara las tablas agregando filas; devuelve un Resultado o lanza ReparacionFallida.

    Args:
        tablas: {tabla: lista de filas}. No se modifica (ni las listas ni las filas).
        objetivos: cantidad objetivo por tabla (por defecto config.TOTALES). Una
            tabla que no figura no se completa. Si figura "internacion" se completan
            las internaciones actuales y pasadas.
        internaciones_actuales / internaciones_pasadas: por defecto las de config.
        seed: semilla del azar (por defecto config.SEED): mismo input y misma
            semilla dan el mismo resultado.
        hoy: fecha de referencia (por defecto FECHA_REFERENCIA o la fecha actual).
        max_iteraciones: tope del bucle (por defecto config.MAX_ITERACIONES_REPARACION).
    """
    if objetivos is None:
        objetivos = dict(TOTALES)
    ctx = _Ctx(
        tablas,
        objetivos,
        INTERNACIONES_ACTUALES
        if internaciones_actuales is None
        else internaciones_actuales,
        INTERNACIONES_PASADAS
        if internaciones_pasadas is None
        else internaciones_pasadas,
        random.Random(SEED if seed is None else seed),
        hoy if hoy is not None else _hoy(),
    )
    tope = MAX_ITERACIONES_REPARACION if max_iteraciones is None else max_iteraciones

    def resultado(iteraciones: int) -> Resultado:
        return Resultado(ctx.t, ctx.agregadas, iteraciones, ctx.acciones, objetivos)

    violaciones: list[Violacion] = []
    for iteracion in range(1, tope + 1):
        violaciones = validar(ctx.t, hoy=ctx.hoy)
        antes = ctx.total_agregado()

        if violaciones:
            for v in violaciones:
                arreglo = _REPARADORES.get(v.regla)
                if arreglo is not None:
                    arreglo(ctx, v)
        else:
            _completar_conteos(ctx)

        if ctx.total_agregado() == antes:  # esta pasada no avanzó
            if violaciones:
                raise ReparacionFallida(
                    _mensaje_fallo(violaciones, iteracion, tope, agotado=False),
                    violaciones,
                    iteracion,
                    resultado(iteracion),
                )
            return resultado(iteracion)

    violaciones = validar(ctx.t, hoy=ctx.hoy)
    if not violaciones:  # el último paso dejó todo en orden
        return resultado(tope)
    raise ReparacionFallida(
        _mensaje_fallo(violaciones, tope, tope, agotado=True),
        violaciones,
        tope,
        resultado(tope),
    )


def _mensaje_fallo(
    violaciones: list[Violacion], iteraciones: int, tope: int, agotado: bool
) -> str:
    causa = (
        f"se agotó el tope de {tope} iteraciones"
        if agotado
        else f"la iteración {iteraciones} no pudo avanzar"
    )
    grupos: dict = {}
    for v in violaciones:
        grupos.setdefault((v.regla, v.tabla), []).append(v)
    lineas = [
        (
            f"No se pudo reparar: {causa} y quedan {len(violaciones)} violaciones "
            f"sin resolver. El reparador solo agrega filas (nunca borra ni modifica), "
            f"por eso estas hay que corregirlas en el generador que las produjo:"
        )
    ]
    for (regla, tabla), vs in sorted(grupos.items()):
        lineas.append(f"  - {regla} en {tabla}: {len(vs)} fila(s)")
        for v in vs[:EJEMPLOS_POR_REGLA_EN_MENSAJE]:
            lineas.append(f"      {v}")
        if len(vs) > EJEMPLOS_POR_REGLA_EN_MENSAJE:
            lineas.append(f"      ... y {len(vs) - EJEMPLOS_POR_REGLA_EN_MENSAJE} más")
    lineas.append("No se emite el SQL.")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Reporte final
# ---------------------------------------------------------------------------


def reporte(
    tablas: dict[str, list[dict]],
    objetivos: dict[str, int] | None = None,
    agregadas: Counter | None = None,
) -> str:
    """Total por tabla contra el Excel, para actualizarlo a mano.

    Las columnas son: objetivo del Excel, filas generadas y diferencia
    (generado - Excel, con signo).
    """
    if objetivos is None:
        objetivos = dict(TOTALES)
    nombres = list(objetivos) + [t for t in tablas if t not in objetivos]
    ancho = max(len("Tabla"), *(len(n) for n in nombres))

    lineas = [f"{'Tabla':<{ancho}}  {'Excel':>7}  {'Generado':>9}  {'Dif.':>6}"]
    total_excel = total_generado = 0
    for nombre in nombres:
        excel = objetivos.get(nombre)
        generado = len(tablas.get(nombre) or [])
        total_generado += generado
        if excel is None:
            lineas.append(f"{nombre:<{ancho}}  {'-':>7}  {generado:>9}  {'-':>6}")
            continue
        total_excel += excel
        dif = generado - excel
        lineas.append(
            f"{nombre:<{ancho}}  {excel:>7}  {generado:>9}  "
            f"{('0' if dif == 0 else f'{dif:+d}'):>6}"
        )
    dif_total = total_generado - total_excel
    lineas.append("-" * len(lineas[0]))
    lineas.append(
        f"{'Total':<{ancho}}  {total_excel:>7}  {total_generado:>9}  "
        f"{('0' if dif_total == 0 else f'{dif_total:+d}'):>6}"
    )

    internaciones = tablas.get("internacion") or []
    if internaciones:
        actuales = sum(1 for n in internaciones if n.get("fecha_egreso") is None)
        lineas.append(
            f"Internaciones: {actuales} actuales + {len(internaciones) - actuales} pasadas"
        )
    if agregadas:
        detalle = ", ".join(f"{t} +{n}" for t, n in sorted(agregadas.items()))
        lineas.append(f"Filas agregadas por la reparación: {detalle}")
    else:
        lineas.append("La reparación no agregó filas.")
    return "\n".join(lineas)
