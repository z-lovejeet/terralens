"""TerraLens is an offline machine-learning project: nothing in the application may call an outside service."""
from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient

from terralens import app as app_module

BACKEND = Path(__file__).resolve().parents[1] / "backend" / "terralens"
NETWORK = re.compile(r"^\s*(?:import|from)\s+(?:urllib|requests|httpx|aiohttp|http\.client|socket|websockets|google|openai|anthropic)\b", re.M)
# The one-off dataset downloader belongs to the offline study pipeline (scripts/prepare_study.py), not the web app.
OFFLINE_PIPELINE = {"study.py"}


def test_application_code_makes_no_network_calls():
    offenders = [
        path.name for path in BACKEND.rglob("*.py")
        if path.name not in OFFLINE_PIPELINE and NETWORK.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_no_api_keys_are_read_by_the_application():
    for path in BACKEND.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "API_KEY" not in text and ".env.local" not in text, path.name


@pytest.mark.parametrize("route", ["/api/area-check", "/api/crisis-scan", "/api/plant-check", "/api/change-check", "/api/similar"])
def test_removed_routes_are_gone(tmp_path, monkeypatch, route):
    monkeypatch.setattr(app_module, "RUNTIME", tmp_path / "runtime")
    with TestClient(app_module.app) as client:
        assert client.post(route, files={"file": ("x.jpg", b"x", "image/jpeg")}).status_code in (404, 405)
