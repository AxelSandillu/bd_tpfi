"""Emisión del archivo SQL de poblado de PostgreSQL.

Recibe un diccionario con listas de filas (una lista de diccionarios por
cada tabla), genera INSERT por lotes en el orden requerido por las FK y los
triggers y escribe un único archivo dentro de una transacción.

Los campos auxiliares que algunos generadores agregan a sus diccionarios se
ignoran: las columnas se definen explícitamente según scripts/01_init.sql.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

from config import RUTA_SALIDA

# El orden respeta las dependencias de FK y los requisitos de los triggers.
ORDEN_TABLAS: tuple[str, ...] = (
    "departamento",
    "ciudad",
    "barrio",
    "obra_social",
    "paciente",
    "centro_de_salud",
    "personal",
    "especialidad",
    "especializado_en",
    "tipo_servicio",
    "especialidad_requerida",
    "horario_atencion",
    "atencion_centro",
    "servicio",
    "atencion_servicio",
    "personal_servicio",
    "registro_hc",
    "internacion",
)

# Columnas reales de PostgreSQL según scripts/01_init.sql. No incluir campos
# auxiliares del generador como id_georef, peso, interna o listas de casos.
COLUMNAS_TABLAS: dict[str, tuple[str, ...]] = {
    "departamento": ("id", "nombre"),
    "ciudad": ("id", "id_departamento", "nombre"),
    "barrio": ("id", "id_ciudad", "nombre"),
    "obra_social": ("id", "razon_social", "estado"),
    "paciente": ("dni", "id_obra_social", "nombre", "apellido", "nacimiento", "num_asociado"),
    "centro_de_salud": ("id", "id_barrio", "nombre", "inaguracion", "calle", "altura"),
    "personal": ("matricula", "nombre", "apellido", "telefono", "email", "nacimiento", "rol"),
    "especialidad": ("nombre",),
    "especializado_en": ("matricula_personal", "nombre_especialidad"),
    "tipo_servicio": ("nombre", "num_enfermeros", "num_medicos"),
    "especialidad_requerida": ("nombre_tipo_servicio", "nombre_especialidad"),
    "horario_atencion": ("id", "apertura", "cierre", "dia"),
    "atencion_centro": ("id_centro_salud", "id_horario"),
    "servicio": ("id", "id_centro_salud", "nombre_tipo_servicio", "matricula_encargado"),
    "atencion_servicio": ("id_servicio", "id_horario"),
    "personal_servicio": ("id_servicio", "matricula_personal"),
    "registro_hc": ("id", "id_servicio", "dni_paciente", "matricula_personal", "dia_visita", "diagnostico", "tratamiento"),
    "internacion": ("id", "id_registro_hc", "fecha_ingreso", "fecha_egreso"),
}

TABLAS_IDENTITY: tuple[str, ...] = (
    "departamento",
    "ciudad",
    "barrio",
    "obra_social",
    "centro_de_salud",
    "servicio",
    "registro_hc",
    "internacion",
    "horario_atencion",
)


def _sql_cadena(valor: str) -> str:
    """Escapa una cadena para un literal SQL estándar de PostgreSQL."""
    if "\x00" in valor:
        raise ValueError("PostgreSQL no admite el carácter NUL en valores de texto")
    return "'" + valor.replace("'", "''") + "'"


def _sql_valor(valor: Any) -> str:
    """Convierte un valor Python en un literal SQL seguro y determinista.

    Los literales de texto de columnas ENUM y DOMAIN se dejan sin CAST
    explícito: PostgreSQL infiere el tipo desde la columna destino del INSERT.
    """
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, datetime):
        return _sql_cadena(valor.isoformat(sep=" "))
    if isinstance(valor, (date, time)):
        return _sql_cadena(valor.isoformat())
    if isinstance(valor, str):
        return _sql_cadena(valor)
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, (float, Decimal)):
        # Evita emitir NaN/Infinity como si fueran números SQL comunes.
        if isinstance(valor, float) and (valor != valor or valor in (float("inf"), float("-inf"))):
            raise ValueError(f"Valor numérico no finito: {valor!r}")
        return str(valor)
    raise TypeError(f"Tipo de dato no soportado para SQL: {type(valor).__name__}")


def _sql_fila(tabla: str, fila: dict[str, Any]) -> str:
    """Serializa una fila usando exclusivamente las columnas de la tabla."""
    columnas = COLUMNAS_TABLAS[tabla]
    faltantes = [columna for columna in columnas if columna not in fila]
    if faltantes:
        raise ValueError(
            f"Faltan columnas para {tabla}: {', '.join(faltantes)}"
        )
    return "(" + ", ".join(_sql_valor(fila[columna]) for columna in columnas) + ")"


def _generar_insert(tabla: str, filas: list[dict[str, Any]], tamano_lote: int) -> list[str]:
    """Genera uno o más INSERT de la tabla, divididos en lotes."""
    if tabla not in COLUMNAS_TABLAS:
        raise ValueError(f"Tabla no contemplada por el emisor: {tabla}")
    if not filas:
        return []

    columnas = COLUMNAS_TABLAS[tabla]
    lista_columnas = ", ".join(columnas)
    overriding = " OVERRIDING SYSTEM VALUE" if tabla in TABLAS_IDENTITY else ""
    sentencias = []

    for inicio in range(0, len(filas), tamano_lote):
        lote = filas[inicio : inicio + tamano_lote]
        valores = ",\n".join(f"    {_sql_fila(tabla, fila)}" for fila in lote)
        sentencias.append(
            f"INSERT INTO {tabla} ({lista_columnas}){overriding} VALUES\n{valores};"
        )
    return sentencias


def _generar_setval() -> list[str]:
    """Genera el ajuste de las nueve secuencias IDENTITY del esquema."""
    sentencias = []
    for tabla in TABLAS_IDENTITY:
        secuencia = f"pg_get_serial_sequence('public.{tabla}', 'id')"
        sentencias.append(
            "SELECT setval(\n"
            f"    {secuencia},\n"
            f"    COALESCE((SELECT MAX(id) FROM {tabla}), 1),\n"
            f"    EXISTS (SELECT 1 FROM {tabla})\n"
            ");"
        )
    return sentencias


def emitir(
    datos: dict[str, list[dict[str, Any]]],
    ruta_salida: str | Path | None = None,
    tamano_lote: int = 500,
) -> Path:
    """Emite ``02_seed.sql`` y devuelve la ruta del archivo generado.

    Args:
        datos: diccionario tabla -> lista de filas generadas y reparadas.
              Las tablas ausentes se consideran vacías.
        ruta_salida: destino opcional. Por defecto usa config.RUTA_SALIDA.
        tamano_lote: cantidad máxima de filas por sentencia INSERT.

    Raises:
        TypeError/ValueError: si la entrada, el tamaño de lote o un valor no
            pueden serializarse correctamente.
        OSError: si no se puede crear o escribir el archivo.
    """
    if not isinstance(datos, dict):
        raise TypeError("'datos' debe ser un diccionario de tablas")
    if not isinstance(tamano_lote, int) or isinstance(tamano_lote, bool) or tamano_lote <= 0:
        raise ValueError("tamano_lote debe ser un entero mayor que cero")

    destino = Path(ruta_salida if ruta_salida is not None else RUTA_SALIDA)
    lineas = [
        "-- Archivo generado automáticamente. No editar manualmente.",
        "-- La carga completa se ejecuta dentro de una única transacción.",
        "BEGIN;",
        "",
    ]

    for tabla in ORDEN_TABLAS:
        filas = datos.get(tabla, [])
        if not isinstance(filas, list):
            raise TypeError(f"Los datos de '{tabla}' deben ser una lista de filas")

        # Los generadores actuales de registro_hc no asignan ID y el módulo
        # de internaciones todavía depende del reparador. En esas dos tablas,
        # la PK IDENTITY se materializa aquí de forma determinista si falta.
        # Si una versión futura ya proporciona el ID, se conserva.
        if tabla in ("registro_hc", "internacion"):
            filas = [
                {**fila, "id": fila.get("id", indice)}
                for indice, fila in enumerate(filas, start=1)
            ]

        if filas:
            lineas.append(f"-- {tabla}: {len(filas)} filas")
            lineas.extend(_generar_insert(tabla, filas, tamano_lote))
            lineas.append("")

    lineas.append("-- Sincronización de secuencias IDENTITY")
    lineas.extend(_generar_setval())
    lineas.extend(("", "COMMIT;", ""))

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8", newline="\n")
    return destino
