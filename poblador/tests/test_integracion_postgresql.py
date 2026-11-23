"""Prueba end-to-end opcional. Requiere PostgreSQL y TEST_ADMIN_DSN.

TEST_ADMIN_DSN debe apuntar a una base administrativa (normalmente postgres)
con permisos CREATEDB. La prueba crea y elimina una base temporal aislada.
"""
import os
import uuid
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

BASE = Path(__file__).resolve().parents[2]
POBLADOR = BASE / "poblador"
SCRIPTS = BASE / "scripts"


@pytest.mark.integration
def test_carga_completa_postgresql():
    admin_dsn = os.getenv("TEST_ADMIN_DSN")
    if not admin_dsn:
        pytest.skip("Defina TEST_ADMIN_DSN para ejecutar la prueba de integración.")

    nombre_db = "bd_tpfi_test_" + uuid.uuid4().hex[:10]
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{nombre_db}"')
    try:
        # Reutiliza host/usuario/clave del DSN administrativo y cambia dbname.
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        params = conninfo_to_dict(admin_dsn)
        params["dbname"] = nombre_db
        dsn = make_conninfo(**params)

        with psycopg.connect(dsn) as conn:
            conn.execute((SCRIPTS / "01_init.sql").read_text(encoding="utf-8"), prepare=False)
            triggers = SCRIPTS / "02_triggers.sql"
            if not triggers.exists():
                pytest.fail("Falta scripts/02_triggers.sql (dependencia del issue #18).")
            conn.execute(triggers.read_text(encoding="utf-8"), prepare=False)
            seed_path = os.getenv("SEED_SQL", str(POBLADOR / "02_seed.sql"))
            sql_seed = Path(seed_path)
            if not sql_seed.is_file():
                pytest.fail(
                    f"No existe {sql_seed}. Genere primero 02_seed.sql "
                    "con main.py o indique SEED_SQL."
                )
            conn.execute(sql_seed.read_text(encoding="utf-8"), prepare=False)
            from config import TOTALES
            for tabla, esperado in TOTALES.items():
                real = conn.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
                assert real == esperado, (
                    f"{tabla}: se esperaban {esperado} filas y hay {real}"
                )
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (nombre_db,),
            )
            admin.execute(f'DROP DATABASE IF EXISTS "{nombre_db}"')
