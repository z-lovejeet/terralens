"""Land model, Map my image and Sort my photos: all built on the frozen PCA + K-Means study pipeline."""

import io
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from terralens import app as app_module
from terralens.features import extract_features
from terralens.inference import _project, load_model
from terralens.landmodel import classify_features, group_profiles, land_model
from terralens.settings import UPLOAD_LIMITS

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
CODES = {"T": "trees", "F": "farmland", "W": "water", "B": "built"}


@lru_cache(maxsize=1)
def tile_pools() -> dict[str, list[str]]:
    """Cohort patches nearest the purest land-group centres for each land type (by frozen group, not label)."""
    profiles = group_profiles(ARTIFACTS)
    with np.load(ARTIFACTS / "compact_features.npz", allow_pickle=False) as bundle:
        raw, ids = bundle["X"], bundle["ids"]
    grouped = classify_features(raw, ARTIFACTS)
    clusters, distances = grouped["clusters"], grouped["distances"]
    pools = {}
    for land_type in CODES.values():
        ranked = sorted((c for c, p in profiles.items() if p["land_type"] == land_type), key=lambda c: -profiles[c]["reliability"])
        pool = []
        for group in ranked:  # purest groups first, closest members first, until there are enough tiles
            members = np.flatnonzero(clusters == group)
            pool += [str(ids[i]) for i in members[np.argsort(distances[members], kind="stable")]]
            if len(pool) >= 36:
                break
        pools[land_type] = pool[:36]
    return pools


@pytest.fixture
def client(tmp_path, monkeypatch):
    if not (ARTIFACTS / "model.joblib").is_file():
        pytest.skip("Run scripts/prepare_study.py first.")
    monkeypatch.setattr(app_module, "RUNTIME", tmp_path / "runtime")
    with TestClient(app_module.app) as value:
        yield value


def jpeg(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=94)
    return buffer.getvalue()


