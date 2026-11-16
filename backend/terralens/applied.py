"""Real-world operational capabilities: Regional Scene Scanner & Temporal Change Detector."""
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .features import FEATURE_NAMES, extract_features
from .inference import ArtifactVersion, _load_model, _project, analyze_image

CLUSTER_LABELS = {
    0: "Sea & Lake (Wetlands)",
    1: "Industrial Buildings",
    2: "Forest",
    3: "River & Waterways",
    4: "Annual Crops",
    5: "Permanent Crops",
    6: "Sea & Lake (Deep Water)",
    7: "Herbaceous Vegetation",
    8: "Pasture & Grassland",
    9: "Residential Buildings",
}

CLUSTER_COLORS = {
    0: "#1A5276",  # Dark blue
    1: "#7F8C8D",  # Gray
    2: "#196F3D",  # Forest green
    3: "#2980B9",  # Cyan-blue
    4: "#F39C12",  # Amber crop
    5: "#D35400",  # Rust orange
    6: "#154360",  # Deep navy
    7: "#27AE60",  # Light green
    8: "#82E0AA",  # Soft pasture
    9: "#8E44AD",  # Residential purple
}


def image_to_base64_jpeg(image: Image.Image, quality: int = 88) -> str:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def scan_regional_scene(image: Image.Image, artifacts_dir: Path, target_grid: int = 4) -> dict[str, Any]:
    """Tile an arbitrary satellite image into a grid of 64x64 patches and segment land cover."""
    artifacts_dir = Path(artifacts_dir)
    model_version = ArtifactVersion.read(artifacts_dir / "model.joblib")
    model = _load_model(model_version)

    # Standardize image to square multiple of 64 (e.g. 256x256 for 4x4 grid)
    target_dim = target_grid * 64
    rgb_img = image.convert("RGB")
    w, h = rgb_img.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    square = rgb_img.crop((left, top, left + min_dim, top + min_dim))
    resized = square.resize((target_dim, target_dim), Image.Resampling.LANCZOS)

    tiles = []
    cluster_counts: dict[int, int] = {}
    pca_centers = model["kmeans"].cluster_centers_

    for row in range(target_grid):
        for col in range(target_grid):
            tile_box = (col * 64, row * 64, (col + 1) * 64, (row + 1) * 64)
            tile_img = resized.crop(tile_box)
            raw = extract_features(tile_img)[None, :]
            standardized, space = _project(model, raw)
            point = space[0]
            cluster_id = int(model["kmeans"].predict(space)[0])

            distances = np.linalg.norm(point - pca_centers, axis=1)
            dist = float(distances[cluster_id])
            conf = max(0.15, min(0.99, float(1.0 - (dist / 8.0))))

            cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1

            # Determine dominant feature characteristics
            brightness = float(raw[0, FEATURE_NAMES.index("value_mean")])
            greenness = float(raw[0, FEATURE_NAMES.index("green_mean")])
            contrast = float(raw[0, FEATURE_NAMES.index("texture_contrast_d1")])
            features_summary = f"Brightness: {brightness:.2f} · Greenness: {greenness:.2f} · Contrast: {contrast:.1f}"

            tiles.append({
                "row": row,
                "col": col,
                "cluster_id": cluster_id,
                "cluster_name": CLUSTER_LABELS.get(cluster_id, f"Group {cluster_id + 1:02d}"),
                "color": CLUSTER_COLORS.get(cluster_id, "#4A7C59"),
                "confidence": round(conf, 3),
                "distance": round(dist, 3),
                "pca": point[:2].tolist(),
                "summary": features_summary,
            })

    total_tiles = target_grid * target_grid
    distribution = []
    for c_id, count in sorted(cluster_counts.items(), key=lambda x: x[1], reverse=True):
        pct = round((count / total_tiles) * 100, 1)
        distribution.append({
            "cluster_id": c_id,
            "name": CLUSTER_LABELS.get(c_id, f"Group {c_id + 1:02d}"),
            "count": count,
            "percentage": pct,
            "color": CLUSTER_COLORS.get(c_id, "#4A7C59"),
        })

    # Overall ecological assessment
    top_cluster = distribution[0]["cluster_id"]
    top_name = distribution[0]["name"]
    top_pct = distribution[0]["percentage"]

    forest_pct = sum(d["percentage"] for d in distribution if d["cluster_id"] == 2)
    water_pct = sum(d["percentage"] for d in distribution if d["cluster_id"] in (0, 3, 6))
    agri_pct = sum(d["percentage"] for d in distribution if d["cluster_id"] in (4, 5, 8))
    urban_pct = sum(d["percentage"] for d in distribution if d["cluster_id"] in (1, 9))

    narrative = f"Landscape is predominantly {top_name} ({top_pct}% of total surveyed area)."
    if forest_pct > 25:
        narrative += f" Substantial natural forest canopy cover ({forest_pct}%)."
    if water_pct > 10:
        narrative += f" Critical surface hydrological buffer present ({water_pct}%)."
    if urban_pct > 25:
        narrative += f" High density of built structures and impervious surfaces ({urban_pct}%)."
    if agri_pct > 25:
        narrative += f" Extensive agricultural tillage and pastureland ({agri_pct}%)."

    return {
        "grid_size": target_grid,
        "total_tiles": total_tiles,
        "input_dimensions": [w, h],
        "scanned_dimensions": [target_dim, target_dim],
        "tiles": tiles,
        "distribution": distribution,
        "assessment": narrative,
        "image_base64": image_to_base64_jpeg(resized),
    }


