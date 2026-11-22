"""Validador independiente de las tablas generadas en memoria y de tipos_servicio.json.

Recorre las tablas ya armadas sin usar los pools y devuelve violaciones
(tabla, fila, regla). Verifica UNIQUE, largos máximos, regex (matrícula,
teléfono, email), FK resueltas, cupos y especialidades por servicio, un
servicio por persona, (centro, tipo) único, encargado médico, registros
atendidos por un médico del servicio, ingreso = visita, egreso >= ingreso,
fechas anteriores a hoy, visitas dentro del horario del servicio e
internaciones sin solapamiento.

Contiene dos validaciones:

- cargar_tipos_servicio(): valida data/tipos_servicio.json al arrancar.
- validar(): valida las tablas ya armadas en memoria (issue #16). Es
  independiente: no importa pools ni generadores, solo recibe las tablas.

Las reglas replican las del esquema (01_init.sql) y las de los triggers
corregidos (02_triggers.sql), más las reglas de realismo de la sección 4 de
PLANIFICACION.md. Por eso los regex y los largos de este módulo no están en
config.py: no son ajustables, son una copia del esquema de la base y deben
coincidir con él.
"""

import json
import re
from datetime import date, datetime, time
from pathlib import Path
from typing import NamedTuple


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


# ===========================================================================
# Validador de las tablas generadas (issue #16)
# ===========================================================================

class Violacion(NamedTuple):
    """Una regla incumplida.

    tabla:   nombre de la tabla (clave del dict de tablas).
    fila:    posición (0-based) de la fila dentro de la lista de esa tabla.
    regla:   código corto y estable de la regla (ver REGLAS al final).
    detalle: explicación legible, con la clave de la fila y los valores.
    """

    tabla: str
    fila: int
    regla: str
    detalle: str

    def __str__(self) -> str:
        return f"[{self.tabla} fila {self.fila}] {self.regla}: {self.detalle}"


# --- Reglas del esquema (copia de 01_init.sql; no son ajustables) -----------

MAX_VARCHAR = 30  # largo de los VARCHAR(30) del esquema

# Se usan con fullmatch, por eso no llevan ^ ni $.
REGEX_MATRICULA = re.compile(r"[0-9]{2}[1-5][0-9]+")  # DOMAIN Matricula
REGEX_TELEFONO = re.compile(r"\+?[0-9\s\-\(\)]{7,15}")  # trigger de personal
REGEX_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.IGNORECASE)
MIN_DIGITOS_TELEFONO = 7
EDAD_MINIMA_PERSONAL = 18

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
ROLES = ("Médico", "Enfermero")

COLUMNAS_VARCHAR = {
    "departamento": ("nombre",),
    "ciudad": ("nombre",),
    "barrio": ("nombre",),
    "obra_social": ("razon_social",),
    "paciente": ("nombre", "apellido"),
    "centro_de_salud": ("nombre", "direccion", "calle"),
    "tipo_servicio": ("nombre",),
    "personal": ("nombre", "apellido", "telefono", "email"),
    "especialidad": ("nombre",),
}

# PK y UNIQUE por tabla. Una fila con algún valor None en la clave no cuenta
# (en SQL, NULL no viola UNIQUE). registro_hc.id puede no estar todavía en las
# filas (lo asigna el emisor): en ese caso no hay nada que comparar.
CLAVES_UNICAS = {
    "departamento": (("id",), ("nombre",)),
    "ciudad": (("id",), ("nombre",)),
    "barrio": (("id",), ("nombre",)),
    "obra_social": (("id",),),
    "paciente": (("dni",), ("num_asociado",)),
    "centro_de_salud": (("id",), ("nombre",)),
    "tipo_servicio": (("nombre",),),
    "personal": (("matricula",), ("telefono",), ("email",)),
    "especialidad": (("nombre",),),
    "servicio": (("id",),),
    "horario_atencion": (("id",),),
    "registro_hc": (("id",),),
    "internacion": (("id",),),
    "especializado_en": (("matricula_personal", "nombre_especialidad"),),
    "especialidad_requerida": (("nombre_tipo_servicio", "nombre_especialidad"),),
    "atencion_centro": (("id_centro_salud", "id_horario"),),
    "atencion_servicio": (("id_servicio", "id_horario"),),
    "personal_servicio": (("id_servicio", "matricula_personal"),),
}

