# Planificación: generador de `02_seed.sql`

> **Propósito de este documento:** servir de contexto completo para quien desarrolle los issues (persona o asistente de IA). Contiene el objetivo, el esquema, las reglas de negocio, las decisiones ya tomadas, la arquitectura y los criterios de aceptación. Si algo no está aquí, no está decidido: preguntar antes de inventar.

---

## 1. Objetivo

Construir un programa (Python 3.11+) que genere **un único archivo `02_seed.sql`** para poblar una base **PostgreSQL** con datos de prueba verosímiles del sistema de salud de la provincia de **Entre Ríos, Argentina**.

Requisitos principales:

1. Las **cantidades por tabla** salen del Excel `Plan_de_poblado.xlsx`. Son objetivos: puede haber pequeñas desviaciones por reparación.
2. Los datos de **personas** (nombre, apellido, fecha de nacimiento) vienen de la API **randomuser.me**.
3. Los datos **geográficos** (departamentos, ciudades, barrios, calles) pertenecen a **Entre Ríos** y salen de APIs públicas.
4. El resto de los datos se genera de forma aleatoria pero **coherente**: el SQL debe ejecutarse sin errores con los triggers activos y los datos deben tener sentido (un médico atiende en su servicio, las visitas caen en horario de atención, etc.).
5. Todo es **reproducible** (semilla) y las APIs se consultan **una vez** y se guardan en cache.
6. Todo lo ajustable vive en un archivo **`config.py`**.
7. Al final el programa **verifica, repara agregando filas si hace falta, e informa** el total por tabla contra el Excel. Los desvíos se pasan **a mano** al Excel después de la ejecución final.

---

## 2. Esquema de la base (`01_init.sql`)

### Tipos

- `Dia` ENUM: Lunes, Martes, Miércoles, Jueves, Viernes, Sábado, Domingo.
- `Rol` ENUM: `'Médico'`, `'Enfermero'`.
- `Matricula` DOMAIN `VARCHAR` con `CHECK (VALUE ~ '^[0-9]{2}[1-5][0-9]+$')`.

### Tablas (resumen; PK en **negrita**)

| Tabla                    | Columnas                                                                                                                                | Notas                                                                                            |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `departamento`           | **id** (identity), nombre VARCHAR(30) UNIQUE                                                                                            |                                                                                                  |
| `ciudad`                 | **id** (identity), id_departamento FK, nombre VARCHAR(30) UNIQUE                                                                        |                                                                                                  |
| `barrio`                 | **id** (identity), id_ciudad FK, nombre VARCHAR(30) UNIQUE                                                                              | UNIQUE **global**, no por ciudad                                                                 |
| `obra_social`            | **id** (identity), razon_social VARCHAR(30), estado BOOLEAN                                                                             |                                                                                                  |
| `paciente`               | **dni** INT, id_obra_social FK NULL, nombre, apellido, nacimiento TIMESTAMP, num_asociado INT UNIQUE NULL                               | **Cambio de esquema acordado:** `dni` pasa de `GENERATED ALWAYS AS IDENTITY` a `INT PRIMARY KEY` |
| `centro_de_salud`        | **id** (identity), id_barrio FK, nombre VARCHAR(30) UNIQUE, direccion VARCHAR(30), inaguracion TIMESTAMP, calle VARCHAR(30), altura INT | `inaguracion` está mal escrito pero se respeta. `direccion` = "calle altura"                     |
| `tipo_servicio`          | **nombre** VARCHAR(30), num_enfermeros INT, num_medicos INT                                                                             | `num_*` son **topes máximos** (cupos)                                                            |
| `personal`               | **matricula** Matricula UNIQUE, nombre, apellido, telefono VARCHAR(30) UNIQUE, email VARCHAR(30) UNIQUE, nacimiento TIMESTAMP, rol Rol  |                                                                                                  |
| `servicio`               | **id** (identity), id_centro_salud FK, nombre_tipo_servicio FK, matricula_encargado FK NULL                                             |                                                                                                  |
| `personal_servicio`      | **(id_servicio, matricula_personal)**, `matricula_personal` UNIQUE                                                                      | Cada persona está en **un solo servicio**                                                        |
| `registro_hc`            | **id** (identity), id_servicio FK, dni_paciente FK, matricula_personal FK, dia_visita TIMESTAMP, diagnostico TEXT, tratamiento TEXT     |                                                                                                  |
| `internacion`            | **id** (identity), id_registro_hc FK, fecha_ingreso TIMESTAMP, fecha_egreso TIMESTAMP NULL                                              |                                                                                                  |
| `especialidad`           | **nombre** VARCHAR(30)                                                                                                                  |                                                                                                  |
| `especializado_en`       | **(matricula_personal, nombre_especialidad)**                                                                                           |                                                                                                  |
| `especialidad_requerida` | **(nombre_tipo_servicio, nombre_especialidad)**                                                                                         |                                                                                                  |
| `horario_atencion`       | **id** (identity), apertura TIME, cierre TIME, dia Dia                                                                                  | **Una fila = un solo día** con su franja                                                         |
| `atencion_centro`        | **(id_centro_salud, id_horario)**                                                                                                       |                                                                                                  |
| `atencion_servicio`      | **(id_servicio, id_horario)**                                                                                                           |                                                                                                  |

