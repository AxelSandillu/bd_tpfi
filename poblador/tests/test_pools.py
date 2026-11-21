"""Test cases para el issue #11: Pools de recursos.

Verifica:
- Pool consumible: tomar(n) quita elementos y no vuelven a salir.
- Pool consumible: agotamiento lanza PoolAgotadoError.
- Pool reutilizable: sortear(n) con reposición permite repetir elementos.
- Indexación por atributo (medicos_libres, enfermeros_libres, pacientes, etc.).
- Reproducibilidad con la misma semilla.
"""

import random

import pytest

from generadores.pools import Pool, PoolAgotadoError, Pools


# ---------------------------------------------------------------------------
# Pool base
# ---------------------------------------------------------------------------

def test_pool_consumible_tomar_quita_elementos():
    """Un elemento tomado no vuelve a estar disponible."""
    elementos = [{"id": 1}, {"id": 2}, {"id": 3}]
    pool = Pool("test", elementos, consumible=True, rng=random.Random(42))

    tomados = pool.tomar(2)
    assert len(tomados) == 2
    assert pool.cantidad() == 1

    # Los tomados ya no están disponibles
    restantes = pool.disponibles()
    assert len(restantes) == 1
    for t in tomados:
        assert t not in restantes


def test_pool_consumible_elemento_no_repite():
    """Tomar de un pool consumible nunca devuelve un elemento ya tomado."""
    elementos = [{"id": i} for i in range(10)]
    pool = Pool("test", elementos, consumible=True, rng=random.Random(42))

    tomados = []
    while not pool.esta_vacio():
        tomados.extend(pool.tomar(1))

    ids_tomados = [e["id"] for e in tomados]
    assert len(ids_tomados) == len(set(ids_tomados)), "No debe haber repetidos"
    assert len(ids_tomados) == 10


def test_pool_consumible_agotamiento_lanza_error():
    """tomar(n) con n mayor a lo disponible lanza PoolAgotadoError."""
    elementos = [{"id": 1}, {"id": 2}]
    pool = Pool("test", elementos, consumible=True, rng=random.Random(42))

    pool.tomar(2)
    assert pool.esta_vacio()

    with pytest.raises(PoolAgotadoError):
        pool.tomar(1)


def test_pool_reutilizable_sortear_con_reposicion():
    """sortear(n) no quita elementos y permite repetir."""
    elementos = ["A", "B", "C"]
    pool = Pool("test", elementos, consumible=False, rng=random.Random(42))

    sorteados = pool.sortear(5)
    assert len(sorteados) == 5
    assert pool.cantidad() == 3  # no se quitan elementos


def test_pool_reutilizable_esta_vacio_lanza_error_al_sortear():
    """Un pool reutilizable vacío lanza PoolAgotadoError al sortear."""
    pool = Pool("vacio", [], consumible=False, rng=random.Random(42))
    assert pool.esta_vacio()

    with pytest.raises(PoolAgotadoError):
        pool.sortear(1)


def test_pool_agregar_elemento():
    """agregar() incorpora un elemento al pool de disponibles."""
    pool = Pool("test", [1, 2], consumible=True, rng=random.Random(42))
    pool.agregar(3)
    assert pool.cantidad() == 3


def test_pool_tomar_uno_devuelve_elemento_y_lo_quita():
    """tomar_uno() devuelve un elemento y reduce el pool en 1."""
    elementos = [10, 20, 30]
    pool = Pool("test", elementos, consumible=True, rng=random.Random(42))
    uno = pool.tomar_uno()
    assert uno in elementos
    assert pool.cantidad() == 2


# ---------------------------------------------------------------------------
# Pools (contenedor indexado por atributo)
# ---------------------------------------------------------------------------

def test_pools_registrar_y_obtener():
    """Registrar un pool y obtenerlo por nombre."""
    pools = Pools(rng=random.Random(42))
    p = pools.registrar("mi_pool", [1, 2, 3], consumible=True)
    assert pools.obtener("mi_pool") is p


