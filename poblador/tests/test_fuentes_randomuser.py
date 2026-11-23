"""Pruebas de cache y política de reintentos de RandomUser."""

import json
from unittest.mock import Mock

import pytest
import requests

from fuentes import randomuser


def test_reutiliza_cache_sin_consultar_api_ni_verificar_nacionalidades(monkeypatch, tmp_path):
    monkeypatch.delenv("POBLADOR_OFFLINE", raising=False)
    monkeypatch.setattr(randomuser, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(randomuser, "PESOS_NAT", {"es": 1.0})
    monkeypatch.setattr(randomuser, "SEED", 42)
    archivo = tmp_path / "randomuser_es_42.json"
    archivo.write_text(
        json.dumps({"results": [{
            "name": {"first": "Ana", "last": "Pérez"},
            "dob": {"date": "1990-01-01T00:00:00.000Z"},
            "nat": "ES",
        }]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        randomuser, "_fetch_one",
        lambda *args, **kwargs: pytest.fail("No debería consultar la API si hay cache"),
    )
    monkeypatch.setattr(
        randomuser, "verificar_nats_disponibles",
        lambda: pytest.fail("No debería hacer llamadas de verificación adicionales"),
    )

    personas = randomuser.obtener_personas(1)

    assert personas == [{
        "nombre": "Ana",
        "apellido": "Pérez",
        "nacimiento": "1990-01-01T00:00:00.000Z",
        "nat": "ES",
    }]


def test_offline_informa_cache_ausente(monkeypatch, tmp_path):
    monkeypatch.setenv("POBLADOR_OFFLINE", "1")
    monkeypatch.setattr(randomuser, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(randomuser, "PESOS_NAT", {"es": 1.0})
    monkeypatch.setattr(randomuser, "SEED", 42)

    with pytest.raises(randomuser.RandomUserError, match="randomuser_es_42.json"):
        randomuser.obtener_personas(1)


def test_error_404_de_randomuser_no_se_reintenta(monkeypatch):
    respuesta = requests.Response()
    respuesta.status_code = 404
    error = requests.HTTPError("404 Not Found", response=respuesta)
    get = Mock(side_effect=error)
    monkeypatch.setattr(randomuser.requests, "get", get)
    monkeypatch.setattr(randomuser, "MAX_REINTENTOS", 9)

    with pytest.raises(randomuser.RandomUserError, match="404 Not Found"):
        randomuser._fetch_one("es", 1, 42)

    assert get.call_count == 1