**Tablas con identity** (ids insertados explícitamente con `OVERRIDING SYSTEM VALUE` y `setval` al final): `departamento`, `ciudad`, `barrio`, `obra_social`, `centro_de_salud`, `servicio`, `registro_hc`, `internacion`, `horario_atencion`. `paciente` ya **no** es identity.

---

## 3. Cantidades objetivo (Excel `Plan_de_poblado.xlsx`)

| Orden | Tabla                  | Depende de                               | Cantidad                           |
| ----- | ---------------------- | ---------------------------------------- | ---------------------------------- |
| 1     | departamento           | –                                        | 15                                 |
| 2     | ciudad                 | departamento                             | 15                                 |
| 3     | barrio                 | ciudad                                   | 20                                 |
| 4     | obra_social            | –                                        | 50                                 |
| 5     | paciente               | obra_social                              | 400                                |
| 6     | centro_de_salud        | barrio                                   | 20                                 |
| 7     | personal               | –                                        | 300 (100 médicos + 200 enfermeros) |
| 8     | especialidad           | –                                        | 15                                 |
| 9     | especializado_en       | personal, especialidad                   | 320                                |
| 10    | tipo_servicio          | –                                        | 20                                 |
| 11    | especialidad_requerida | tipo_servicio, especialidad              | 25                                 |
| 12    | servicio               | centro_de_salud, tipo_servicio, personal | 70                                 |
| 13    | registro_hc            | servicio, paciente, personal             | 750                                |
| 14    | internacion            | registro_hc                              | 150 (40 actuales + 110 pasadas)    |
| 15    | personal_servicio      | servicio, personal                       | 150                                |
| 16    | horario_atencion       | –                                        | 70                                 |
| 17    | atencion_centro        | centro_de_salud, horario_atencion        | 20                                 |
| 18    | atencion_servicio      | servicio, horario_atencion               | 160                                |

Total aproximado: 3.088 registros.

---

## 4. Reglas de negocio (triggers y restricciones)

El programa **asume el `02_triggers.sql` corregido** (la versión original usaba columnas que no existen, p. ej. `id_personal`, `tipo_personal`, `id_centro`, y varias funciones no tenían `RETURN NEW`). La carga se hace **con los triggers activos**: la base es el validador final.

