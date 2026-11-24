"""Everyday land labels from the unsupervised land model.

The 30-group land model (``scripts/build_land_model.py``) is K-Means++ fitted on the study
patches in the frozen 28-component PCA space. Plain-language land types are attached to its
groups afterwards, from the post-hoc audit (which EuroSAT categories each frozen group mostly
contains). Labels are used only to *name* groups, never to assign an image to a group.
If the land model has not been built, the 10 reference groups are used instead.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

import numpy as np

from .inference import ArtifactVersion, _load_model, _project

LAND_MODEL_FILENAME = "land-model.joblib"
# An image is unfamiliar when it sits further from its group centre than 1.5x the distance
# that only 1% of the 21,600 study patches exceed (any group).
UNUSUAL_FACTOR = 1.5
UNUSUAL_REFERENCE_PERCENTILE = 99

# Everyday land types and the EuroSAT reference categories they summarise.
LAND_TYPES: dict[str, dict] = {
    "trees": {"label": "Trees & greenery", "classes": ("Forest", "HerbaceousVegetation")},
    "farmland": {"label": "Fields & farmland", "classes": ("AnnualCrop", "PermanentCrop", "Pasture")},
    "water": {"label": "Water", "classes": ("River", "SeaLake")},
    "built": {"label": "Buildings & roads", "classes": ("Residential", "Industrial", "Highway")},
    "mixed": {"label": "Mixed land", "classes": ()},
}
LAND_ORDER = ("trees", "farmland", "water", "built", "mixed")
VEGETATED = ("trees", "farmland")


# ---------------------------------------------------------------------------
# Naming the frozen groups
# ---------------------------------------------------------------------------

def _name_group(shares: dict[str, float]) -> str:
    """A group takes a land type only when that type clearly dominates it."""
    top = max(LAND_ORDER[:4], key=lambda key: shares[key])
    if shares[top] >= 0.5:
        return top
    if shares["trees"] + shares["farmland"] >= 0.75:
        return max(VEGETATED, key=lambda key: shares[key])
    return "mixed"


@lru_cache(maxsize=2)
def _group_profiles(audit_version: ArtifactVersion, run_id: str) -> dict[int, dict]:
    audit = json.loads(audit_version.path.read_text(encoding="utf-8"))
    if audit.get("reference_run_id") != run_id:
        raise ValueError("The saved audit does not describe the frozen scanning model")
    class_to_type = {name: key for key, value in LAND_TYPES.items() for name in value["classes"]}
    profiles = {}
    for row in audit["contingency"]:
        total = max(int(row["total"]), 1)
        shares = dict.fromkeys(LAND_ORDER[:4], 0.0)
        for name, count in row["counts"].items():
            shares[class_to_type[name]] += count / total
        land_type = _name_group(shares)
        profiles[int(row["cluster"])] = {
            "land_type": land_type,
            "shares": {key: round(value, 4) for key, value in shares.items()},
            # How often patches in this group really are the named land type.
            "reliability": round(shares[land_type] if land_type != "mixed" else max(shares.values()), 4),
        }
    return profiles


@lru_cache(maxsize=2)
def _load_land_model(version: ArtifactVersion) -> dict:
    # Only the application-generated land model is loaded (scripts/build_land_model.py).
    return _load_model(version)


def land_model(artifacts_dir: Path) -> dict | None:
    """The 30-group land model fitted on the frozen PCA space, if it has been built."""
    path = Path(artifacts_dir) / LAND_MODEL_FILENAME
    if not path.is_file():
        return None
    land = _load_land_model(ArtifactVersion.read(path))
    reference = _load_model(ArtifactVersion.read(Path(artifacts_dir) / "model.joblib"))
    if land["base_run_id"] != reference["reference_run_id"] or land["components"] != reference["components"]:
        raise ValueError("The land model was not built on the frozen reference projection")
    return land


def group_profiles(artifacts_dir: Path) -> dict[int, dict]:
    """Everyday names for the groups used to label squares: the 30-group land model, or the 10 reference groups."""
    land = land_model(artifacts_dir)
    if land is not None:
        return {int(group): dict(profile) for group, profile in land["groups"].items()}
    model = _load_model(ArtifactVersion.read(Path(artifacts_dir) / "model.joblib"))
    return _group_profiles(ArtifactVersion.read(Path(artifacts_dir) / "audit.json"), model["reference_run_id"])


def classify_features(raw: np.ndarray, artifacts_dir: Path) -> dict:
    """Group descriptor rows with the frozen projection and the land model (or the 10 reference groups)."""
    model = _load_model(ArtifactVersion.read(Path(artifacts_dir) / "model.joblib"))
    labeller = land_model(artifacts_dir) or model
    profiles = group_profiles(artifacts_dir)
    _, space = _project(model, raw)
    clusters = labeller["kmeans"].predict(space)
    centres = labeller["kmeans"].cluster_centers_
    distances = np.linalg.norm(space - centres[clusters], axis=1)
    reference = np.concatenate(list(labeller["cluster_distances"].values()))
    unusual_limit = UNUSUAL_FACTOR * float(np.percentile(reference, UNUSUAL_REFERENCE_PERCENTILE))
    return {
        "run_id": labeller.get("run_id", model["reference_run_id"]),
        "clusters": clusters,
        "space": space,
        "distances": distances,
        "unusual": distances > unusual_limit,
        "land_types": [profiles[int(cluster)]["land_type"] for cluster in clusters],
        "profiles": profiles,
    }
