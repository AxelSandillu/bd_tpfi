"""Constantes ajustables del generador de 02_seed.sql.

Todo lo ajustable del programa vive en este archivo. Ningún otro módulo
debe definir constantes propias; si un valor necesita cambiar, se modifica
aquí y el resto del programa lo lee desde config.

Valores base de la sección 9 de PLANIFICAION.md.
"""

# --- Generales ---
SEED = 42
FECHA_REFERENCIA = None  # None = hoy (los triggers usan CURRENT_DATE)
MAX_REINTENTOS = 20
MARGEN_API = 1.3  # pedir más personas de las necesarias

# --- Tamaños de tabla (objetivos del Excel Plan_de_poblado.xlsx) ---
TOTALES = {
    "departamento": 15,
    "ciudad": 15,
    "barrio": 20,
    "obra_social": 50,
    "paciente": 400,
    "centro_de_salud": 20,
    "personal": 300,
    "especialidad": 15,
    "especializado_en": 320,
    "tipo_servicio": 20,
    "especialidad_requerida": 25,
    "servicio": 70,
    "registro_hc": 750,
    "internacion": 150,
    "personal_servicio": 150,
    "horario_atencion": 70,
    "atencion_centro": 20,
    "atencion_servicio": 160,
}
MEDICOS = 100
ENFERMEROS = 200
INTERNACIONES_ACTUALES = 40
INTERNACIONES_PASADAS = 110
DEPARTAMENTOS_EXCLUIDOS = []  # vacío = excluir los 2 menos poblados

# --- Porcentajes ---
PCT_PACIENTES_SIN_OBRA_SOCIAL = 0.25
PCT_OBRAS_SOCIALES_INACTIVAS = 0.10
PCT_PACIENTES_PEDIATRICOS = 0.15
PCT_MEDICOS_DOS_ESPECIALIDADES = 0.20

# --- Nacionalidades de randomuser.me ---
PESOS_NAT = {"es": 0.50, "mx": 0.35, "br": 0.10, "de": 0.02, "fr": 0.02, "ch": 0.01}

# --- Fechas y rangos ---
EDAD_PERSONAL = (22, 65)
VENTANA_VISITAS_ANIOS = 2
INAUGURACION_ENTRE = (1950, 2020)
DURACION_INTERNACION_DIAS = (1, 30)
INTERNACION_ACTUAL_DIAS = (1, 20)
FRANJAS_HORARIAS = [
    ("07:00", "13:00"),
    ("08:00", "16:00"),
    ("13:00", "19:00"),
    ("16:00", "22:00"),
    ("08:00", "12:00"),
    ("14:00", "20:00"),
    ("09:00", "15:00"),
    ("15:00", "21:00"),
    ("10:00", "18:00"),
    ("18:00", "23:00"),
]  # 10 franjas distintas (7 días × 10 franjas = 70 horarios)

# --- Identificadores ---
SISA_PAIS = 54
# 1=DNI, 2=LC, 3=LE, 4=CI, 5=PAS. Por defecto solo se usa DNI (peso 1.0).
SISA_TIPO_DOC_PESOS = {1: 1.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}
EMAIL_DOMINIO = "example.com"
AREAS_TELEFONICAS = {
    "Paraná": "343",
    "Concordia": "345",
    "Gualeguaychú": "3446",
    "Concepción del Uruguay": "3442",
}

# --- URLs de APIs públicas ---
URL_RANDOMUSER = "https://randomuser.me/api/"
URL_GEOREF = "https://apis.datos.gob.ar/georef"
# Overpass API (OpenStreetMap) para barrios de Entre Ríos.
URL_OVERPASS = "https://overpass-api.de/api/interpreter"

# --- Archivos y fuentes ---
RUTA_TIPOS_SERVICIO = "data/tipos_servicio.json"
RUTA_SALIDA = "02_seed.sql"