| Regla                                                                                                                                      | Origen  | Cómo la respeta el generador                                                                                     |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ------- | ---------------------------------------------------------------------------------------------------------------- |
| `centro_de_salud.inaguracion` estrictamente anterior a hoy                                                                                 | trigger | Los triggers usan `CURRENT_DATE` de la base, no `FECHA_REFERENCIA`. Generar con la fecha real y un día de margen |
| `paciente.nacimiento` y `personal.nacimiento` estrictamente anteriores a hoy                                                               | trigger | Idem                                                                                                             |
| `personal.email` cumple `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`                                                                 | trigger | Además, máximo 30 caracteres (columna)                                                                           |
| `personal.telefono` cumple `^\+?[0-9\s\-\(\)]{7,15}$` y ≥ 7 dígitos                                                                        | trigger | Formato compacto `+549` + área + número (13 dígitos tras el `+`)                                                 |
| `personal` mayor de 18 años                                                                                                                | trigger | Edad del personal en `EDAD_PERSONAL` (22–65)                                                                     |
| `servicio.matricula_encargado` debe ser un **médico**                                                                                      | trigger | Se elige entre los médicos del propio servicio (la columna admite NULL, pero se completa siempre)                |
| `(id_centro_salud, nombre_tipo_servicio)` **único** en `servicio`                                                                          | trigger | Pool de pares sin repetir                                                                                        |
| `registro_hc.matricula_personal` debe ser un **médico que trabaje en ese servicio**                                                        | trigger | El médico se sortea entre los médicos de `personal_servicio` del servicio                                        |
| `internacion.fecha_ingreso` **igual** a `registro_hc.dia_visita`                                                                           | trigger | Se copia el valor                                                                                                |
| `internacion.fecha_egreso` ≥ `fecha_ingreso` (o NULL)                                                                                      | trigger | Se genera estrictamente posterior                                                                                |
| `personal_servicio`: no superar `num_medicos` / `num_enfermeros` del tipo                                                                  | trigger | Cupos por rol                                                                                                    |
| `personal_servicio`: **toda** persona (médico **o enfermero**) debe tener **todas** las especialidades requeridas por el tipo del servicio | trigger | Se **otorgan** especialidades faltantes a la persona. Las especialidades **no** se separan por rol               |
| `personal_servicio`: sin superposición horaria entre servicios                                                                             | trigger | Inerte mientras `matricula_personal` sea UNIQUE (1 servicio por persona)                                         |

**Reglas de realismo propias (no las impone la base):** las visitas caen dentro del horario del servicio; una visita es posterior a la inauguración del centro y al nacimiento del paciente; un paciente no tiene internaciones superpuestas; solo se interna en servicios con `interna: true`.

---

## 5. Decisiones cerradas

1. **Horarios:** cada centro tiene **un solo** horario general (`atencion_centro` = 20 filas; como cada fila de `horario_atencion` es un día, es un día con su franja). Los servicios tienen horarios propios (`atencion_servicio` = 160) y **no** se exige que queden dentro del horario del centro.
2. **DNI:** `paciente.dni` pasa a `INT PRIMARY KEY`. No hay otros cambios de esquema necesarios (`registro_hc.dni_paciente` ya es `INT`). Opcional: endurecer el dominio a `^[0-9]{2}[1-5][0-9]{9}$`.
3. **Matrícula (SISA, 12 dígitos):** `[país 2 dígitos][tipo documento 1 dígito][documento 9 dígitos, ceros a la izquierda]`. País argentino = `54`. Tipos: `1`=DNI, `2`=LC, `3`=LE, `4`=CI, `5`=PAS. Por defecto todo el personal usa país `54` y tipo `1`. Ejemplo: DNI 30.123.456 → `541030123456`. Fuente: documentación de REFEPS/SISA.
4. **Departamentos:** de los 17 de Entre Ríos se usan 15, **descartando los dos menos poblados** (lista de exclusión configurable).
5. **Nacionalidades de randomuser:** ES+MX 85%, BR 10%, DE/FR/CH 5%.
6. **Barrios y obras sociales:** intentar la fuente real (Overpass / padrón SSS) y caer a una **lista curada** si falla.
7. **Códigos de área:** Paraná 343, Concordia 345, Gualeguaychú 3446, Concepción del Uruguay 3442. Para otras ciudades, completar y verificar contra la tabla de ENACOM.
8. **Tipos de servicio y especialidades:** viven en `data/tipos_servicio.json`.
9. **Reparación automática:** al final se valida y, si algo no cuadra, se **agregan** filas hasta cuadrar; se informa el total por tabla.
10. **Todo lo ajustable** está en `config.py`.

---

## 6. Fuentes de datos

| Dato                                                 | Fuente                                                                                         | Detalle                                                                                                                   |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Nombre, apellido, nacimiento                         | randomuser.me                                                                                  |                                                                                                                           |
| Departamentos, localidades, calles                   | **Georef AR** (`apis.datos.gob.ar/georef`)                                                     | Provincia Entre Ríos = código INDEC **30**. Endpoints: `departamentos`, `localidades`, `calles`                           |
| Barrios                                              | **Overpass API** (OpenStreetMap)                                                               | `place=suburb \ neighbourhood \ quarter` dentro de Entre Ríos. Georef no tiene barrios. Fallback: lista curada en `data/` |
| Obras sociales                                       | Padrón de Agentes del Seguro de Salud (Superintendencia de Servicios de Salud, datos abiertos) | Fallback: lista curada de ~50. Truncar a 30 caracteres                                                                    |
| Diagnósticos y tratamientos                          | `tipos_servicio.json` (campo `casos`, con código CIE-10)                                       | Catálogo propio en español                                                                                                |
| Teléfonos, DNI, matrículas, emails, horarios, fechas | Generados localmente                                                                           | §8                                                                                                                        |

