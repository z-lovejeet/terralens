"""Build the 30-group land model used for everyday land labels.

The 10-group reference model stays the study's headline result. This finer model is
fitted the same unsupervised way (K-Means++ in the frozen 28-component PCA space,
study cohort only) but with 30 groups, so each group is smaller and purer.

Reference labels are opened only AFTER the 30 groups are fixed, to give each group an
everyday name (its most common land type among study patches) and to score the result
on the untouched holdout cohort. They never influence the grouping itself.

Run:  PYTHONPATH=backend .venv/bin/python scripts/build_land_model.py
Needs the prepared study cache in .data/ (scripts/prepare_study.py).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import (
    adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score, normalized_mutual_info_score, silhouette_score,
)

ROOT = Path(__file__).resolve().parents[1]
K = 30
SEED = 42
STABILITY_SEEDS = (42, 17, 91)
MIXED_BELOW = 0.5  # a group whose largest land type is under half of its patches is called "mixed"
LAND_OF_CLASS = {
    "Forest": "trees", "HerbaceousVegetation": "trees",
    "AnnualCrop": "farmland", "PermanentCrop": "farmland", "Pasture": "farmland",
    "River": "water", "SeaLake": "water",
    "Residential": "built", "Industrial": "built", "Highway": "built",
}
LAND_TYPES = ("trees", "farmland", "water", "built")


def name_group(shares: dict[str, float]) -> str:
    """Same naming rule as the app: a clear majority, or the larger of trees/fields when the group is mostly vegetation."""
    top = max(LAND_TYPES, key=shares.get)
    if shares[top] >= MIXED_BELOW:
        return top
    if shares["trees"] + shares["farmland"] >= 0.75:
        return max(("trees", "farmland"), key=shares.get)
    return "mixed"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(ROOT / ".data"))
    parser.add_argument("--artifacts-dir", default=str(ROOT / "artifacts"))
    args = parser.parse_args()
    data, artifacts = Path(args.data_dir), Path(args.artifacts_dir)

    reference = joblib.load(artifacts / "model.joblib")
    split = json.loads((artifacts / "split_manifest.json").read_text())
    with np.load(data / "features_v2.npz", allow_pickle=False) as bundle:
        ids, X = bundle["ids"].astype(str), bundle["X"]
    position = {patch_id: index for index, patch_id in enumerate(ids)}
    study = np.array([position[i] for i in split["study_ids"]])
    holdout = np.array([position[i] for i in split["holdout_ids"]])

    # Same frozen preprocessing as every other part of TerraLens: nothing is refitted here.
    standardized = reference["scaler"].transform(reference["imputer"].transform(X))
    space = reference["pca"].transform(standardized)[:, :reference["components"]]

    # 1. Unsupervised grouping (labels are not loaded yet).
    fits = [KMeans(n_clusters=K, n_init=10, random_state=seed).fit(space[study]) for seed in STABILITY_SEEDS]
    kmeans = fits[0]
    study_groups = kmeans.labels_
    holdout_groups = kmeans.predict(space[holdout])
    stability = float(np.mean([adjusted_rand_score(fits[0].labels_, other.labels_) for other in fits[1:]]))
    sample = np.random.default_rng(SEED).choice(len(study), size=3000, replace=False)
    internal = {
        "silhouette": float(silhouette_score(space[study][sample], study_groups[sample])),
        "davies_bouldin": float(davies_bouldin_score(space[study], study_groups)),
        "calinski_harabasz": float(calinski_harabasz_score(space[study], study_groups)),
        "seed_stability_ari": stability,
    }

    # 2. Post-hoc naming from the evaluation-only labels (study cohort).
    labels = json.loads((data / "reference_labels_evaluation_only.json").read_text())
    classes = np.array([labels[i] for i in ids])
    land = np.array([LAND_OF_CLASS[c] for c in classes])
    groups = {}
    for group in range(K):
        members = land[study][study_groups == group]
        shares = {t: float(np.mean(members == t)) for t in LAND_TYPES}
        top = max(LAND_TYPES, key=shares.get)
        groups[group] = {
            "land_type": name_group(shares),
            "shares": {t: round(v, 4) for t, v in shares.items()},
            "reliability": round(shares[top], 4),
            "count": int(len(members)),
        }

    # 3. Score on the untouched holdout cohort.
    predicted = np.array([groups[int(g)]["land_type"] for g in holdout_groups])
    truth = land[holdout]
    named = predicted != "mixed"
    evaluation = {
        "holdout_patches": int(len(holdout)),
        "accuracy_strict": float(np.mean(predicted == truth)),
        "named_share": float(np.mean(named)),
        "accuracy_when_named": float(np.mean(predicted[named] == truth[named])),
        "recall": {t: float(np.mean(predicted[truth == t] == t)) for t in LAND_TYPES},
        "ari_vs_classes": float(adjusted_rand_score(classes[holdout], holdout_groups)),
        "nmi_vs_classes": float(normalized_mutual_info_score(classes[holdout], holdout_groups)),
        "confusion": {t: {p: int(np.sum((truth == t) & (predicted == p))) for p in (*LAND_TYPES, "mixed")} for t in LAND_TYPES},
    }
    ten = reference["kmeans"].predict(space[holdout])
    audit10 = json.loads((artifacts / "audit.json").read_text())
    names10 = {}
    for row in audit10["contingency"]:
        total = max(row["total"], 1)
        shares = {t: sum(n for c, n in row["counts"].items() if LAND_OF_CLASS[c] == t) / total for t in LAND_TYPES}
        names10[int(row["cluster"])] = name_group(shares)
    predicted10 = np.array([names10[int(g)] for g in ten])
    evaluation["reference_10_groups"] = {
        "accuracy_strict": float(np.mean(predicted10 == truth)),
        "named_share": float(np.mean(predicted10 != "mixed")),
        "accuracy_when_named": float(np.mean(predicted10[predicted10 != "mixed"] == truth[predicted10 != "mixed"])),
    }

    distances = np.linalg.norm(space[study] - kmeans.cluster_centers_[study_groups], axis=1)
    run_id = f"land-k{K}-s{SEED}"
    bundle = {
        "run_id": run_id,
        "base_run_id": reference["reference_run_id"],
        "components": reference["components"],
        "kmeans": kmeans,
        "groups": groups,
        "cluster_distances": {g: np.sort(distances[study_groups == g]) for g in range(K)},
        "feature_names": reference["feature_names"],
        "archive_sha256": reference["archive_sha256"],
    }
    joblib.dump(bundle, artifacts / "land-model.joblib", compress=3)
    audit = {
        "run_id": run_id,
        "base_run_id": reference["reference_run_id"],
        "k": K,
        "seed": SEED,
        "mixed_below": MIXED_BELOW,
        "disclosure": "Groups were fitted without labels. Reference labels were opened afterwards only to name each group "
                      "(its most common land type among study patches) and to score the holdout cohort.",
        "internal_metrics": internal,
        "evaluation": evaluation,
        "groups": groups,
        "land_model_sha256": hashlib.sha256((artifacts / "land-model.joblib").read_bytes()).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (artifacts / "land-model-audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    print(f"{run_id}: silhouette {internal['silhouette']:.3f}, DB {internal['davies_bouldin']:.2f}, seed ARI {stability:.3f}")
    print(f"holdout accuracy: strict {100 * evaluation['accuracy_strict']:.1f}% | named {100 * evaluation['named_share']:.1f}% "
          f"of patches, {100 * evaluation['accuracy_when_named']:.1f}% right when named")
    print("recall:", {t: round(100 * v, 1) for t, v in evaluation["recall"].items()})
    r10 = evaluation["reference_10_groups"]
    print(f"10-group reference for comparison: strict {100 * r10['accuracy_strict']:.1f}% | named {100 * r10['named_share']:.1f}%, "
          f"{100 * r10['accuracy_when_named']:.1f}% when named")
    print("mixed groups:", [g for g, v in groups.items() if v["land_type"] == "mixed"])


if __name__ == "__main__":
    main()
