# Poblador de datos — PostgreSQL

Genera `02_seed.sql` con datos de prueba para el esquema de salud de Entre Ríos. La generación se realiza en memoria, valida las reglas del modelo y emite un único script SQL transaccional. La semilla y la cache permiten repetir la generación.

## Requisitos

- Python 3.11 o superior.
- PostgreSQL (para ejecutar la carga y la prueba de integración).
- Los scripts del esquema: `../scripts/01_init.sql` y `../scripts/02_triggers.sql`.
- Para la generación online, conexión a Internet.

## Instalación

Desde el directorio `poblador/`:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

python -m pip install -r requirements.txt
```

## Uso de la CLI

Ejecutar desde `poblador/`, así las rutas `data/`, `cache/` y `config.py` se resuelven correctamente.

```bash
# Primera ejecución: obtiene las fuentes y genera 02_seed.sql
python main.py

# Semilla explícita y destino personalizado
python main.py --seed 42 --salida salida/02_seed.sql

# Modo offline: no realiza peticiones HTTP
python main.py --offline --seed 42

# Archivo de configuración alternativo
python main.py --config config_local.py --seed 123 --salida salida/seed.sql

# Ayuda
python main.py --help
```

### Argumentos

| Argumento | Descripción |
|---|---|
| `--seed N` | Semilla del generador. Si se omite, usa `SEED` de la configuración. |
| `--offline` | Desactiva las consultas a APIs. Usa la cache disponible y el fallback geográfico incluido. La cache de personas de randomuser.me debe existir para esa semilla. |
| `--salida RUTA` | Ruta del archivo SQL. Por defecto `RUTA_SALIDA` de `config.py`. |
| `--config RUTA` | Archivo Python de configuración. Por defecto `config.py`. |

La primera ejecución online debe completarse antes de poder ejecutar offline con la misma semilla, para generar las cachés de RandomUser. La geografía dispone de un fallback local, por lo que no requiere caché previa. Las personas se cachean por nacionalidad y semilla. La API de randomuser recibe una semilla derivada de forma estable, por lo que el resultado no depende del hash aleatorio de cada proceso.

## Configuración

Todos los parámetros de generación se ajustan en `config.py`: cantidades objetivo (`TOTALES`), distribución de roles (`MEDICOS`, `ENFERMEROS`), porcentajes de pacientes, nacionalidades (`PESOS_NAT`), rangos de fechas, franjas horarias, reintentos, URLs y rutas de archivos. Georef utiliza la API v2 (`https://apis.datos.gob.ar/georef/api/v2.0`).

Para probar cambios sin modificar la configuración del proyecto, copie `config.py` a otro archivo y páselo mediante `--config`. Mantenga coherencia entre `TOTALES`, las capacidades definidas en `data/tipos_servicio.json` y las restricciones del esquema. Los nombres de tablas, columnas, regex y reglas que replican restricciones SQL no son parámetros configurables.

## Ejecución contra PostgreSQL

En una base vacía, ejecutar en este orden:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f ../scripts/01_init.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f ../scripts/02_triggers.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f 02_seed.sql
```

`02_seed.sql` abre y confirma una transacción. Debe ejecutarse con los triggers activos: no los deshabilite para cargar los datos.

## Cómo leer el reporte

Al terminar, la CLI informa la ruta de salida, la semilla y la cantidad de filas emitidas por tabla. Compare cada cantidad con `TOTALES` en `config.py` (los valores de referencia provienen de `docs/Plan_de_poblado.xlsx`). El SQL también incluye comentarios por tabla con sus cantidades y sincroniza las secuencias `IDENTITY` al final.

Si la validación en memoria detecta reglas incumplidas, el programa intenta repararlas agregando registros. Si no logra resolverlas, termina con error y no presenta el archivo como una generación válida. Las cantidades finales pueden variar cuando la reparación agrega filas; documente cualquier desvío respecto del Excel.

## Pruebas

Pruebas unitarias:

```bash
python -m pytest -q
```

Prueba de integración real contra PostgreSQL:

1. Genere previamente `02_seed.sql` (normalmente con `--offline` luego de poblar la cache).
2. Configure `TEST_ADMIN_DSN` con un DSN de PostgreSQL que conecte a una base administrativa y tenga permiso `CREATEDB`.
3. Ejecute:

```bash
# PowerShell:
$env:TEST_ADMIN_DSN = "host=localhost port=5432 dbname=postgres user=postgres password=..."
python -m pytest -m integration -q

# Linux/macOS:
export TEST_ADMIN_DSN="host=localhost port=5432 dbname=postgres user=postgres password=..."
python -m pytest -m integration -q
```

El test crea una base temporal aislada, ejecuta `01_init.sql`, `02_triggers.sql` y `02_seed.sql`, comprueba los conteos de todas las tablas contra `TOTALES` y elimina la base temporal incluso si falla. `SEED_SQL` permite indicar otra ruta al SQL generado. Sin `TEST_ADMIN_DSN`, el test queda omitido; no se considera una integración ejecutada.

## Reproducibilidad

Con la misma versión del código, el mismo archivo de configuración, la misma semilla y los mismos archivos de cache, la salida SQL es determinista. Para comparar dos corridas, genere a dos rutas diferentes:

```bash
python main.py --offline --seed 42 --salida /tmp/seed_a.sql
python main.py --offline --seed 42 --salida /tmp/seed_b.sql
```

Luego compare los archivos (`fc /b` en Windows o `cmp` en Linux/macOS). No cambie la cache entre ambas corridas.
