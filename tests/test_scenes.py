"""Check my area and Crisis Radar: tile scanning on the frozen PCA + K-Means model."""

import io
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from terralens import app as app_module
from terralens import vision
from terralens.features import extract_features
from terralens.inference import _project, load_model
from terralens.landscan import area_check, change_check, crop_to_grid, cut_tiles, group_profiles, plan_grid
from terralens.settings import UPLOAD_LIMITS

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
CODES = {"T": "trees", "F": "farmland", "W": "water", "B": "built"}


@lru_cache(maxsize=1)
def tile_pools() -> dict[str, list[str]]:
    """Cohort patches nearest the purest group centre for each land type (by frozen cluster, not label)."""
    model = load_model(ARTIFACTS)
    profiles = group_profiles(ARTIFACTS)
    with np.load(ARTIFACTS / "compact_features.npz", allow_pickle=False) as bundle:
        raw, ids = bundle["X"], bundle["ids"]
    _, space = _project(model, raw)
    clusters = model["kmeans"].predict(space)
    distances = np.linalg.norm(space - model["kmeans"].cluster_centers_[clusters], axis=1)
    pools = {}
    for land_type in CODES.values():
        purest = max((c for c, p in profiles.items() if p["land_type"] == land_type), key=lambda c: profiles[c]["reliability"])
        members = np.flatnonzero(clusters == purest)
        pools[land_type] = [str(ids[i]) for i in members[np.argsort(distances[members], kind="stable")[:36]]]
    return pools


def mosaic(layout: list[str]) -> Image.Image:
    """A test scene assembled from real EuroSAT thumbnails, one 64 px tile per letter."""
    pools, used = tile_pools(), {}
    scene = Image.new("RGB", (64 * len(layout[0]), 64 * len(layout)))
    for row, line in enumerate(layout):
        for col, code in enumerate(line):
            land_type = CODES[code]
            index = used.get(land_type, 0)
            used[land_type] = index + 1
            with Image.open(ARTIFACTS / "thumbnails" / f"{pools[land_type][index % 36]}.jpg") as patch:
                scene.paste(patch.convert("RGB"), (col * 64, row * 64))
    return scene


