"""Validador independiente de las tablas generadas en memoria y de tipos_servicio.json.

Recorre las tablas ya armadas sin usar los pools y devuelve violaciones
(tabla, fila, regla). Verifica UNIQUE, largos máximos, regex (matrícula,
teléfono, email), FK resueltas, cupos y especialidades por servicio, un
servicio por persona, (centro, tipo) único, encargado médico, registros
atendidos por un médico del servicio, ingreso = visita, egreso >= ingreso,
fechas anteriores a hoy, visitas dentro del horario del servicio e
internaciones sin solapamiento.

TODO (issue #15): implementar validar() y todas las reglas de la sección 10.
"""

import json
from pathlib import Path


class TiposServicioInvalido(Exception):
    """El archivo tipos_servicio.json no cumple las reglas de arranque."""

    pass


def cargar_tipos_servicio(ruta: str) -> dict:
    """Lee y valida data/tipos_servicio.json al arrancar.

    Devuelve el dict parseado si es válido. Lanza TiposServicioInvalido con un
    mensaje que indica el tipo y el campo que falló si el JSON es inválido.
    """
    path = Path(ruta)
    if not path.exists():
        raise TiposServicioInvalido(
            f"No se encontró el archivo de tipos de servicio: {ruta}"
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TiposServicioInvalido(
            f"JSON mal formado en {ruta}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise TiposServicioInvalido(
            f"El JSON de {ruta} debe ser un objeto, se encontró {type(data).__name__}"
        )

    if "especialidades" not in data:
        raise TiposServicioInvalido(
            "tipos_servicio.json: falta la clave 'especialidades'"
        )
    if "tipos_servicio" not in data:
        raise TiposServicioInvalido(
            "tipos_servicio.json: falta la clave 'tipos_servicio'"
        )

    especialidades = data["especialidades"]
    tipos = data["tipos_servicio"]

    if not isinstance(especialidades, list):
        raise TiposServicioInvalido(
            "tipos_servicio.json: 'especialidades' debe ser una lista"
        )
    if not isinstance(tipos, list):
        raise TiposServicioInvalido(
            "tipos_servicio.json: 'tipos_servicio' debe ser una lista"
        )

    if len(especialidades) != 15:
        raise TiposServicioInvalido(
            f"tipos_servicio.json: se esperaban exactamente 15 especialidades, "
            f"se encontraron {len(especialidades)}"
        )
    if len(tipos) != 20:
        raise TiposServicioInvalido(
            f"tipos_servicio.json: se esperaban exactamente 20 tipos de servicio, "
            f"se encontraron {len(tipos)}"
        )

    # Nombres de especialidades únicos y ≤ 30 caracteres
    vistos_esp = set()
    for i, nombre in enumerate(especialidades):
        if not isinstance(nombre, str):
            raise TiposServicioInvalido(
                f"tipos_servicio.json: especialidades[{i}] debe ser texto, "
                f"se encontró {type(nombre).__name__}"
            )
        if len(nombre) > 30:
            raise TiposServicioInvalido(
                f"tipos_servicio.json: especialidades[{i}] = '{nombre}' excede "
                f"los 30 caracteres (tiene {len(nombre)})"
            )
        if nombre in vistos_esp:
            raise TiposServicioInvalido(
                f"tipos_servicio.json: especialidades[{i}] = '{nombre}' está duplicada"
            )
        vistos_esp.add(nombre)

    conjunto_especialidades = set(especialidades)

    # Validar cada tipo de servicio
    total_requeridas = 0
    hay_interna = False
    capacidad_total = 0

    for i, tipo in enumerate(tipos):
        if not isinstance(tipo, dict):
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] debe ser un objeto, "
                f"se encontró {type(tipo).__name__}"
            )

        nombre = tipo.get("nombre")
        if not isinstance(nombre, str):
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] falta el campo 'nombre' "
                f"o no es texto"
            )
        if len(nombre) > 30:
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                f"'nombre' excede los 30 caracteres (tiene {len(nombre)})"
            )

        num_medicos = tipo.get("num_medicos")
        if not isinstance(num_medicos, int) or isinstance(num_medicos, bool):
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                f"'num_medicos' debe ser un entero ≥ 1"
            )
        if num_medicos < 1:
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                f"'num_medicos' debe ser ≥ 1, se encontró {num_medicos}"
            )

        num_enfermeros = tipo.get("num_enfermeros")
        if not isinstance(num_enfermeros, int) or isinstance(num_enfermeros, bool):
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                f"'num_enfermeros' debe ser un entero ≥ 0"
            )
        if num_enfermeros < 0:
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                f"'num_enfermeros' debe ser ≥ 0, se encontró {num_enfermeros}"
            )

        requeridas = tipo.get("especialidades_requeridas")
        if not isinstance(requeridas, list):
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                f"'especialidades_requeridas' debe ser una lista"
            )
        total_requeridas += len(requeridas)
        for j, req in enumerate(requeridas):
            if not isinstance(req, str):
                raise TiposServicioInvalido(
                    f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                    f"'especialidades_requeridas[{j}]' debe ser texto, se encontró "
                    f"{type(req).__name__}"
                )
            if req not in conjunto_especialidades:
                raise TiposServicioInvalido(
                    f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                    f"'especialidades_requeridas[{j}]' = '{req}' no está en la "
                    f"lista de especialidades"
                )

        interna = tipo.get("interna")
        if not isinstance(interna, bool):
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                f"'interna' debe ser booleano, se encontró {type(interna).__name__}"
            )
        if interna:
            hay_interna = True

        casos = tipo.get("casos")
        if not isinstance(casos, list) or len(casos) < 1:
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                f"'casos' debe ser una lista con al menos 1 caso"
            )
        for k, caso in enumerate(casos):
            if not isinstance(caso, dict):
                raise TiposServicioInvalido(
                    f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                    f"'casos[{k}]' debe ser un objeto"
                )
            for campo in ("cie10", "diagnostico", "tratamiento"):
                if campo not in caso:
                    raise TiposServicioInvalido(
                        f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                        f"'casos[{k}]' falta el subcampo '{campo}'"
                    )
                if not isinstance(caso[campo], str):
                    raise TiposServicioInvalido(
                        f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                        f"'casos[{k}].{campo}' debe ser texto, se encontró "
                        f"{type(caso[campo]).__name__}"
                    )

        peso = tipo.get("peso")
        if peso is not None and not isinstance(peso, (int, float)) or isinstance(peso, bool):
            raise TiposServicioInvalido(
                f"tipos_servicio.json: tipos_servicio[{i}] ('{nombre}') campo "
                f"'peso' debe ser numérico"
            )

        capacidad_total += num_medicos + num_enfermeros

    if total_requeridas != 25:
        raise TiposServicioInvalido(
            f"tipos_servicio.json: se esperaban exactamente 25 filas de "
            f"'especialidades_requeridas' en total, se encontraron {total_requeridas}"
        )

    if not hay_interna:
        raise TiposServicioInvalido(
            "tipos_servicio.json: debe haber al menos un tipo con 'interna: true'"
        )

    # 70 servicios distribuidos entre los 20 tipos => ~3.5 servicios por tipo.
    # Capacidad esperada = suma_de_cupos * (70 / num_tipos) >= 150.
    if capacidad_total * 70 < 150 * len(tipos):
        raise TiposServicioInvalido(
            f"tipos_servicio.json: la capacidad total de personal es insuficiente "
            f"para los 70 servicios. Suma de cupos (num_medicos + num_enfermeros) "
            f"de todos los tipos = {capacidad_total}; con 70 servicios y "
            f"{len(tipos)} tipos se esperan al menos 150 asignaciones "
            f"(personal_servicio en config.py). Aumente num_medicos y/o "
            f"num_enfermeros de algunos tipos."
        )

    return data