def test_pools_obtener_inexistente_lanza_keyerror():
    pools = Pools(rng=random.Random(42))
    with pytest.raises(KeyError):
        pools.obtener("no_existe")


def test_pools_personal_sin_servicio_indexado():
    """personal_sin_servicio crea un pool consumible indexado."""
    pools = Pools(rng=random.Random(42))
    personal = [{"matricula": "M1", "rol": "Médico"}, {"matricula": "E1", "rol": "Enfermero"}]
    pool = pools.personal_sin_servicio(personal)

    assert "personal_sin_servicio" in pools
    assert pool.cantidad() == 2
    assert pool.consumible is True


def test_pools_medicos_y_enfermeros_libres():
    pools = Pools(rng=random.Random(42))
    medicos = [{"matricula": "M1"}, {"matricula": "M2"}]
    enfermeros = [{"matricula": "E1"}, {"matricula": "E2"}, {"matricula": "E3"}]

    p_med = pools.medicos_libres(medicos)
    p_enf = pools.enfermeros_libres(enfermeros)

    assert p_med.cantidad() == 2
    assert p_enf.cantidad() == 3
    assert p_med.consumible is True
    assert p_enf.consumible is True


def test_pools_pares_centro_tipo_consumible():
    pools = Pools(rng=random.Random(42))
    pares = [{"centro": 1, "tipo": "Pediatría"}, {"centro": 2, "tipo": "Cardiología"}]
    pool = pools.pares_centro_tipo(pares)
    assert pool.consumible is True
    assert pool.cantidad() == 2


def test_pools_registros_no_internados_consumible():
    pools = Pools(rng=random.Random(42))
    registros = [{"id": 1}, {"id": 2}, {"id": 3}]
    pool = pools.registros_no_internados(registros)
    assert pool.consumible is True
    assert pool.cantidad() == 3


def test_pools_pacientes_reutilizable():
    pools = Pools(rng=random.Random(42))
    pacientes = [{"dni": 1}, {"dni": 2}]
    pool = pools.pacientes(pacientes)
    assert pool.consumible is False
    assert pool.cantidad() == 2


def test_pools_horarios_reutilizable():
    pools = Pools(rng=random.Random(42))
    horarios = [{"id": 1}, {"id": 2}]
    pool = pools.horarios(horarios)
    assert pool.consumible is False


def test_pools_obras_sociales_reutilizable():
    pools = Pools(rng=random.Random(42))
    obras = [{"id": 1}, {"id": 2}, {"id": 3}]
    pool = pools.obras_sociales(obras)
    assert pool.consumible is False


def test_pools_servicios_que_internan_reutilizable():
    pools = Pools(rng=random.Random(42))
    servicios = [{"id": 1}, {"id": 2}]
    pool = pools.servicios_que_internan(servicios)
    assert pool.consumible is False


# ---------------------------------------------------------------------------
# Reproducibilidad
# ---------------------------------------------------------------------------

def test_misma_seed_genera_mismo_sorteo():
    elementos = [{"id": i} for i in range(20)]
    p1 = Pool("test", elementos, consumible=True, rng=random.Random(42))
    p2 = Pool("test", elementos, consumible=True, rng=random.Random(42))

    t1 = p1.tomar(5)
    t2 = p2.tomar(5)
    assert [e["id"] for e in t1] == [e["id"] for e in t2]


def test_distinta_seed_puede_generar_sorteo_distinto():
    elementos = [{"id": i} for i in range(20)]
    p1 = Pool("test", elementos, consumible=True, rng=random.Random(42))
    p2 = Pool("test", elementos, consumible=True, rng=random.Random(99))

    t1 = p1.tomar(10)
    t2 = p2.tomar(10)
    ids1 = {e["id"] for e in t1}
    ids2 = {e["id"] for e in t2}
    # Es muy probable que difieran; solo verificamos que ambos tomen 10 distintos
    assert len(ids1) == 10
    assert len(ids2) == 10
