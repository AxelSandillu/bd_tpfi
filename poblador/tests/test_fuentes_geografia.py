"""Pruebas de cache, modo offline y compatibilidad con Georef v2."""

import json
from unittest.mock import Mock

import pytest
import requests

from fuentes import geografia


def test_offline_usa_fallback_sin_realizar_peticiones(monkeypatch, tmp_path):
    monkeypatch.setenv("POBLADOR_OFFLINE", "1")
    monkeypatch.setattr(geografia, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(
        geografia,
        "FALLBACK_PATH",
        geografia.Path(__file__).resolve().parents[1] / "data" / "geografia_fallback.json",
    )

    def no_http(*args, **kwargs):
        pytest.fail("El modo offline no debe realizar peticiones HTTP")

    monkeypatch.setattr(geografia.requests, "get", no_http)
    monkeypatch.setattr(geografia.requests, "post", no_http)

    departamentos = geografia.obtener_departamentos()
    assert departamentos
    departamento_id = departamentos[0]["id"]
    assert geografia.obtener_localidades(departamento_id)
    assert geografia.obtener_calles(departamento_id)
    assert geografia.obtener_barrios()


def test_error_404_no_se_reintenta(monkeypatch):
    respuesta = requests.Response()
    respuesta.status_code = 404
    error = requests.HTTPError("404 Not Found", response=respuesta)
    get = Mock(side_effect=error)
    monkeypatch.setattr(geografia.requests, "get", get)
    monkeypatch.setattr(geografia, "MAX_REINTENTOS", 8)

    with pytest.raises(geografia.GeografiaError, match="404 Not Found"):
        geografia._fetch_json("https://ejemplo.invalid/recurso")

    assert get.call_count == 1


def test_departamentos_interpreta_respuesta_georef_v2(monkeypatch, tmp_path):
    monkeypatch.delenv("POBLADOR_OFFLINE", raising=False)
    monkeypatch.setattr(geografia, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(geografia, "_cargar_cache", lambda nombre: None)
    guardados = {}
    monkeypatch.setattr(geografia, "_guardar_cache", lambda nombre, datos: guardados.update({nombre: datos}))
    monkeypatch.setattr(
        geografia,
        "_fetch_json",
        lambda url, params=None: {
            "departamentos": [
                {"id": "3001", "nombre": "Paraná"},
                {"id": "3002", "nombre": "Concordia"},
                {"id": "3003", "nombre": "Gualeguaychú"},
                {"id": "3004", "nombre": "Uruguay"},
                {"id": "3005", "nombre": "Colón"},
            ]
        },
    )

    resultado = geografia.obtener_departamentos()

    assert len(resultado) == 5
    assert resultado[0] == {"id": "3001", "nombre": "Paraná"}
    assert guardados["departamentos"] == resultado


def test_relacion_georef_puede_venir_anidada_o_aplanada():
    assert geografia._id_relacionado({"departamento": {"id": "3005"}}, "departamento") == "3005"
    assert geografia._id_relacionado({"departamento_id": "3005"}, "departamento") == "3005"