def detect_temporal_change(
    before_img: Image.Image,
    after_img: Image.Image,
    artifacts_dir: Path,
) -> dict[str, Any]:
    """Quantify land-cover transition and detect environmental degradation between two passes."""
    before_analysis = analyze_image(before_img, artifacts_dir)
    after_analysis = analyze_image(after_img, artifacts_dir)

    b_cluster = before_analysis["cluster"]
    a_cluster = after_analysis["cluster"]
    b_pca = np.array(before_analysis["pca"])
    a_pca = np.array(after_analysis["pca"])
    pca_distance = float(np.linalg.norm(b_pca - a_pca))

    # Feature diffs
    b_feat = {f["name"]: f["value"] for f in before_analysis["features"]}
    a_feat = {f["name"]: f["value"] for f in after_analysis["features"]}

    green_delta = (a_feat.get("green_mean", 0) - b_feat.get("green_mean", 0)) / max(b_feat.get("green_mean", 1), 0.01)
    albedo_delta = (a_feat.get("value_mean", 0) - b_feat.get("value_mean", 0)) / max(b_feat.get("value_mean", 1), 0.01)
    texture_delta = (a_feat.get("texture_contrast_d1", 0) - b_feat.get("texture_contrast_d1", 0)) / max(b_feat.get("texture_contrast_d1", 1), 0.01)
    entropy_delta = (a_feat.get("grey_entropy", 0) - b_feat.get("grey_entropy", 0)) / max(b_feat.get("grey_entropy", 1), 0.01)

    # Classify alert
    if b_cluster == 2 and a_cluster != 2:
        alert_level = "CRITICAL"
        alert_title = "Forest Canopy Depletion Alert"
        narrative = (
            f"Severe vegetation loss detected. Land signature shifted from Forest (Group 02) "
            f"to {CLUSTER_LABELS.get(a_cluster, 'Cleared Land')} (Group {a_cluster + 1:02d}). "
            f"Chlorophyll greenness reduced by {abs(green_delta)*100:.1f}% with significant canopy entropy loss."
        )
        recommendation = "Immediate on-ground dispatch recommended to inspect illegal deforestation or burn scars."
    elif b_cluster in (0, 3, 6) and a_cluster not in (0, 3, 6):
        alert_level = "WARNING"
        alert_title = "Hydrological Depletion Warning"
        narrative = (
            f"Surface water body shrinkage detected. Waterway (Group {b_cluster + 1:02d}) shifted to "
            f"{CLUSTER_LABELS.get(a_cluster, 'Exposed Riverbed')} (Group {a_cluster + 1:02d}). "
            f"Albedo increased by {albedo_delta*100:.1f}%, consistent with exposed sandbars or severe drought."
        )
        recommendation = "Issue regional drought advisory and adjust reservoir release schedules."
    elif b_cluster in (4, 5, 7, 8) and a_cluster in (1, 9):
        alert_level = "WARNING"
        alert_title = "Urban Encroachment Alert"
        narrative = (
            f"Rapid infrastructure expansion detected. Permeable rural land (Group {b_cluster + 1:02d}) "
            f"converted to {CLUSTER_LABELS.get(a_cluster, 'Built Structures')} (Group {a_cluster + 1:02d}). "
            f"Texture contrast increased by {texture_delta*100:.1f}% due to artificial roof grids."
        )
        recommendation = "Cross-reference satellite coordinates with municipal zoning permits."
    elif b_cluster == a_cluster and pca_distance < 1.2:
        alert_level = "STABLE"
        alert_title = "Ecological Equilibrium Maintained"
        narrative = (
            f"Land cover remained stable within {CLUSTER_LABELS.get(b_cluster, 'same category')}. "
            f"Spectral drift distance is minimal ({pca_distance:.2f} in 28-PC space), well within seasonal limits."
        )
        recommendation = "Maintain standard recurring satellite monitoring cadence."
    else:
        alert_level = "INFO"
        alert_title = "Spectral Drift Detected"
        narrative = (
            f"Land cover transitioned from {CLUSTER_LABELS.get(b_cluster, f'Group {b_cluster+1}')} "
            f"to {CLUSTER_LABELS.get(a_cluster, f'Group {a_cluster+1}')} (PCA drift: {pca_distance:.2f})."
        )
        recommendation = "Flag patch for continued observation in subsequent Sentinel-2 overpasses."

    return {
        "before": {
            "cluster": b_cluster,
            "cluster_name": CLUSTER_LABELS.get(b_cluster, f"Group {b_cluster + 1:02d}"),
            "color": CLUSTER_COLORS.get(b_cluster, "#4A7C59"),
            "distance": round(before_analysis["distance"], 3),
            "pca": before_analysis["pca"],
            "image_base64": image_to_base64_jpeg(before_img.resize((64, 64))),
        },
        "after": {
            "cluster": a_cluster,
            "cluster_name": CLUSTER_LABELS.get(a_cluster, f"Group {a_cluster + 1:02d}"),
            "color": CLUSTER_COLORS.get(a_cluster, "#4A7C59"),
            "distance": round(after_analysis["distance"], 3),
            "pca": after_analysis["pca"],
            "image_base64": image_to_base64_jpeg(after_img.resize((64, 64))),
        },
        "pca_distance": round(pca_distance, 3),
        "alert": {
            "level": alert_level,
            "title": alert_title,
            "narrative": narrative,
            "recommendation": recommendation,
        },
        "deltas": {
            "greenness": round(green_delta * 100, 1),
            "albedo": round(albedo_delta * 100, 1),
            "contrast": round(texture_delta * 100, 1),
            "entropy": round(entropy_delta * 100, 1),
        },
    }
