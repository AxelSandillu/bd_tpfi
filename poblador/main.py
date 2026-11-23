"""CLI para generar el archivo SQL de poblado de PostgreSQL.

Ejemplos:
    python main.py --seed 42 --salida salida/02_seed.sql
    python main.py --offline --seed 42
    python main.py --config config.py --seed 123
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import random
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un 02_seed.sql reproducible para PostgreSQL."
    )
    parser.add_argument("--seed", type=int, default=None, help="Semilla aleatoria.")
    parser.add_argument("--offline", action="store_true",
                        help="No consulta APIs; exige cache local o usa los fallback incluidos.")
    parser.add_argument("--salida", default=None, help="Ruta del SQL generado.")
    parser.add_argument("--config", default="config.py",
                        help="Ruta al archivo de configuración Python.")
    return parser


def _cargar_config(ruta: str):
    path = Path(ruta).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo de configuración: {path}")
    spec = importlib.util.spec_from_file_location("config", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar la configuración: {path}")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["config"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def generar(args: argparse.Namespace) -> Path:
    if args.offline:
        os.environ["POBLADOR_OFFLINE"] = "1"
    else:
        os.environ.pop("POBLADOR_OFFLINE", None)

    config = _cargar_config(args.config)
    seed = config.SEED if args.seed is None else args.seed
    # Los módulos leen la configuración al importarse. Se establece la semilla
    # antes de importarlos y se pasa un RNG único a los generadores.
    config.SEED = seed
    rng = random.Random(seed)

    from validar import cargar_tipos_servicio, validar
    from generadores.geografia import generar_geografia
    from generadores.obras_sociales import generar_obras_sociales
    from generadores.pacientes import generar_pacientes
    from generadores.personal import generar_personal
    from generadores.estructura_clinica import generar_estructura_clinica
    from generadores.registro_hc import generar_registro_hc_completo
    from generadores.internaciones import generar_internaciones_completo
    from reparar import reparar
    from emitir_sql import emitir

    tipos_json = cargar_tipos_servicio(config.RUTA_TIPOS_SERVICIO)
    geografia = generar_geografia(seed=seed)
    obras = generar_obras_sociales(rng)
    pacientes = generar_pacientes(obras, rng)
    personal = generar_personal(rng)
    estructura = generar_estructura_clinica(
        personal=personal, centros=geografia["centro_de_salud"],
        datos_json=tipos_json, seed=seed
    )
    registros = generar_registro_hc_completo(
        datos_estructura=estructura, datos_pacientes=pacientes,
        datos_geografia=geografia, datos_json=tipos_json, seed=seed
    )
    internaciones = generar_internaciones_completo(
        datos_registro_hc=registros, datos_estructura=estructura, seed=seed
    )

    datos: dict[str, list[dict]] = {}
    datos.update(geografia)
    datos.update(estructura)
    datos.update(registros)
    datos.update(internaciones)
    datos["obra_social"] = obras
    datos["paciente"] = pacientes
    datos["personal"] = personal

    violaciones = validar(datos)
    if violaciones:
        resultado = reparar(datos, seed=seed)
        datos = resultado.tablas
        violaciones = validar(datos)
    if violaciones:
        detalle = "\n".join(str(v) for v in violaciones[:20])
        raise RuntimeError(
            f"El conjunto generado conserva {len(violaciones)} violaciones:\n{detalle}"
        )

    destino = emitir(datos, args.salida or config.RUTA_SALIDA)
    print(f"SQL generado: {destino}")
    print(f"Semilla: {seed}")
    print("Registros por tabla:")
    for tabla in datos:
        print(f"  {tabla}: {len(datos[tabla])}")
    return destino


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        generar(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