# (tabla, columna, tabla referenciada, columna referenciada)
CLAVES_FORANEAS = (
    ("ciudad", "id_departamento", "departamento", "id"),
    ("barrio", "id_ciudad", "ciudad", "id"),
    ("paciente", "id_obra_social", "obra_social", "id"),
    ("centro_de_salud", "id_barrio", "barrio", "id"),
    ("servicio", "id_centro_salud", "centro_de_salud", "id"),
    ("servicio", "nombre_tipo_servicio", "tipo_servicio", "nombre"),
    ("servicio", "matricula_encargado", "personal", "matricula"),
    ("personal_servicio", "id_servicio", "servicio", "id"),
    ("personal_servicio", "matricula_personal", "personal", "matricula"),
    ("registro_hc", "id_servicio", "servicio", "id"),
    ("registro_hc", "dni_paciente", "paciente", "dni"),
    ("registro_hc", "matricula_personal", "personal", "matricula"),
    ("internacion", "id_registro_hc", "registro_hc", "id"),
    ("especializado_en", "matricula_personal", "personal", "matricula"),
    ("especializado_en", "nombre_especialidad", "especialidad", "nombre"),
    ("especialidad_requerida", "nombre_tipo_servicio", "tipo_servicio", "nombre"),
    ("especialidad_requerida", "nombre_especialidad", "especialidad", "nombre"),
    ("atencion_centro", "id_centro_salud", "centro_de_salud", "id"),
    ("atencion_centro", "id_horario", "horario_atencion", "id"),
    ("atencion_servicio", "id_servicio", "servicio", "id"),
    ("atencion_servicio", "id_horario", "horario_atencion", "id"),
)

# (tabla, columna): fechas que deben ser estrictamente anteriores a hoy.
# Los triggers comparan contra CURRENT_DATE de la base.
FECHAS_ANTERIORES_A_HOY = (
    ("centro_de_salud", "inaguracion"),
    ("paciente", "nacimiento"),
    ("personal", "nacimiento"),
    ("registro_hc", "dia_visita"),
    ("internacion", "fecha_ingreso"),
    ("internacion", "fecha_egreso"),
)


# --- Utilidades --------------------------------------------------------------

def _filas(tablas: dict, nombre: str) -> list[dict]:
    return tablas.get(nombre) or []


def _instante(valor) -> datetime | None:
    """str ISO ('YYYY-MM-DD', con hora o con 'Z'), date o datetime -> datetime sin zona."""
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None)
    if isinstance(valor, date):
        return datetime.combine(valor, time.min)
    if isinstance(valor, str):
        try:
            return datetime.fromisoformat(valor.strip().replace("Z", "+00:00")).replace(
                tzinfo=None
            )
        except ValueError:
            return None
    return None


def _hora(valor) -> time | None:
    if isinstance(valor, time):
        return valor
    if isinstance(valor, str):
        try:
            return time.fromisoformat(valor.strip())
        except ValueError:
            return None
    return None


def _ids_registro_hc(tablas: dict) -> dict:
    """{id del registro: fila}. Si la fila no trae `id`, vale su posición (1-based),
    que es el id que le toca al emitir el SQL con ids explícitos."""
    return {r.get("id", pos): r for pos, r in enumerate(_filas(tablas, "registro_hc"), start=1)}


def _valores_referenciables(tablas: dict, tabla: str, columna: str) -> set:
    if tabla == "registro_hc" and columna == "id":
        return set(_ids_registro_hc(tablas))
    return {f.get(columna) for f in _filas(tablas, tabla)}


def _edad(nacimiento: date, hoy: date) -> int:
    return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))


# --- Reglas por grupo ----------------------------------------------------------

def _unicidad(tablas: dict) -> list[Violacion]:
    out = []
    for tabla, claves in CLAVES_UNICAS.items():
        filas = _filas(tablas, tabla)
        for columnas in claves:
            vistos: dict = {}
            for i, f in enumerate(filas):
                valor = tuple(f.get(c) for c in columnas)
                if any(v is None for v in valor):
                    continue
                if valor in vistos:
                    out.append(Violacion(
                        tabla, i, "unique",
                        f"{'+'.join(columnas)} = {valor if len(valor) > 1 else valor[0]!r} "
                        f"repetido (ya está en la fila {vistos[valor]})",
                    ))
                else:
                    vistos[valor] = i
    return out