Toda llamada de red se hace en `fuentes/`, pasa por cache en `cache/` y debe poder funcionar **offline** con cache o fallback.

### 6.1 randomuser.me (detalles)

- Admite hasta 5.000 resultados por request, lista de nacionalidades con `nat=es,mx,br` y filtro de campos con `inc=name,dob,nat`.
- **No tiene nacionalidad AR** (ni UY, CL, PY, BO) hasta donde se sabe. **Verificar con una llamada de prueba** qué códigos ofrece y avisar si alguno de `PESOS_NAT` no existe.
- Sustitutos de AR: **ES y MX** (nombres y apellidos hispanos). **BR** es el único país limítrofe disponible. **DE/FR/CH** representan descendientes de inmigrantes (comunes en Entre Ríos).
- Se hace **una llamada por nacionalidad** con la cantidad calculada desde `PESOS_NAT` (más un margen `MARGEN_API` para reparaciones).
- De la API **solo** se usan nombre, apellido y fecha de nacimiento. Se descartan teléfono, dirección, email, etc. (tienen formato de otro país).
- La API devuelve adultos (~21 a 99 años). Los **pacientes pediátricos** toman nombre y apellido de la API pero la **fecha de nacimiento se genera localmente**.
- Se guarda en `cache/randomuser_*.json`; la semilla de la API se deriva de `SEED`.
- Cuidar caracteres especiales (acentos, `ñ`, apóstrofes) y escapar comillas en el SQL.

---

## 7. `data/tipos_servicio.json` (formato final)

```json
{
  "especialidades": ["Pediatría", "Cardiología", "..."],
  "tipos_servicio": [
    {
      "nombre": "Pediatría",
      "num_medicos": 2,
      "num_enfermeros": 2,
      "especialidades_requeridas": ["Pediatría"],
      "interna": true,
      "peso": 1.5,
      "casos": [
        {
          "cie10": "J21.9",
          "diagnostico": "Bronquiolitis aguda",
          "tratamiento": "Hidratación, oxigenoterapia si SatO2 < 92%"
        }
      ]
    }
  ]
}
```

- `num_medicos` y `num_enfermeros` son **topes**, van a `tipo_servicio`.
- `especialidades_requeridas` va a `especialidad_requerida`.
- `interna` (¿admite internación?) y `peso` (cuántos servicios de ese tipo se crean, proporcionalmente) son **solo del generador**.
- `casos` alimentan `registro_hc.diagnostico` / `tratamiento`.

**Validaciones al arrancar** (abortar con mensaje claro, indicando tipo y campo):

- Exactamente 20 tipos y 15 especialidades.
- 25 filas de `especialidades_requeridas` en total.
- Toda especialidad requerida existe en `especialidades`.
- Nombres de 30 caracteres o menos.
- Al menos 1 médico por tipo (`num_medicos ≥ 1`).
- Al menos 1 caso por tipo.
- Al menos un tipo con `interna: true`.
- Capacidad total suficiente: considerando los 70 servicios, la suma de cupos debe permitir ≥ 150 asignaciones.

---

## 8. Arquitectura y algoritmo

### 8.1 Estructura del proyecto

```
poblado/
├── config.py
├── main.py
├── pools.py
├── validar.py
├── reparar.py
├── emitir_sql.py
├── data/
│   ├── tipos_servicio.json
│   └── (listas curadas de fallback)
├── cache/                 # ignorado por git
├── fuentes/               # randomuser, georef, overpass (con cache)
├── generadores/           # un módulo por grupo de tablas
└── tests/
```

### 8.2 Principio clave: orden de generación ≠ orden de emisión

Se genera todo **en memoria** con las dependencias resueltas y recién después se emite el SQL en el orden requerido por las FK y los triggers (§8.9). Ejemplo: las especialidades de cada persona dependen de los servicios, que dependen del personal.

### 8.3 Pools

