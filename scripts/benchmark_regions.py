"""Measure how well Map my image recovers regions in scenes with a known layout.

Each test scene is an 8 x 8 mosaic of held-out EuroSAT patches arranged in blobs of 2-5
clearly different land types (forest, lake or sea, houses, crop fields, industrial). The scene
is mapped exactly as the app does it, then compared with the true layout. The evaluation-only
labels are used only for this scoring. Results are written to artifacts/regions-benchmark.json,
which the app reads to show its measured accuracy.

Run:  PYTHONPATH=backend .venv/bin/python scripts/benchmark_regions.py
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import random

import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score

from terralens.regions import map_regions

ROOT = Path(__file__).resolve().parents[1]
TYPES = {"Forest": "trees", "SeaLake": "water", "Residential": "built", "AnnualCrop": "farmland", "Industrial": "built"}
SCENES = 30
TILES = 8


def make_scene(rnd: random.Random, by_class: dict, paths: dict, data: Path) -> tuple[Image.Image, np.ndarray]:
    chosen = rnd.sample(list(TYPES), rnd.choice([2, 3, 4, 5]))
    seeds = [(rnd.randrange(TILES), rnd.randrange(TILES), chosen[k % len(chosen)]) for k in range(len(chosen) + 2)]
    truth, scene = [], Image.new("RGB", (64 * TILES, 64 * TILES))
    for r in range(TILES):
        for c in range(TILES):
            cls = min(seeds, key=lambda s: (s[0] - r) ** 2 + (s[1] - c) ** 2)[2]
            truth.append(cls)
            with Image.open(data / paths[rnd.choice(by_class[cls])]) as patch:
                scene.paste(patch.convert("RGB"), (c * 64, r * 64))
    return scene, np.array(truth).reshape(TILES, TILES)


def area_error(truth: np.ndarray, predicted: np.ndarray) -> float:
    """Mean gap (percentage points) between each true region's share and its best-matching found region."""
    t_labels, p_labels = np.unique(truth), np.unique(predicted)
    cost = np.array([[-np.sum((truth == t) & (predicted == p)) for p in p_labels] for t in t_labels])
    rows, cols = linear_sum_assignment(cost)
    gaps = [abs(np.mean(truth == t_labels[r]) - np.mean(predicted == p_labels[c])) for r, c in zip(rows, cols)]
    unmatched = [np.mean(truth == t) for i, t in enumerate(t_labels) if i not in rows]
    return float(100 * np.mean(gaps + unmatched))


def as_uploaded(scene: Image.Image, zoom: int) -> Image.Image:
    if zoom > 1:
        scene = scene.resize((scene.width * zoom, scene.height * zoom), Image.Resampling.BICUBIC)
    buffer = io.BytesIO()
    scene.save(buffer, "JPEG", quality=88)
    return Image.open(io.BytesIO(buffer.getvalue())).convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(ROOT / ".data"))
    parser.add_argument("--artifacts-dir", default=str(ROOT / "artifacts"))
    args = parser.parse_args()
    data, artifacts = Path(args.data_dir), Path(args.artifacts_dir)
    split = json.loads((artifacts / "split_manifest.json").read_text())
    labels = json.loads((data / "reference_labels_evaluation_only.json").read_text())
    paths = json.loads((data / "source_manifest_preview_only.json").read_text())
    by_class = {}
    for patch_id in split["holdout_ids"]:
        if labels[patch_id] in TYPES:
            by_class.setdefault(labels[patch_id], []).append(patch_id)

    rnd = random.Random(7)
    scenes = [make_scene(rnd, by_class, paths, data) for _ in range(SCENES)]
    results = {}
    for name, zoom in (("native", 1), ("zoomed_x3", 3)):
        rows = []
        named = right = regions_total = 0
        by_method = {}
        for scene, truth_tiles in scenes:
            mapped = map_regions(as_uploaded(scene, zoom), artifacts)
            grid = mapped["grid"]
            factor = grid["rows"] // TILES
            truth = np.repeat(np.repeat(truth_tiles, factor, axis=0), factor, axis=1).ravel()
            cells = np.array(mapped["cells"])
            rows.append((adjusted_rand_score(truth, cells), area_error(truth, cells), mapped["k"] - len(np.unique(truth))))
            truth_land = np.array([TYPES[c] for c in truth])
            method = mapped["naming"]["method"]
            by_method[method] = by_method.get(method, 0) + 1
            for region in mapped["regions"]:
                regions_total += 1
                if region["name"] == "mixed":
                    continue
                members = truth_land[cells == region["region"]]
                values, counts = np.unique(members, return_counts=True)
                named += 1
                right += values[counts.argmax()] == region["name"]
        r = np.array(rows)
        results[name] = {
            "ari": float(r[:, 0].mean()),
            "area_error_points": float(r[:, 1].mean()),
            "regions_minus_true_types": float(r[:, 2].mean()),
            "named_share": named / regions_total,
            "name_accuracy": right / max(named, 1),
            "scenes_by_naming_method": by_method,
        }
    report = {
        "scenes": SCENES,
        "scene": f"{TILES} x {TILES} held-out EuroSAT patches in blobs of 2-5 of: {', '.join(TYPES)}; uploaded as JPEG quality 88",
        "results": results,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (artifacts / "regions-benchmark.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for name, value in results.items():
        print(f"{name:10s} ARI {value['ari']:.2f} | area error {value['area_error_points']:.1f} pts | regions - true types "
              f"{value['regions_minus_true_types']:+.1f} | named {100*value['named_share']:.0f}%, right {100*value['name_accuracy']:.0f}% | {value['scenes_by_naming_method']}")


if __name__ == "__main__":
    main()