def _largos(tablas: dict) -> list[Violacion]:
    out = []
    for tabla, columnas in COLUMNAS_VARCHAR.items():
        for i, f in enumerate(_filas(tablas, tabla)):
            for c in columnas:
                valor = f.get(c)
                if isinstance(valor, str) and len(valor) > MAX_VARCHAR:
                    out.append(Violacion(
                        tabla, i, "largo_maximo",
                        f"{c} = {valor!r} tiene {len(valor)} caracteres (máximo {MAX_VARCHAR})",
                    ))
    return out


def _formatos_personal(tablas: dict) -> list[Violacion]:
    out = []
    for i, p in enumerate(_filas(tablas, "personal")):
        matricula, telefono, email = p.get("matricula"), p.get("telefono"), p.get("email")
        if not isinstance(matricula, str) or not REGEX_MATRICULA.fullmatch(matricula):
            out.append(Violacion("personal", i, "regex_matricula",
                                 f"matricula = {matricula!r} no cumple [0-9]{{2}}[1-5][0-9]+"))
        if (
            not isinstance(telefono, str)
            or not REGEX_TELEFONO.fullmatch(telefono)
            or len(re.sub(r"[^0-9]", "", telefono)) < MIN_DIGITOS_TELEFONO
        ):
            out.append(Violacion("personal", i, "regex_telefono",
                                 f"telefono = {telefono!r} inválido (formato o menos de "
                                 f"{MIN_DIGITOS_TELEFONO} dígitos)"))
        if not isinstance(email, str) or not REGEX_EMAIL.fullmatch(email):
            out.append(Violacion("personal", i, "regex_email", f"email = {email!r} inválido"))
    return out


def _enums(tablas: dict) -> list[Violacion]:
    out = []
    for i, p in enumerate(_filas(tablas, "personal")):
        if p.get("rol") not in ROLES:
            out.append(Violacion("personal", i, "enum_invalido",
                                 f"rol = {p.get('rol')!r} (debe ser uno de {ROLES})"))
    for i, h in enumerate(_filas(tablas, "horario_atencion")):
        if h.get("dia") not in DIAS:
            out.append(Violacion("horario_atencion", i, "enum_invalido",
                                 f"dia = {h.get('dia')!r} (debe ser uno de {DIAS})"))
    return out


def _claves_foraneas(tablas: dict) -> list[Violacion]:
    out = []
    for tabla, columna, ref_tabla, ref_columna in CLAVES_FORANEAS:
        validos = _valores_referenciables(tablas, ref_tabla, ref_columna)
        for i, f in enumerate(_filas(tablas, tabla)):
            valor = f.get(columna)
            if valor is None:  # FK nullable
                continue
            if valor not in validos:
                out.append(Violacion(
                    tabla, i, "fk",
                    f"{columna} = {valor!r} no existe en {ref_tabla}.{ref_columna}",
                ))
    return out


def _fechas(tablas: dict, hoy: date) -> list[Violacion]:
    out = []
    for tabla, columna in FECHAS_ANTERIORES_A_HOY:
        for i, f in enumerate(_filas(tablas, tabla)):
            valor = f.get(columna)
            if valor is None:  # p. ej. fecha_egreso de una internación actual
                continue
            instante = _instante(valor)
            if instante is None:
                out.append(Violacion(tabla, i, "fecha_invalida",
                                     f"{columna} = {valor!r} no es una fecha válida"))
            elif instante.date() >= hoy:
                out.append(Violacion(
                    tabla, i, "fecha_anterior_a_hoy",
                    f"{columna} = {valor!r} debe ser estrictamente anterior a hoy ({hoy})",
                ))
    return out


def _edad_personal(tablas: dict, hoy: date) -> list[Violacion]:
    out = []
    for i, p in enumerate(_filas(tablas, "personal")):
        nacimiento = _instante(p.get("nacimiento"))
        if nacimiento is not None and _edad(nacimiento.date(), hoy) < EDAD_MINIMA_PERSONAL:
            out.append(Violacion(
                "personal", i, "personal_mayor_de_18",
                f"nacimiento = {p.get('nacimiento')!r}: tiene menos de {EDAD_MINIMA_PERSONAL} años",
            ))
    return out