TOWN = ["TTFBBB", "TFFBBB", "WWWWBB", "FFBWWW", "FFFBBW", "TTFFBB"]
CITY = ["BBBBBB", "BBBBTB", "BBBBBB", "BTBBBB", "BBBBBB", "BBBBBW"]
CHANGES = {
    "clearing": (["TTTTTT"] * 4 + ["TTTTTF", "TTTTFF"], ["TTTTTT", "TTFFFT", "TFFFFT", "TFFFFF", "TTFFFF", "TTTTFF"]),
    "construction": (["FFFFTT", "FFFFFT", "BBFFFF", "BBFFFF", "BBBFFF", "BBBFFT"], ["FFFFTT", "BBBFFT", "BBBBFF", "BBBBBF", "BBBBBF", "BBBFFT"]),
    "drying": (["FFFFFF", "FWWWWF", "WWWWWF", "WWWWWF", "FWWWFF", "FFFFFF"], ["FFFFFF", "FFFFFF", "FFWWFF", "FWWWFF", "FFFFFF", "FFFFFF"]),
    "flood": (["FFFFTT", "FFFFFT", "WWWWWW", "FFFFFF", "FFBBFF", "FFBBFF"], ["FFFFTT", "FWWWWT", "WWWWWW", "WWWWWF", "FWBBWF", "FFBBFF"]),
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    if not (ARTIFACTS / "model.joblib").is_file():
        pytest.skip("Run scripts/prepare_study.py first.")
    monkeypatch.setattr(app_module, "RUNTIME", tmp_path / "runtime")
    # Offline by default: no key from the environment or .env.local reaches Google during tests.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(vision, "ROOT", tmp_path)
    with TestClient(app_module.app) as value:
        yield value


def jpeg(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=94)
    return buffer.getvalue()


def test_grid_plan_keeps_square_tiles_and_bounds():
    grid = plan_grid(1200, 800, "medium")
    assert (grid.rows, grid.cols) == (6, 9)
    assert grid.tile_px == pytest.approx(800 / 6)
    tall = plan_grid(300, 3000, "low")
    assert tall.cols == 4 and tall.rows == 12  # long side capped
    with pytest.raises(ValueError):
        plan_grid(500, 500, "ultra")


def test_group_names_come_from_the_post_hoc_audit():
    profiles = group_profiles(ARTIFACTS)
    assert sorted(profiles) == list(range(10))
    for profile in profiles.values():
        assert profile["land_type"] in {"trees", "farmland", "water", "built", "mixed"}
        assert sum(profile["shares"].values()) == pytest.approx(1, abs=1e-3)
        if profile["land_type"] != "mixed":
            assert profile["shares"][profile["land_type"]] == max(profile["shares"].values()) or profile["land_type"] in ("trees", "farmland")


def test_tiles_are_grouped_by_the_frozen_model_without_refitting(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Scene scanning must never refit the study model")
    for estimator in (StandardScaler, PCA, KMeans):
        monkeypatch.setattr(estimator, "fit", forbidden)
    monkeypatch.setattr(PCA, "fit_transform", forbidden)

    scene = Image.open(io.BytesIO(jpeg(mosaic(TOWN)))).convert("RGB")
    result = area_check(scene, ARTIFACTS, "medium")
    grid = plan_grid(*scene.size, "medium")
    tiles = cut_tiles(crop_to_grid(scene, grid), grid)
    model = load_model(ARTIFACTS)
    _, space = _project(model, np.stack([extract_features(tile) for tile in tiles]))
    expected = model["kmeans"].predict(space).tolist()
    assert [tile["cluster"] for tile in result["tiles"]] == expected
    assert sum(item["percent"] for item in result["breakdown"]) == pytest.approx(100, abs=0.5)
    assert result["run_id"] == model["reference_run_id"]


def test_identical_views_report_no_change():
    scene = mosaic(TOWN)
    result = change_check(scene, scene.copy(), ARTIFACTS, "medium")
    assert result["summary"]["changed_percent"] == 0
    assert result["summary"]["level"] == "none"
    assert result["verdict"]["story"] == "none"
    assert all(tile["change"] == "none" for tile in result["tiles"])


def test_unfamiliar_images_lower_reliability():
    blank = Image.new("RGB", (384, 384), (245, 245, 245))
    result = area_check(blank, ARTIFACTS, "low")
    assert result["reliability"]["level"] == "low"
    assert all(tile["unusual"] for tile in result["tiles"])


def test_area_check_without_reader_reports_unavailable(client):
    response = client.post("/api/area-check", files={"file": ("city.jpg", jpeg(mosaic(CITY)), "image/jpeg")})
    assert response.status_code == 503
    assert "not available" in response.json()["detail"]
    assert client.get("/api/scenes/presets").status_code == 404


def area_reply(rows=6, cols=6, skip=0):
    cells = []
    for row in range(rows):
        for col in range(cols):
            if col < 3:
                mix = {"trees": 70, "farmland": 20, "water": 0, "built": 10, "bare": 0}
            elif row == rows - 1:
                mix = {"trees": 30, "farmland": 0, "water": 0, "built": 35, "bare": 35}  # no clear winner -> mixed
            else:
                mix = {"trees": 5, "farmland": 0, "water": 0, "built": 90, "bare": 5}
            cells.append({"cell": f"{'ABCDEFGHIJKL'[col]}{row + 1}", **mix})
    cells.reverse()  # order must not matter: squares are matched by their labels
    return {
        "image_kind": "satellite", "setting": "town_or_suburb", "headline": "Houses beside a wooded strip",
        "summary": "A residential block next to trees.", "cells": cells[skip:],
        "features": ["Tree cover along the west side", "Dense houses to the east"], "quality_notes": [],
    }


def test_area_check_builds_report_from_per_square_mix(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vision, "_request", fake_gemini(area_reply(8, 8)))
    response = client.post("/api/area-check", files={"file": ("town.jpg", jpeg(mosaic(TOWN)), "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assert body["grid"] == {"rows": 8, "cols": 8}  # the app always reads at the detailed level
    assert body["tiles"][0]["land_type"] == "trees" and body["tiles"][3]["land_type"] == "built"
    assert body["tiles"][-1]["land_type"] == "mixed" and body["tiles"][-1]["shares"]["bare"] == 35
    shares = {item["land_type"]: item["percent"] for item in body["breakdown"]}
    assert shares["trees"] == pytest.approx((24 * 70 + 35 * 5 + 5 * 30) / 64, abs=0.1)
    assert sum(shares.values()) == pytest.approx(100, abs=0.5)
    assert body["place"]["headline"] == "Houses beside a wooded strip"
    assert body["reliability"]["level"] == "high"
    assert "cluster" not in body["tiles"][0] and "gemini" not in body["method"].lower()


def test_area_check_rejects_incomplete_readings(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vision, "_request", fake_gemini(area_reply(8, 8, skip=20)))
    response = client.post("/api/area-check", files={"file": ("town.jpg", jpeg(mosaic(TOWN)), "image/jpeg")})
    assert response.status_code == 422 and "could not be mapped" in response.json()["detail"]


def test_reading_grid_is_drawn_with_labels():
    scene = mosaic(TOWN).resize((900, 600))
    overlay = vision.grid_overlay(scene, 4, 6)
    assert overlay.size == (900, 600)
    assert overlay.getpixel((150, 300)) != scene.getpixel((150, 300))  # grid line drawn at column boundary


@pytest.mark.parametrize("story", sorted(CHANGES))
def test_crisis_radar_compare_names_each_change(client, story):
    before, after = CHANGES[story]
    files = {"before": ("b.jpg", jpeg(mosaic(before)), "image/jpeg"), "after": ("a.jpg", jpeg(mosaic(after)), "image/jpeg")}
    response = client.post("/api/change-check", files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"]["story"] == story
    assert body["summary"]["changed_percent"] >= 15
    assert body["verdict"]["next_steps"] and len(body["groups"]) == 10
    assert response.headers["cache-control"] == "no-store"


def fake_gemini(payload: dict):
    return lambda model, key, body: {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}], "modelVersion": model}


FLOOD_REPLY = {
    "image_kind": "satellite", "status": "crisis", "crisis_type": "flood", "secondary_types": ["none", "flood", "storm_damage", "made_up"],
    "severity": "high", "confidence": 1.7, "headline": "Fields under water", "summary": "Water covers farmland.",
    "scene_description": "Farmland by a river", "affected_area_percent": 140,
    "regions": [{"label": "Flooded fields", "box_2d": [100, 200, 500, 700]}, {"label": "broken", "box_2d": [1, 2, 3]}],
    "evidence": ["Water over field boundaries"], "actions": ["Avoid flooded roads"], "cloud_cover": "some", "quality_notes": [],
}


def test_crisis_scan_validates_the_model_reply(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vision, "_request", fake_gemini(FLOOD_REPLY))
    response = client.post("/api/crisis-scan", files={"file": ("scene.jpg", jpeg(mosaic(TOWN)), "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assessment = body["assessment"]
    assert body["vision_error"] is None
    assert assessment["crisis_type"] == "flood" and assessment["severity"] == "high"
    assert assessment["secondary_types"] == ["storm_damage"]
    assert assessment["confidence"] == 1 and assessment["affected_area_percent"] == 100
    assert assessment["regions"] == [{"label": "Flooded fields", "top": 10.0, "left": 20.0, "height": 40.0, "width": 50.0}]
    assert body["land"]["grid"] == {"rows": 6, "cols": 6}
    assert sum(item["percent"] for item in body["land"]["breakdown"]) == pytest.approx(100, abs=0.5)


def test_crisis_scan_normal_scene_clears_hazard_fields(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calm = {**FLOOD_REPLY, "status": "no_crisis", "crisis_type": "flood", "severity": "high", "affected_area_percent": 50}
    monkeypatch.setattr(vision, "_request", fake_gemini(calm))
    assessment = client.post("/api/crisis-scan", files={"file": ("s.jpg", jpeg(mosaic(CITY)), "image/jpeg")}).json()["assessment"]
    assert (assessment["crisis_type"], assessment["severity"], assessment["affected_area_percent"]) == ("none", "none", 0)


def test_crisis_scan_reports_unavailable_scanner_without_inventing_results(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(vision, "ROOT", Path("/nonexistent"))
    response = client.post("/api/crisis-scan", files={"file": ("s.jpg", jpeg(mosaic(TOWN)), "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assert body["assessment"] is None
    assert "not available" in body["vision_error"]["message"]
    assert body["land"]["tiles"]

    def rejected(model, key, payload):
        raise vision.urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
    monkeypatch.setenv("GEMINI_API_KEY", "bad-key")
    monkeypatch.setattr(vision, "_request", rejected)
    body = client.post("/api/crisis-scan", files={"file": ("s.jpg", jpeg(mosaic(TOWN)), "image/jpeg")}).json()
    assert body["assessment"] is None and "not available" in body["vision_error"]["message"]


def test_crisis_scan_falls_back_to_the_next_model(monkeypatch):
    calls = []

    def first_missing(model, key, payload):
        calls.append(model)
        if len(calls) == 1:
            raise vision.urllib.error.HTTPError("url", 404, "Not found", {}, None)
        return fake_gemini(FLOOD_REPLY)(model, key, payload)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "model-a,model-b")
    monkeypatch.setattr(vision, "_request", first_missing)
    result = vision.assess_crisis(Image.new("RGB", (256, 256), (40, 80, 120)))
    assert calls == ["model-a", "model-b"] and result["model"] == "model-b"


def test_scene_uploads_are_validated(client):
    tiny = jpeg(Image.new("RGB", (64, 64), (40, 90, 40)))
    city = jpeg(mosaic(CITY))
    for route in ("/api/area-check", "/api/crisis-scan"):
        assert client.post(route, files={"file": ("x.jpg", b"not an image", "image/jpeg")}).status_code == 422
        assert client.post(route, files={"file": ("x.jpg", tiny, "image/jpeg")}).status_code == 422
        assert client.post(route).status_code == 422
    assert client.post("/api/area-check", files={"file": ("c.jpg", city, "image/jpeg")}, data={"detail": "ultra"}).status_code == 422
    assert client.post("/api/change-check", files={"before": ("b.jpg", city, "image/jpeg")}).status_code == 422


def test_oversized_scene_upload_is_rejected_early(client):
    limit = UPLOAD_LIMITS["/api/area-check"]
    response = client.post(
        "/api/area-check", content=b"x" * 16, headers={"content-type": "multipart/form-data; boundary=x", "content-length": str(limit + 1)},
    )
    assert response.status_code == 413


def plant_reply(rows=8, cols=8):
    cells = [
        {"cell": f"{'ABCDEFGHIJKL'[c]}{r + 1}", "trees": 20, "plantable": 30 if c < 4 else 0, "built": 50 if c < 4 else 80, "water": 0, "other": 0}
        for r in range(rows) for c in range(cols)
    ]
    return {
        "image_kind": "satellite", "cells": cells, "headline": "Room for trees on the west side", "summary": "Open plots on the left.",
        "spots": [
            {"label": "Small courtyard", "kind": "courtyard", "priority": "low", "reason": "Small gap.", "box_2d": [600, 600, 700, 700]},
            {"label": "Vacant plot", "kind": "open_plot", "priority": "high", "reason": "Large empty plot.", "box_2d": [0, 0, 500, 500]},
            {"label": "Broken box", "kind": "roadside", "priority": "high", "reason": "Bad.", "box_2d": [10, 20]},
            {"label": "Verge", "kind": "made_up_kind", "priority": "medium", "reason": "Wide verge.", "box_2d": [500, 0, 600, 1000]},
        ],
        "quality_notes": [],
    }


def test_plant_check_without_reader_reports_unavailable(client):
    response = client.post("/api/plant-check", files={"file": ("p.jpg", jpeg(mosaic(TOWN)), "image/jpeg")})
    assert response.status_code == 503


def test_plant_check_counts_trees_and_ranks_spots(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vision, "_request", fake_gemini(plant_reply()))
    scene = jpeg(mosaic(TOWN))  # 384 x 384 px, read on an 8 x 8 grid
    body = client.post("/api/plant-check", files={"file": ("p.jpg", scene, "image/jpeg")}, data={"area_width": "colony"}).json()
    summary = body["summary"]
    assert body["grid"] == {"rows": 8, "cols": 8}
    assert summary["plantable_percent"] == 15.0 and summary["tree_cover_now"] == 20.0
    # 500 m wide square image = 250,000 m²; 15% open = 37,500 m²; 60% usable at 25 m² per tree = 900 trees
    assert summary["plantable_m2"] == 37500 and summary["trees_possible"] == 900
    assert summary["tree_cover_after"] == pytest.approx(29.0)
    assert [spot["label"] for spot in body["spots"]] == ["Vacant plot", "Verge", "Small courtyard"]  # broken box dropped, sorted
    assert body["spots"][0]["number"] == 1 and body["spots"][0]["area_m2"] == 62500
    assert body["spots"][1]["kind"] == "other"
    assert any("mini-forest" in idea for idea in body["ideas"])
    assert len(body["before_you_plant"]) == 5

    street = client.post("/api/plant-check", files={"file": ("p.jpg", scene, "image/jpeg")}, data={"area_width": "street"}).json()
    assert street["summary"]["plantable_m2"] == 6000  # (200/500)^2 of the colony estimate
    assert client.post("/api/plant-check", files={"file": ("p.jpg", scene, "image/jpeg")}, data={"area_width": "planet"}).status_code == 422
