# TerraLens: Testing and Installation Guide (for the evaluator)

**Project:** Unsupervised Land-Type Grouping of Satellite Image Patches Using Clustering
**Course / ID:** INT396 Unsupervised Learning, SIH26142 · Lovely Professional University
**Team:** Lovejeet Singh (12521613), Mohammad Asim (12518421), Reshu Kumar (12508208)

This guide takes about **10 minutes**. Everything runs on your own computer: **no API key, no account and no internet connection are needed** after the packages are installed. The application makes no calls to any outside service.

| Link | Address |
| :--- | :--- |
| Live demo (no installation needed) | <https://terralens-slek.onrender.com> |
| Source code | <https://github.com/z-lovejeet/terralens> |
| Dataset (EuroSAT RGB, 27,000 patches) | <https://www.kaggle.com/datasets/apollo2506/eurosat-dataset> |

> The live demo runs on a free server that sleeps when idle, so the **first page load can take up to a minute**. Running it locally (below) is instant.

---

## 1. What is inside this folder

| Path | Content |
| :--- | :--- |
| `backend/terralens/` | Python (FastAPI) server and all machine-learning code (features, PCA, t-SNE, K-Means, Map my image, Sort my photos) |
| `frontend/src/` | React + TypeScript interface source; `frontend/dist/` is the **ready-built interface** (so Node.js is not needed to run it) |
| `artifacts/` | The fitted models and saved study results (scaler, PCA, K-Means, 30-group land model, audit, thumbnails) |
| `tests/` | 52 automated tests |
| `examples/` | Ready-made images to try each tool, with answer keys |
| `scripts/` | Setup/start scripts and the scripts that rebuild the study, models and deliverables |
| `docs/`, `README.md` | Full documentation, methodology and diagrams |
| `Dockerfile`, `requirements*.txt` | Container definition and exact pinned Python packages |

---

## 2. Requirements

* **Python 3.12** (recommended; the pinned packages are tested on it). Python 3.13 also works on macOS/Linux/Windows if 3.12 is unavailable.
* About 1.5 GB of free disk space and 4 GB of RAM.
* Node.js is **optional**: only needed to rebuild the interface (Option B).

---

## 3. Install and run (Option A, fastest: Python only)