def forbid_refitting(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("The study scaler and PCA must never be refitted")
    monkeypatch.setattr(StandardScaler, "fit", forbidden)
    monkeypatch.setattr(PCA, "fit", forbidden)
    monkeypatch.setattr(PCA, "fit_transform", forbidden)


# ---------------------------------------------------------------------------
# 30-group land model
# ---------------------------------------------------------------------------

def test_group_names_come_from_the_post_hoc_audit():
    profiles = group_profiles(ARTIFACTS)
    assert sorted(profiles) == list(range(30))
    for profile in profiles.values():
        assert profile["land_type"] in {"trees", "farmland", "water", "built", "mixed"}
        assert sum(profile["shares"].values()) == pytest.approx(1, abs=1e-3)


def test_land_labels_use_the_frozen_projection(monkeypatch):
    forbid_refitting(monkeypatch)
    with np.load(ARTIFACTS / "compact_features.npz", allow_pickle=False) as bundle:
        raw = bundle["X"][:50]
    result = classify_features(raw, ARTIFACTS)
    model, land = load_model(ARTIFACTS), land_model(ARTIFACTS)
    _, space = _project(model, raw)
    assert result["clusters"].tolist() == land["kmeans"].predict(space).tolist()
    assert result["run_id"] == land["run_id"] and land["base_run_id"] == model["reference_run_id"]


def test_unfamiliar_images_are_flagged():
    blank = extract_features(Image.new("RGB", (64, 64), (245, 245, 245)))[None, :]
    assert classify_features(blank, ARTIFACTS)["unusual"].tolist() == [True]


def test_land_model_is_recorded_and_beats_the_ten_group_labels():
    audit = json.loads((ARTIFACTS / "land-model-audit.json").read_text())
    evaluation = audit["evaluation"]
    assert audit["k"] == 30 and audit["base_run_id"] == load_model(ARTIFACTS)["reference_run_id"]
    assert evaluation["holdout_patches"] == 5400
    assert evaluation["accuracy_strict"] > evaluation["reference_10_groups"]["accuracy_strict"] + 0.1
    assert evaluation["named_share"] > evaluation["reference_10_groups"]["named_share"]
    assert sum(sum(row.values()) for row in evaluation["confusion"].values()) == 5400


# ---------------------------------------------------------------------------
# Map my image
# ---------------------------------------------------------------------------

LAYOUT = ["WWWWBBBB", "WWWWBBBB", "WWWBBBBB", "WWTTTBBB", "TTTTTTBB", "TTTTTTTB", "TTTTTTTT", "TTTTTTTT"]


def region_scene(layout=LAYOUT, size=768) -> tuple[bytes, np.ndarray]:
    """A scene of real satellite tiles with a known layout, enlarged like a screenshot."""
    pools, used = tile_pools(), {}
    scene = Image.new("RGB", (64 * len(layout[0]), 64 * len(layout)))
    for r, row in enumerate(layout):
        for c, code in enumerate(row):
            land = CODES[code]; index = used.get(land, 0); used[land] = index + 1
            with Image.open(ARTIFACTS / "thumbnails" / f"{pools[land][index % len(pools[land])]}.jpg") as patch:
                scene.paste(patch.convert("RGB"), (c * 64, r * 64))
    truth = np.repeat(np.repeat(np.array([[CODES[ch] for ch in row] for row in layout]), 3, axis=0), 3, axis=1).ravel()
    return jpeg(scene.resize((size, size), Image.Resampling.BICUBIC)), truth


def test_map_regions_recovers_a_known_layout(client):
    from sklearn.metrics import adjusted_rand_score
    upload, truth = region_scene()
    body = client.post("/api/map-regions", files={"file": ("scene.jpg", upload, "image/jpeg")}, data={"count": "3"}).json()
    assert body["grid"] == {"rows": 24, "cols": 24} and len(body["cells"]) == 576
    assert body["k"] == 3 and body["chosen"] == "you"
    assert sum(region["share"] for region in body["regions"]) == pytest.approx(100, abs=0.5)
    assert [region["letter"] for region in body["regions"]] == ["A", "B", "C"]
    assert adjusted_rand_score(truth, body["cells"]) > 0.5
    assert all(region["description"] for region in body["regions"])
    auto = client.post("/api/map-regions", files={"file": ("scene.jpg", upload, "image/jpeg")}).json()
    assert auto["chosen"] == "automatic" and 2 <= auto["k"] <= 8
    assert [c["k"] for c in auto["candidates"]] == list(range(2, 9))


def test_regions_are_named_by_the_land_model_when_the_image_matches_the_training_data(client):
    upload, truth = region_scene()
    body = client.post("/api/map-regions", files={"file": ("scene.jpg", upload, "image/jpeg")}, data={"count": "3"}).json()
    assert body["naming"]["method"] == "land model"
    assert sum(item["share"] for item in body["land_cover"]) == pytest.approx(100, abs=0.5)
    cells = np.array(body["cells"])
    for region in body["regions"]:
        assert region["named_by"] == "land model"
        if region["name"] == "mixed":
            continue
        assert region["confidence"] == "high" and region["model_agreement"] >= 0.5
        values, counts = np.unique(truth[cells == region["region"]], return_counts=True)
        assert region["name"] == values[counts.argmax()]  # names on this known scene are right


def test_colour_and_texture_reading_names_typical_regions():
    from terralens.reading import read_region
    base = {"greenness": 0.05, "redness": 0.1, "brightness": 0.45, "texture": 0.03, "rows": 0.5, "dark": 0.0}
    read = lambda **cues: read_region({**base, **cues}, least_green=0.02)[0]
    assert read(greenness=0.2, texture=0.003, redness=0.02, brightness=0.25) == "water"       # calm lake
    assert read(brightness=0.06, dark=0.99, texture=0.006) == "water"                          # deep dark river
    assert read(texture=0.12, rows=0.35) == "built"                                            # roofs and streets
    assert read(brightness=0.75, texture=0.01) == "bare"                                       # sand bank
    assert read(greenness=0.24, texture=0.066, rows=0.3, brightness=0.2) == "trees"            # forest canopy
    assert read(greenness=0.18, texture=0.012, rows=0.67, brightness=0.38, redness=0.15) == "farmland"  # crop rows
    assert read(greenness=0.6, texture=0.0, brightness=0.5) != "water"                         # vivid flat green is plants


def test_map_regions_never_changes_the_saved_study_models():
    from terralens.regions import map_regions
    model, land = load_model(ARTIFACTS), land_model(ARTIFACTS)
    before = (model["scaler"].mean_.copy(), model["pca"].components_.copy(), land["kmeans"].cluster_centers_.copy())
    upload, _ = region_scene(size=384)
    result = map_regions(Image.open(io.BytesIO(upload)), ARTIFACTS, 2)
    assert result["k"] == 2 and len(result["cells"]) == 576
    after = (model["scaler"].mean_, model["pca"].components_, land["kmeans"].cluster_centers_)
    assert all(np.array_equal(a, b) for a, b in zip(before, after))


def test_a_few_extreme_squares_do_not_hijack_the_regions():
    """Regression: bright out-of-range squares used to capture whole clusters and hide the main split."""
    from sklearn.metrics import adjusted_rand_score
    from terralens.regions import map_regions
    layout = ["WWWWBBBB"] * 8
    upload, truth = region_scene(layout, size=768)
    scene = Image.open(io.BytesIO(upload)).convert("RGB")
    for x, y in ((40, 40), (500, 300), (650, 650)):  # glare-like white blocks, like shiny roofs
        scene.paste((255, 255, 255), (x, y, x + 40, y + 40))
    result = map_regions(scene, ARTIFACTS, 2)
    assert adjusted_rand_score(truth, result["cells"]) > 0.6
    assert min(region["share"] for region in result["regions"]) > 20


def test_images_unlike_the_training_data_are_named_from_colour_and_texture():
    from terralens.reading import READ_TYPES
    from terralens.regions import map_regions
    cartoon = Image.new("RGB", (600, 600), (30, 140, 40))
    cartoon.paste((240, 240, 240), (0, 0, 300, 600))
    result = map_regions(cartoon, ARTIFACTS)
    assert result["naming"]["method"] == "colour and texture" and result["naming"]["unfamiliar_percent"] >= 30
    assert all(region["named_by"] == "colour and texture" and region["name"] in READ_TYPES for region in result["regions"])
    assert all(region["model_agreement"] is None and region["confidence"] in ("medium", "low") for region in result["regions"])
    assert {region["name"] for region in result["regions"]} == {"bare", "farmland"}  # bright white ground, flat green plants
    assert result["k"] == 2  # only two distinct-looking kinds of square exist
    from terralens.regions import map_regions as mapper
    with pytest.raises(ValueError):
        mapper(Image.new("RGB", (300, 300), (30, 140, 40)), ARTIFACTS)


def test_map_regions_reports_its_measured_accuracy(client):
    report = json.loads((ARTIFACTS / "regions-benchmark.json").read_text())
    assert report["scenes"] >= 20 and set(report["results"]) == {"native", "zoomed_x3"}
    upload, _ = region_scene(size=256)
    accuracy = client.post("/api/map-regions", files={"file": ("s.jpg", upload, "image/jpeg")}).json()["accuracy"]
    assert accuracy["ari"] == report["results"]["native"]["ari"] and accuracy["name_accuracy"] > 0.9
    assert accuracy["colour_texture"]["views"] == 14 and accuracy["colour_texture"]["accuracy"] > 0.8


def test_map_regions_validates_input(client):
    upload, _ = region_scene(size=256)
    assert client.post("/api/map-regions").status_code == 422
    assert client.post("/api/map-regions", files={"file": ("x.jpg", b"not an image", "image/jpeg")}).status_code == 422
    small = jpeg(Image.new("RGB", (100, 100), (40, 90, 40)))
    assert client.post("/api/map-regions", files={"file": ("s.jpg", small, "image/jpeg")}).status_code == 422
    for bad in ("1", "9", "lots"):
        assert client.post("/api/map-regions", files={"file": ("s.jpg", upload, "image/jpeg")}, data={"count": bad}).status_code == 422
    assert "/api/map-regions" in UPLOAD_LIMITS


# ---------------------------------------------------------------------------
# Sort my photos
# ---------------------------------------------------------------------------

def photo_batch(per_type: int = 8, types=("water", "built", "trees")) -> list:
    pools, files = tile_pools(), []
    for land_type in types:
        for patch_id in pools[land_type][:per_type]:
            with Image.open(ARTIFACTS / "thumbnails" / f"{patch_id}.jpg") as patch:
                files.append(("files", (f"{land_type}-{patch_id}.jpg", jpeg(patch.convert("RGB").resize((128, 128))), "image/jpeg")))
    return files


def test_sort_photos_separates_clearly_different_land(client):
    files = photo_batch()
    body = client.post("/api/sort-photos", files=files, data={"groups": "3"}).json()
    assert body["k"] == 3 and body["chosen"] == "you" and body["photo_count"] == 24
    assert sorted(i for group in body["groups"] for i in group["members"]) == list(range(24))
    for group in body["groups"]:
        sources = [body["photos"][i]["name"].split("-")[0] for i in group["members"]]
        assert max(sources.count(s) for s in set(sources)) / len(sources) >= 0.75, sources
        assert group["description"]
    auto = client.post("/api/sort-photos", files=files).json()
    assert auto["chosen"] == "automatic" and 2 <= auto["k"] <= 10
    assert [c["k"] for c in auto["candidates"]] == list(range(2, 11))
    from terralens.sorting import _elbow
    assert auto["k"] == _elbow([c["k"] for c in auto["candidates"]], [c["inertia"] for c in auto["candidates"]])


def test_elbow_rule_finds_the_bend_of_the_inertia_curve():
    from terralens.sorting import _elbow
    # sharp drop until 4 groups, then almost flat: the elbow is 4
    assert _elbow([2, 3, 4, 5, 6, 7], [100, 60, 25, 22, 20, 19]) == 4
    assert _elbow([2, 3], [10, 5]) == 2


def test_sort_photos_uses_the_frozen_projection(monkeypatch):
    from terralens.sorting import sort_photos
    forbid_refitting(monkeypatch)
    photos = [(name, Image.open(io.BytesIO(data))) for _, (name, data, _) in photo_batch(per_type=3)]
    result = sort_photos(photos, ARTIFACTS, 2)
    assert result["k"] == 2 and len(result["photos"]) == 9


def test_sort_photos_validates_input(client):
    files = photo_batch(per_type=2)
    assert client.post("/api/sort-photos", files=files[:3]).status_code == 422
    assert client.post("/api/sort-photos", files=files, data={"groups": "many"}).status_code == 422
    assert client.post("/api/sort-photos", files=files, data={"groups": "6"}).status_code == 422  # not fewer than photos
    bad = files[:4] + [("files", ("broken.jpg", b"not an image", "image/jpeg"))]
    response = client.post("/api/sort-photos", files=bad)
    assert response.status_code == 422 and "broken.jpg" in response.json()["detail"]
    assert "/api/sort-photos" in UPLOAD_LIMITS