- **Consumibles** (cada elemento se usa una vez): personal sin servicio, pares (centro, tipo) sin usar, registros todavía no internados.
- **Reutilizables** (se sortea con reposición): pacientes, horarios, obras sociales.
- Indexados por atributo (`medicos_libres`, `enfermeros_libres`, `servicios_que_internan`, etc.).
- `tomar(n)` sortea y quita; si no alcanza lanza una excepción que dispara el reintento con otra semilla derivada (hasta `MAX_REINTENTOS`).

### 8.4 Identificadores

- **Registro global de documentos usados:** pacientes y personal nunca comparten documento.
- **DNI** correlacionado con el año de nacimiento (aproximado, con ruido): ≈14–18 M para 1960, ≈35 M para 1990, ≈48–50 M para 2010; extrapolar para nacidos más recientes.
- **Matrícula:** según §5.3; validar contra el dominio.
- **Teléfono:** `+549` + área + número, 10 dígitos después de `549`; UNIQUE; área según la ciudad de residencia/centro (`AREAS_TELEFONICAS`).
- **Email:** `nombre.apellido` normalizado (minúsculas, sin tildes ni `ñ`), dominio reservado `example.com`, **máximo 30 caracteres**, UNIQUE (sufijo numérico si hace falta; truncar la parte local, no el dominio).
- **`num_asociado`:** entero UNIQUE dentro del rango de `INT`, NULL si no hay obra social.

### 8.5 Geografía y catálogos

- `departamento`: 15 de 17 (menos poblados excluidos).
- `ciudad`: una por departamento (la cabecera). `nombre` UNIQUE.
- `barrio`: 20, repartidos en proporción a la población de cada ciudad. `nombre` UNIQUE **global**: calificar los nombres genéricos (p. ej. "Centro") con la ciudad, respetando los 30 caracteres.
- `centro_de_salud`: 20, **uno por barrio**. `calle` y `altura` vienen de Georef, `direccion` = "calle altura" (≤ 30). Inauguración dentro de `INAUGURACION_ENTRE`.
- `obra_social`: 50, ~10% con `estado=false`.
- `paciente`: 400. ~25% sin obra social (`id_obra_social` y `num_asociado` NULL). Casi ninguno con obra social inactiva. ~15% pediátricos.
- `personal`: 100 médicos + 200 enfermeros.

### 8.6 Estructura clínica (corazón del algoritmo)

1. `tipo_servicio`, `especialidad`, `especialidad_requerida` ← JSON.
2. `horario_atencion`: 70 = 7 días × 10 franjas (`FRANJAS_HORARIAS`), todas distintas.
3. `atencion_centro`: un horario por centro (20).
4. `servicio` (70): pares (centro, tipo) únicos; todo centro con al menos un servicio; tipos distribuidos según `peso`.
5. `atencion_servicio` (160): ~2,3 horarios por servicio, tomados del pool reutilizable.
6. `personal_servicio` (150):
   - Armar los servicios de la **especialidad más escasa a la más abundante**.
   - Primero **un médico por servicio**, que será el encargado.
   - Luego completar hasta los cupos de cada tipo, hasta sumar 150, sin pasar de 100 médicos ni 200 enfermeros asignados.
   - **Invertir el sentido del filtro:** se elige a la persona y se le **otorgan las especialidades requeridas que le falten** (prefiriendo a quien ya las tiene). Así el pool no se queda sin candidatos.
7. `especializado_en` (objetivo 320): cada persona tiene al menos una especialidad (300 base) y 20 médicos tienen una segunda. Las especialidades otorgadas por los servicios cuentan dentro de esos totales; el resto se completa al azar. Si las requeridas obligan a superar 320, se informa el desvío (§10).

### 8.7 Registros de historia clínica (750)

Para cada registro: **servicio → horario del servicio → médico del servicio → paciente**.

- La fecha cae en un día de la semana que coincide con el `dia` del horario y la hora dentro de `apertura`–`cierre`.
- Debe ser posterior a la inauguración del centro y al nacimiento del paciente, dentro de los últimos `VENTANA_VISITAS_ANIOS` años y anterior a hoy.
- `diagnostico` y `tratamiento` salen de un `caso` del tipo de servicio.
- **Primero** se generan los registros de las 40 internaciones actuales, con fechas recientes (`INTERNACION_ACTUAL_DIAS`).

### 8.8 Internaciones (150)