Open a terminal **inside the unzipped `TerraLens` folder**.

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
PYTHONPATH=backend python -m uvicorn terralens.app:app --host 127.0.0.1 --port 8000
```

**Windows (Command Prompt)**
```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.lock.txt
set PYTHONPATH=backend
python -m uvicorn terralens.app:app --host 127.0.0.1 --port 8000
```

Then open **<http://127.0.0.1:8000>** in a browser. Stop the server with `Ctrl + C`.
If port 8000 is busy, use another number (for example `--port 8010`) and open that address instead.

### Option B: one-command scripts (also rebuilds the interface, needs Node.js 20.19+)

```bash
./scripts/setup.sh        # Windows: .\scripts\setup.bat
./scripts/start.sh        # Windows: .\scripts\start.bat
```

### Option C: Docker

```bash
docker build -t terralens .
docker run --rm -p 8000:8000 terralens
```
Open <http://localhost:8000>.

---

## 4. Check that it works (2 minutes)

1. Open <http://127.0.0.1:8000/api/health>. It should show `{"status":"ok","study_ready":true,...}`.
2. Open <http://127.0.0.1:8000>. The **Observatory** page loads, with *27,000 observations* in the left sidebar.
3. Interactive API documentation is at <http://127.0.0.1:8000/docs>.

---

## 5. Try every feature with the included examples

| Page (left menu) | What to do | What you should see |
| :--- | :--- | :--- |
| **Map my image** | Upload `examples/map-my-image/demo-scene.jpg`, leave *Number of regions* on *Auto* | **4 regions** found by itself and named by the land model: Trees ≈ 37%, Water ≈ 26%, Buildings ≈ 19%, Fields ≈ 18%, with an elbow chart and the measured accuracy panel |
| **Sort my photos** | Click *Choose a folder* and pick `examples/sort-my-photos/` (30 images), leave groups on *Auto*, click *Sort photos* | **5 groups**, about 83% pure (compare with `answer_key.csv`); switch to the *Land type* view |
| **Patch analyzer** | Upload `examples/demo-patch-01.jpg` (expected Group 10, residential) or `examples/demo-patch-02.jpg` (expected Group 04, river), or click a bundled test patch | Assigned group, distance to every group center, runner-up margin and the nearest reference patches |
| **Cluster atlas** | Click through the 10 discovered groups | Typical patches, numerical portrait and PCA location of each group (reference labels stay hidden) |
| **Model lab** | Open the three tabs | *Manifold Projections* (PCA vs t-SNE side by side), *Clustering Benchmarks* (K-Means results and experiments), *Methodology & Reference Audit* (sealed post-hoc audit) |
| **Observatory** | Toggle *All / Study / Holdout* | Class distribution of all 27,000 patches and the 10 discovered groups |

Any top-down satellite image (JPEG, PNG or WebP, at least 128 pixels per side) can be uploaded to *Map my image*; a screenshot from a map application also works. For close-up screenshots the region names are produced by colour-and-texture rules and are marked "best guess" when uncertain (see the README).

---

## 6. Run the automated tests (52 tests)

With the virtual environment active (Option A), install the test tools and run:

```bash
pip install -r requirements-dev.lock.txt
python -m pytest -q
```

Expected result: **`52 passed`** (about 10 seconds; no internet needed). The tests check feature determinism, label isolation (no class label reaches any fitting step), PCA/t-SNE/K-Means invariants and saved-model reuse, the REST API and upload limits, the 30-group land model, Map my image, Sort my photos, and that **no application code uses a network client or an API key**.

---

## 7. Where the project objectives are demonstrated

| Objective | Where to look |
| :--- | :--- |
| 1. Prepare the data with labels hidden: features, missing values, encoding, scaling | `README.md` sections *Data Hygiene & Label-Quarantine Protocol* and *Feature Engineering*; `backend/terralens/features.py`, `study.py`; the **Observatory** page |
| 2. PCA and t-SNE, retained variance, 2-D structure, K-Means on PCA features | **Model lab → Manifold Projections** and **Clustering Benchmarks**; `README.md` sections on PCA, t-SNE and clustering; IEEE paper |
| 3. Interpretation: explained variance, feature contributions, parameter sensitivity, limitations, bias, ethics | **Model lab → Methodology & Reference Audit**, **Cluster atlas**; `README.md` sections on validation, audit and limitations; report and IEEE paper |

Extra tools built on the same frozen models: **Map my image**, **Sort my photos** and a finer 30-group land model. Everything is unsupervised machine learning; **no external API or pretrained model is used**.

---

## 8. Optional: rebuild the study from scratch

Not needed for evaluation (all results and fitted models are included in `artifacts/`). To reproduce them, `PYTHONPATH=backend python scripts/prepare_study.py` downloads the public EuroSAT archive (about 2 GB, 5 to 10 minutes) and refits the scaler, PCA, t-SNE and K-Means with fixed seeds. `scripts/build_land_model.py` and `scripts/benchmark_regions.py` rebuild the 30-group model and the Map my image benchmark.

---

## 9. Troubleshooting

| Problem | Fix |
| :--- | :--- |
| `pip install` fails on an old or very new Python | Use Python 3.12 (for example install it with [uv](https://docs.astral.sh/uv/): `uv venv --python 3.12 .venv`) |
| `ModuleNotFoundError: terralens` | Set `PYTHONPATH=backend` as shown (the start scripts do it for you), and run from the `TerraLens` folder |
| Blank page or "Waiting for the observations" | The server is not running, or `frontend/dist` is missing: run Option B or `npm --prefix frontend ci && npm --prefix frontend run build` |
| `Address already in use` | Choose another port with `--port` |
| Windows blocks `.ps1` scripts | Use the Command Prompt commands or the `.bat` scripts |
| First request is slow | The first request loads the models into memory; later requests are fast |

Full installation notes for macOS, Linux, Windows and Docker, with more detail, are in `README.md` (section *Installation & Setup Instructions*).
