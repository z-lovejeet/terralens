"""Sort my photos: group a user's own satellite land images with unsupervised learning.

Every photo goes through the study's fixed pipeline (78 descriptors, study-fitted scaler,
28-component PCA). The photos are then clustered with K-Means++ in that space; when the
user does not choose a number of groups, K is picked automatically at the elbow of the
inertia curve (where adding groups stops making them much tighter). Each group is described
in plain words from the descriptors that set it apart, and given its most common land type from the 30-group land model. No label,
outside service or internet connection is involved.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score

from .features import FEATURE_NAMES, extract_features
from .landmodel import LAND_TYPES, classify_features

MIN_PHOTOS = 4
MAX_PHOTOS = 300
MAX_AUTO_K = 10
MAX_CHOSEN_K = 12
SEED = 42


def _square_patch(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    side = min(rgb.size)
    left, top = (rgb.width - side) // 2, (rgb.height - side) // 2
    return rgb.crop((left, top, left + side, top + side)).resize((64, 64), Image.Resampling.LANCZOS)


def _family(prefixes: tuple[str, ...], exact: tuple[str, ...] = ()) -> list[int]:
    return [i for i, name in enumerate(FEATURE_NAMES) if name in exact or name.startswith(prefixes)]


# Plain-language families: (higher phrase, lower phrase, [(descriptor index, sign)]).
# Each family is averaged first, so many correlated histogram bins cannot outvote one clear signal.
FAMILIES = [
    ("brighter", "darker", [(i, 1) for i in _family((), ("value_mean", "red_mean", "green_mean", "blue_mean", "red_median", "green_median", "blue_median"))]),
    ("more colourful", "duller in colour", [(i, 1) for i in _family((), ("saturation_mean",))]),
    ("busier, more detailed texture", "smoother texture",
     [(i, 1) for i in _family(("texture_contrast", "texture_dissimilarity", "edge_mean", "edge_density", "edge_p90", "grey_entropy"))]
     + [(i, -1) for i in _family(("texture_homogeneity", "texture_energy", "texture_asm"))]),
    ("greener", "less green", [(i, 1) for i in _family(("hue_bin_02", "hue_bin_03", "hue_bin_04"))]),
    ("bluer", "less blue", [(i, 1) for i in _family(("hue_bin_06", "hue_bin_07", "hue_bin_08"))]),
    ("redder or browner", "less red or brown", [(i, 1) for i in _family(("hue_bin_00", "hue_bin_01", "hue_bin_11"))]),
    ("more varied in tone", "more even in tone", [(i, 1) for i in _family((), ("red_std", "green_std", "blue_std", "value_std", "saturation_std"))]),
]
MIN_DESCRIBED_SHIFT = 0.3  # in study standard deviations


def _describe(offsets: np.ndarray) -> list[str]:
    """Up to two plain phrases for what most sets a group apart from the other photos."""
    scored = []
    for higher, lower, members in FAMILIES:
        value = float(np.mean([sign * offsets[index] for index, sign in members]))
        if abs(value) >= MIN_DESCRIBED_SHIFT:
            scored.append((abs(value), higher if value > 0 else lower))
    phrases = [text for _, text in sorted(scored, reverse=True)[:2]]
    return phrases or ["close to the average of your photos"]


def _elbow(ks: list[int], inertia: list[float]) -> int:
    """The elbow of the inertia curve: the K farthest below the straight line from the first to the last K.

    Adding groups always makes them tighter (lower inertia); the elbow is where adding more stops
    helping much. On held-out EuroSAT batches with a known number of land types this chose K better
    than the best-silhouette rule (mean ARI 0.37 vs 0.26; knowing the true K gives 0.38).
    """
    if len(ks) < 3:
        return ks[0]
    x = (np.array(ks) - ks[0]) / (ks[-1] - ks[0])
    y = (np.array(inertia) - min(inertia)) / ((max(inertia) - min(inertia)) or 1.0)
    return int(ks[int(np.argmax((1 - x) - y))])


def _choose_k(space: np.ndarray, requested: int | None) -> tuple[int, list[dict]]:
    n = len(space)
    upper = min(MAX_AUTO_K, n - 1)
    candidates = []
    for k in range(2, upper + 1):
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(space)
        if len(np.unique(kmeans.labels_)) < 2:
            continue
        candidates.append({
            "k": k,
            "inertia": round(float(kmeans.inertia_), 4),
            "silhouette": round(float(silhouette_score(space, kmeans.labels_)), 4),
        })
    if requested is not None:
        return min(requested, n - 1), candidates
    if not candidates:
        return 2, candidates
    return _elbow([c["k"] for c in candidates], [c["inertia"] for c in candidates]), candidates


def sort_photos(photos: list[tuple[str, Image.Image]], artifacts_dir: Path, requested_k: int | None = None) -> dict:
    if not MIN_PHOTOS <= len(photos) <= MAX_PHOTOS:
        raise ValueError(f"Choose between {MIN_PHOTOS} and {MAX_PHOTOS} photos.")
    if requested_k is not None and not 2 <= requested_k <= MAX_CHOSEN_K:
        raise ValueError(f"Choose between 2 and {MAX_CHOSEN_K} groups.")

    raw = np.stack([extract_features(_square_patch(image)) for _, image in photos])
    land = classify_features(raw, artifacts_dir)
    space = land["space"]
    k, candidates = _choose_k(space, requested_k)
    kmeans = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(space)
    labels = kmeans.labels_
    distances = np.linalg.norm(space - kmeans.cluster_centers_[labels], axis=1)
    silhouette = float(silhouette_score(space, labels)) if len(np.unique(labels)) > 1 else None

    # Standardised descriptors (study units) relative to this photo set, to describe what sets each group apart.
    from .inference import ArtifactVersion, _load_model
    model = _load_model(ArtifactVersion.read(Path(artifacts_dir) / "model.joblib"))
    standardized = model["scaler"].transform(model["imputer"].transform(raw))
    overall = standardized.mean(axis=0)

    outlier = np.zeros(len(photos), dtype=bool)
    groups = []
    for group in range(k):
        members = np.flatnonzero(labels == group)
        member_distances = distances[members]
        if len(members) >= 4:
            q1, q3 = np.percentile(member_distances, [25, 75])
            outlier[members[member_distances > q3 + 1.5 * (q3 - q1)]] = True
        types = [land["land_types"][i] for i in members]
        counts = {t: types.count(t) for t in (*LAND_TYPES.keys(),) if types.count(t)}
        dominant = max(counts, key=counts.get)
        groups.append({
            "group": group,
            "size": int(len(members)),
            "members": [int(i) for i in members[np.argsort(member_distances, kind="stable")]],
            "land_type": dominant,
            "land_share": round(counts[dominant] / len(members), 3),
            "land_counts": counts,
            "description": _describe(standardized[members].mean(axis=0) - overall),
            "spread": round(float(np.mean(member_distances)), 3),
        })
    groups.sort(key=lambda item: -item["size"])
    order = {item["group"]: rank for rank, item in enumerate(groups)}
    for item in groups:
        item["group"] = order[item["group"]]

    photo_rows = [
        {
            "index": index,
            "name": name[:120],
            "group": order[int(labels[index])],
            "land_type": land["land_types"][index],
            "distance": round(float(distances[index]), 3),
            "outlier": bool(outlier[index]),
            "unfamiliar": bool(land["unusual"][index]),
            "pca": [round(float(space[index, 0]), 4), round(float(space[index, 1]), 4)],
        }
        for index, (name, _) in enumerate(photos)
    ]
    unfamiliar_share = float(np.mean(land["unusual"]))
    if silhouette is None or silhouette < 0.1:
        quality = "weak"
    elif silhouette < 0.25:
        quality = "moderate"
    else:
        quality = "clear"
    return {
        "photo_count": len(photos),
        "k": k,
        "chosen": "you" if requested_k is not None else "automatic",
        "silhouette": round(silhouette, 4) if silhouette is not None else None,
        "davies_bouldin": round(float(davies_bouldin_score(space, labels)), 4) if k > 1 else None,
        "separation": quality,
        "candidates": candidates,
        "groups": groups,
        "photos": photo_rows,
        "unfamiliar_percent": round(100 * unfamiliar_share, 1),
        "land_run_id": land["run_id"],
        "method": (
            "Each photo is cropped to a square, described by the study's 78 colour, texture and edge measurements, "
            "standardised and projected with the study's PCA (28 components). The photos are then grouped with K-Means++ "
            "in that space. When you leave the number of groups on Auto, every option from 2 to 10 is tried and the elbow "
            "method picks the number where adding more groups stops making them much tighter. Land types come from "
            "the 30-group land model. Nothing is sent outside this server."
        ),
    }