- 150 registros **distintos**, de servicios con `interna: true`.
- `fecha_ingreso` **igual** a `dia_visita`.
- **40 actuales:** `fecha_egreso` NULL, ingreso reciente.
- **110 pasadas:** egreso estrictamente posterior al ingreso (duración en `DURACION_INTERNACION_DIAS`) y anterior a ahora.
- Un paciente no tiene internaciones superpuestas (a lo sumo una activa).

### 8.9 Orden de emisión del SQL

1. departamento → ciudad → barrio
2. obra_social → paciente
3. centro_de_salud
4. personal → especialidad → especializado_en
5. tipo_servicio → especialidad_requerida
6. horario_atencion → atencion_centro
7. servicio
8. atencion_servicio
9. personal_servicio _(sus triggers necesitan los pasos 4, 5 y 8)_
10. registro_hc _(su trigger necesita el paso 9)_
11. internacion

Formato del archivo:

- Un solo `02_seed.sql` dentro de `BEGIN` / `COMMIT`.
- Ids explícitos con `OVERRIDING SYSTEM VALUE` y, al final, `setval` de cada secuencia (vía `pg_get_serial_sequence`) en las 9 tablas con identity.
- Escape correcto de comillas, NULL, booleanos, timestamps (`'YYYY-MM-DD HH:MM:SS'`), enums y dominio.
- INSERT por lotes.

---

## 9. `config.py` (constantes ajustables)

```python
# --- Generales ---
SEED = 42
FECHA_REFERENCIA = None            # None = hoy (los triggers usan CURRENT_DATE)
MAX_REINTENTOS = 20
MARGEN_API = 1.3                   # pedir más personas de las necesarias

# --- Tamaños de tabla (objetivos del Excel) ---
TOTALES = {"departamento": 15, "ciudad": 15, "barrio": 20, "obra_social": 50,
           "paciente": 400, "centro_de_salud": 20, "personal": 300,
           "especialidad": 15, "especializado_en": 320, "tipo_servicio": 20,
           "especialidad_requerida": 25, "servicio": 70, "registro_hc": 750,
           "internacion": 150, "personal_servicio": 150,
           "horario_atencion": 70, "atencion_centro": 20, "atencion_servicio": 160}
MEDICOS, ENFERMEROS = 100, 200
INTERNACIONES_ACTUALES, INTERNACIONES_PASADAS = 40, 110
DEPARTAMENTOS_EXCLUIDOS = []       # vacío = excluir los 2 menos poblados

# --- Porcentajes ---
PCT_PACIENTES_SIN_OBRA_SOCIAL = 0.25
PCT_OBRAS_SOCIALES_INACTIVAS = 0.10
PCT_PACIENTES_PEDIATRICOS = 0.15
PCT_MEDICOS_DOS_ESPECIALIDADES = 0.20

# --- Nacionalidades de randomuser ---
PESOS_NAT = {"es": .50, "mx": .35, "br": .10, "de": .02, "fr": .02, "ch": .01}

# --- Fechas y rangos ---
EDAD_PERSONAL = (22, 65)
VENTANA_VISITAS_ANIOS = 2
INAUGURACION_ENTRE = (1950, 2020)
DURACION_INTERNACION_DIAS = (1, 30)
INTERNACION_ACTUAL_DIAS = (1, 20)
FRANJAS_HORARIAS = [("07:00", "13:00"), ("08:00", "16:00")]  # completar hasta 10

# --- Identificadores ---
SISA_PAIS = 54
SISA_TIPO_DOC_PESOS = {1: 1.0}     # 1=DNI, 2=LC, 3=LE, 4=CI, 5=PAS
EMAIL_DOMINIO = "example.com"
AREAS_TELEFONICAS = {"Paraná": "343", "Concordia": "345",
                     "Gualeguaychú": "3446", "Concepción del Uruguay": "3442"}

# --- Archivos y fuentes ---
RUTA_TIPOS_SERVICIO = "data/tipos_servicio.json"
RUTA_SALIDA = "02_seed.sql"
```

Los valores son punto de partida; ningún módulo debe tener constantes propias.

---

## 10. Validación, reparación y reporte