def _servicios(tablas: dict) -> list[Violacion]:
    out = []
    roles = {p.get("matricula"): p.get("rol") for p in _filas(tablas, "personal")}
    tipos = {t.get("nombre"): t for t in _filas(tablas, "tipo_servicio")}
    miembros: dict = {}  # id_servicio -> [matriculas]
    for ps in _filas(tablas, "personal_servicio"):
        miembros.setdefault(ps.get("id_servicio"), []).append(ps.get("matricula_personal"))

    vistos: dict = {}
    for i, s in enumerate(_filas(tablas, "servicio")):
        # (centro, tipo) único
        par = (s.get("id_centro_salud"), s.get("nombre_tipo_servicio"))
        if par in vistos:
            out.append(Violacion(
                "servicio", i, "centro_tipo_unico",
                f"el centro {par[0]!r} ya tiene un servicio de tipo {par[1]!r} "
                f"(fila {vistos[par]})",
            ))
        else:
            vistos[par] = i

        # encargado: debe ser médico (y, por realismo, trabajar en el servicio)
        encargado = s.get("matricula_encargado")
        if encargado is not None and encargado in roles:
            if roles[encargado] != "Médico":
                out.append(Violacion(
                    "servicio", i, "encargado_medico",
                    f"matricula_encargado = {encargado!r} es {roles[encargado]!r}, no Médico",
                ))
            elif encargado not in miembros.get(s.get("id"), []):
                out.append(Violacion(
                    "servicio", i, "encargado_en_servicio",
                    f"matricula_encargado = {encargado!r} no trabaja en el servicio {s.get('id')!r}",
                ))

        # cupos por rol
        tipo = tipos.get(s.get("nombre_tipo_servicio"))
        if tipo is None:
            continue  # la FK ya lo reporta
        cantidad = {"Médico": 0, "Enfermero": 0}
        for m in miembros.get(s.get("id"), []):
            if roles.get(m) in cantidad:
                cantidad[roles[m]] += 1
        if cantidad["Médico"] > tipo.get("num_medicos", cantidad["Médico"]):
            out.append(Violacion(
                "servicio", i, "cupo_medicos",
                f"servicio {s.get('id')!r} ({tipo['nombre']}) tiene {cantidad['Médico']} "
                f"médicos y el tope es {tipo['num_medicos']}",
            ))
        if cantidad["Enfermero"] > tipo.get("num_enfermeros", cantidad["Enfermero"]):
            out.append(Violacion(
                "servicio", i, "cupo_enfermeros",
                f"servicio {s.get('id')!r} ({tipo['nombre']}) tiene {cantidad['Enfermero']} "
                f"enfermeros y el tope es {tipo['num_enfermeros']}",
            ))
    return out


def _personal_servicio(tablas: dict) -> list[Violacion]:
    out = []
    tipo_de_servicio = {s.get("id"): s.get("nombre_tipo_servicio") for s in _filas(tablas, "servicio")}
    requeridas: dict = {}
    for er in _filas(tablas, "especialidad_requerida"):
        requeridas.setdefault(er.get("nombre_tipo_servicio"), set()).add(er.get("nombre_especialidad"))
    especialidades: dict = {}
    for ee in _filas(tablas, "especializado_en"):
        especialidades.setdefault(ee.get("matricula_personal"), set()).add(ee.get("nombre_especialidad"))

    vistos: dict = {}
    for i, ps in enumerate(_filas(tablas, "personal_servicio")):
        matricula = ps.get("matricula_personal")

        # una persona, un solo servicio
        if matricula in vistos:
            out.append(Violacion(
                "personal_servicio", i, "un_servicio_por_persona",
                f"matricula_personal = {matricula!r} ya está en el servicio "
                f"{vistos[matricula][1]!r} (fila {vistos[matricula][0]})",
            ))
        else:
            vistos[matricula] = (i, ps.get("id_servicio"))

        # especialidades requeridas por el tipo del servicio (médicos y enfermeros)
        tipo = tipo_de_servicio.get(ps.get("id_servicio"))
        faltantes = sorted(requeridas.get(tipo, set()) - especialidades.get(matricula, set()))
        if faltantes:
            out.append(Violacion(
                "personal_servicio", i, "especialidades_requeridas",
                f"{matricula!r} en el servicio {ps.get('id_servicio')!r} ({tipo}) "
                f"no tiene: {', '.join(faltantes)}",
            ))
    return out


