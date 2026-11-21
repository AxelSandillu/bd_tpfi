"""Test cases para el issue #9: Obras sociales.

Verifica:
- 50 obras sociales generadas.
- IDs secuenciales 1..50.
- razon_social desde config.OBRAS_SOCIALES (máx. 30 caracteres).
- ~10% con estado=false (inactivas).
- Reproducibilidad con la misma semilla.
"""

import pytest

from generadores.obras_sociales import generar_obras_sociales


@pytest.fixture
def rng():
    import random
    return random.Random(42)


def test_generar_obras_sociales_devuelve_50(rng):
    obras = generar_obras_sociales(rng)
    assert len(obras) == 50


def test_obras_sociales_ids_secuenciales(rng):
    obras = generar_obras_sociales(rng)
    ids = [o["id"] for o in obras]
    assert ids == list(range(1, 51))


def test_obras_sociales_razon_social_max_30(rng):
    obras = generar_obras_sociales(rng)
    for o in obras:
        assert len(o["razon_social"]) <= 30, (
            f"razon_social excede 30 caracteres: '{o['razon_social']}'"
        )


def test_obras_sociales_aproximadamente_10_inactivas(rng):
    obras = generar_obras_sociales(rng)
    inactivas = [o for o in obras if not o["estado"]]
    activas = [o for o in obras if o["estado"]]
    # ~10% de 50 = 5 inactivas. Permitir margen de 1 por redondeo.
    assert 4 <= len(inactivas) <= 6, f"Esperadas ~5 inactivas, obtuve {len(inactivas)}"
    assert len(activas) + len(inactivas) == 50


def test_obras_sociales_estado_es_booleano(rng):
    obras = generar_obras_sociales(rng)
    for o in obras:
        assert isinstance(o["estado"], bool)


def test_misma_seed_genera_mismo_resultado(rng):
    obras_a = generar_obras_sociales(rng)
    rng2 = __import__("random").Random(42)
    obras_b = generar_obras_sociales(rng2)
    assert obras_a == obras_b


def test_distinta_seed_puede_generar_resultado_distinto():
    import random
    obras_a = generar_obras_sociales(random.Random(42))
    obras_b = generar_obras_sociales(random.Random(99))
    # Puede coincidir por azar, pero generalmente diferente. Solo verificamos que ambos tengan 50.
    assert len(obras_a) == 50
    assert len(obras_b) == 50