1. **Validador independiente** (`validar.py`): recorre las tablas ya armadas **sin usar los pools** y devuelve violaciones (tabla, fila, regla). Verifica: UNIQUE, largos máximos, regex (matrícula, teléfono, email), FK resueltas, cupos y especialidades por servicio, un servicio por persona, (centro, tipo) único, encargado médico, registros atendidos por un médico del servicio, ingreso = visita, egreso ≥ ingreso, fechas anteriores a hoy, visitas dentro del horario del servicio, internaciones sin solapamiento.
2. **Reparador** (`reparar.py`): bucle validar → reparar.
   - **Solo agrega** filas o reasigna desde pools; **nunca borra ni modifica** lo existente.
   - Prefiere arreglos que no cambian conteos antes de los que agregan filas (por ejemplo, otorgar una especialidad faltante agrega una fila a `especializado_en`).
   - Tope de iteraciones; si se agota, aborta con el detalle de lo no resuelto.
3. **Reporte final** por tabla, para actualizar el Excel a mano:

```
Tabla                 Excel   Generado   Dif.
departamento             15         15      0
especializado_en        320        327     +7
...
```

4. **No se emite el SQL** si quedan violaciones.

---

## 11. Plan de trabajo (issues)

| #   | Issue                                                  | Depende de |
| --- | ------------------------------------------------------ | ---------- |
| 1   | Estructura del proyecto y dependencias                 | –          |
| 2   | `config.py`                                            | 1          |
| 3   | Carga y validación de `tipos_servicio.json`            | 1, 2       |
| 4   | Fuente randomuser.me                                   | 2          |
| 5   | Fuentes Georef AR y Overpass                           | 2          |
| 6   | Catálogos curados                                      | 3          |
| 7   | Registro de documentos e identificadores               | 2          |
| 8   | Geografía y centros de salud                           | 5, 6       |
| 9   | Obras sociales y pacientes                             | 4, 6, 7    |
| 10  | Personal y especialidades                              | 3, 4, 7    |
| 11  | Pools de recursos                                      | 8, 9, 10   |
| 12  | Estructura clínica (servicios, horarios, asignaciones) | 3, 11      |
| 13  | Registros de historia clínica                          | 12         |
| 14  | Internaciones                                          | 13         |
| 15  | Validador independiente                                | 14         |
| 16  | Reparación automática y reporte                        | 15         |
| 17  | Emisión del SQL                                        | 16         |
| 18  | CLI, pruebas de integración y documentación            | 17         |

**Hitos:** M1 (issues 1–6) base y fuentes · M2 (7–14) generadores · M3 (15–18) consistencia y emisión.

---

## 12. Pruebas

- **Unitarias:** identificadores (unicidad, regex de matrícula/teléfono/email, largos), pools (consumo y agotamiento), validaciones del JSON, una prueba por regla del validador con datos adulterados.
- **Integración:** crear una base PostgreSQL con `01_init.sql` (con el cambio de `dni`) y el `02_triggers.sql` corregido, ejecutar `02_seed.sql` y comprobar los conteos del reporte.
- **Reproducibilidad:** dos corridas con la misma semilla y la misma cache generan archivos idénticos.

---

## 13. Riesgos conocidos (se resuelven programando)

1. **Ajuste de capacidad:** que 70 servicios, el tope de 100 médicos y las 150 asignaciones cuadren puede requerir reintentos o ajustar pesos del JSON.
2. **Distribución de especialidades:** evitar que un servicio quede sin candidatos (mitigado con el sentido invertido de la asignación y el orden por escasez).
3. **Reparto de fechas** de los 750 registros dentro de los horarios de cada servicio, con las 40 internaciones actuales recientes y sin solapamientos.
4. **randomuser.me:** los códigos de `nat` disponibles no están verificados; comprobar con una llamada de prueba.
5. **Códigos de área** de ciudades distintas de las cuatro listadas: verificar con ENACOM.
6. **Desfase de fecha:** los triggers validan contra `CURRENT_DATE` de la base; no usar fechas de hoy ni futuras.

---

## 14. Reglas transversales de implementación

- Reproducible con `SEED`; sin llamadas de red fuera de `fuentes/`; siempre con cache.
- Respetar largos máximos (`VARCHAR(30)`) y escapar comillas en el SQL.
- Nada de números mágicos: todo en `config.py`.
- Se asume el `02_triggers.sql` corregido y activo durante la carga.
- Nombres de variables y tablas coherentes con el esquema (snake_case en español).
- No borrar ni modificar datos ya generados durante la reparación; solo agregar.