def _registros_hc(tablas: dict) -> list[Violacion]:
    out = []
    roles = {p.get("matricula"): p.get("rol") for p in _filas(tablas, "personal")}
    trabaja_en = {(ps.get("id_servicio"), ps.get("matricula_personal"))
                  for ps in _filas(tablas, "personal_servicio")}
    horarios = {h.get("id"): h for h in _filas(tablas, "horario_atencion")}
    servicios = {s.get("id") for s in _filas(tablas, "servicio")}
    horarios_de_servicio: dict = {}
    for a in _filas(tablas, "atencion_servicio"):
        h = horarios.get(a.get("id_horario"))
        if h is not None:
            horarios_de_servicio.setdefault(a.get("id_servicio"), []).append(h)

    for i, r in enumerate(_filas(tablas, "registro_hc")):
        id_servicio, matricula = r.get("id_servicio"), r.get("matricula_personal")

        # lo atiende un médico que trabaja en ese servicio
        if matricula in roles and id_servicio in servicios:
            if roles[matricula] != "Médico":
                out.append(Violacion(
                    "registro_hc", i, "registro_medico_del_servicio",
                    f"matricula_personal = {matricula!r} es {roles[matricula]!r}, no Médico",
                ))
            elif (id_servicio, matricula) not in trabaja_en:
                out.append(Violacion(
                    "registro_hc", i, "registro_medico_del_servicio",
                    f"el médico {matricula!r} no trabaja en el servicio {id_servicio!r}",
                ))

        # la visita cae dentro del horario del servicio
        instante = _instante(r.get("dia_visita"))
        if instante is None or id_servicio not in servicios:
            continue  # fecha_invalida / fk ya lo reportan
        dia = DIAS[instante.weekday()]
        del_dia = [h for h in horarios_de_servicio.get(id_servicio, []) if h.get("dia") == dia]
        if not del_dia:
            out.append(Violacion(
                "registro_hc", i, "visita_en_horario",
                f"dia_visita = {r.get('dia_visita')!r} es {dia} y el servicio {id_servicio!r} "
                f"no atiende ese día",
            ))
        elif instante.time() != time.min:  # solo se mira la hora si la visita la trae
            def _cabe(h):
                apertura, cierre = _hora(h.get("apertura")), _hora(h.get("cierre"))
                return apertura is not None and cierre is not None \
                    and apertura <= instante.time() <= cierre
            if not any(_cabe(h) for h in del_dia):
                franjas = ", ".join(f"{h.get('apertura')}-{h.get('cierre')}" for h in del_dia)
                out.append(Violacion(
                    "registro_hc", i, "visita_en_horario",
                    f"dia_visita = {r.get('dia_visita')!r}: {instante.time()} está fuera de "
                    f"la franja del {dia} ({franjas})",
                ))
    return out


def _internaciones(tablas: dict) -> list[Violacion]:
    out = []
    registros = _ids_registro_hc(tablas)
    tipo_por_servicio = {s.get("id"): s.get("nombre_tipo_servicio") for s in _filas(tablas, "servicio")}
    interna_por_tipo = {t.get("nombre"): t["interna"] for t in _filas(tablas, "tipo_servicio")
                        if "interna" in t}  # campo solo del generador: puede no estar

    usados: dict = {}
    por_paciente: dict = {}  # dni -> [(ingreso, egreso, fila)]
    for i, n in enumerate(_filas(tablas, "internacion")):
        id_registro = n.get("id_registro_hc")
        registro = registros.get(id_registro)
        ingreso, egreso = _instante(n.get("fecha_ingreso")), _instante(n.get("fecha_egreso"))

        # ingreso = visita
        if registro is not None:
            visita = _instante(registro.get("dia_visita"))
            if ingreso is not None and visita is not None and ingreso != visita:
                out.append(Violacion(
                    "internacion", i, "ingreso_igual_a_visita",
                    f"fecha_ingreso = {n.get('fecha_ingreso')!r} y la visita del registro "
                    f"{id_registro!r} es {registro.get('dia_visita')!r}",
                ))

            # solo se interna en servicios que internan
            tipo = tipo_por_servicio.get(registro.get("id_servicio"))
            if tipo in interna_por_tipo and not interna_por_tipo[tipo]:
                out.append(Violacion(
                    "internacion", i, "internacion_servicio_interna",
                    f"el registro {id_registro!r} es del servicio {registro.get('id_servicio')!r} "
                    f"({tipo}), que no admite internación",
                ))

        # egreso >= ingreso
        if ingreso is not None and egreso is not None and egreso < ingreso:
            out.append(Violacion(
                "internacion", i, "egreso_posterior_a_ingreso",
                f"fecha_egreso = {n.get('fecha_egreso')!r} es anterior a fecha_ingreso = "
                f"{n.get('fecha_ingreso')!r}",
            ))

        # un registro se interna una sola vez
        if id_registro is not None:
            if id_registro in usados:
                out.append(Violacion(
                    "internacion", i, "internacion_registro_unico",
                    f"el registro {id_registro!r} ya tiene una internación (fila {usados[id_registro]})",
                ))
            else:
                usados[id_registro] = i

        if registro is not None and ingreso is not None:
            por_paciente.setdefault(registro.get("dni_paciente"), []).append(
                (ingreso, egreso or datetime.max, i)
            )

    # sin solapamientos por paciente (una activa cuenta como abierta hasta siempre)
    for dni, intervalos in por_paciente.items():
        intervalos.sort(key=lambda x: (x[0], x[2]))
        fin_anterior, fila_anterior = None, None
        for ingreso, egreso, fila in intervalos:
            if fin_anterior is not None and ingreso <= fin_anterior:
                out.append(Violacion(
                    "internacion", fila, "internacion_sin_solapamiento",
                    f"el paciente {dni!r} ingresa el {ingreso.date()} mientras sigue internado "
                    f"por la internación de la fila {fila_anterior}",
                ))
            if fin_anterior is None or egreso > fin_anterior:
                fin_anterior, fila_anterior = egreso, fila
    return out


# --- Punto de entrada ------------------------------------------------------------

REGLAS = (
    "unique", "largo_maximo", "regex_matricula", "regex_telefono", "regex_email",
    "enum_invalido", "fk", "fecha_invalida", "fecha_anterior_a_hoy", "personal_mayor_de_18",
    "centro_tipo_unico", "encargado_medico", "encargado_en_servicio", "cupo_medicos",
    "cupo_enfermeros", "un_servicio_por_persona", "especialidades_requeridas",
    "registro_medico_del_servicio", "visita_en_horario", "ingreso_igual_a_visita",
    "egreso_posterior_a_ingreso", "internacion_registro_unico",
    "internacion_servicio_interna", "internacion_sin_solapamiento",
)


def validar(tablas: dict[str, list[dict]], hoy: date | None = None) -> list[Violacion]:
    """Valida las tablas ya generadas y devuelve la lista de violaciones.

    Args:
        tablas: dict {nombre de tabla: lista de filas (dicts)}. Una tabla que
            falta se toma como vacía.
        hoy: fecha contra la que se comparan las fechas "anteriores a hoy"
            (por defecto date.today(), igual que CURRENT_DATE en los triggers).

    Es independiente: solo mira las tablas recibidas, no usa pools ni
    generadores, y no modifica nada. Una lista vacía significa que cumple
    todas las reglas.
    """
    if hoy is None:
        hoy = date.today()

    violaciones: list[Violacion] = []
    violaciones += _unicidad(tablas)
    violaciones += _largos(tablas)
    violaciones += _formatos_personal(tablas)
    violaciones += _enums(tablas)
    violaciones += _claves_foraneas(tablas)
    violaciones += _fechas(tablas, hoy)
    violaciones += _edad_personal(tablas, hoy)
    violaciones += _servicios(tablas)
    violaciones += _personal_servicio(tablas)
    violaciones += _registros_hc(tablas)
    violaciones += _internaciones(tablas)
    return violaciones
