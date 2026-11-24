# API contract v1

All routes under `/api`. JSON numbers are finite or null. No class labels in fitting or default dataset responses. The immutable reference bundle is `artifacts/study.json`. The label audit is separate `artifacts/audit.json`. Anonymous preview images live in `artifacts/thumbnails/{id}.jpg`.

## GET /study
Returns `{project, dataset, preprocessing, split, quality, feature_names, feature_families, pca, selected_run_id, runs, points, tsne_runs, experiments, limitations, provenance}`.

- `project`: `{name,title,problem_id,course}`.
- `dataset`: `{name,source_url,total_images,valid_images,image_width,image_height,channels,archive_sha256}`.
- `split`: `{study_count,holdout_count,seed}`.
- `quality`: `{unreadable_images,duplicate_images,missing_values,constant_features,notes:string[]}`.
- `preprocessing`: `{description,scaling,missing_value_policy,categorical_encoding,label_policy}`.
- `feature_names`: string[]. `feature_families`: `[{name,count,description}]`.
- `pca`: `{explained_variance_ratio:number[],cumulative_variance:number[],thresholds:[{variance,components}],loadings:[{component,features:[{name,loading}]}]}`.
- `runs`: `[{id,k,variance:number|null,components,seed,metrics:{silhouette,davies_bouldin,calinski_harabasz,inertia,silhouette_original},runtime_seconds,stability:number|null,clusters:[{id,count,description,representatives:string[],boundary_samples:string[],feature_profile:[{name,value,zscore}]}],selection_reason?:string,holdout_metrics?:object}]`.
- `points`: `[{id,pca:[number,number],tsne:[number,number],cluster:number}]`; same order/IDs used for all t-SNE runs, reference run cluster assignments.
- `tsne_runs`: `[{id,perplexity,seed,trustworthiness,runtime_seconds,points:[number,number][]}]`.
- `experiments`: free structured JSON of ablations and sensitivity tables with declared units/spaces.
- `provenance`: `{created_at,seed,versions,selection_rule,metric_space,visual_sample_size,notes:string[]}`.
- `limitations`: string[].

## Other endpoints
- `GET /health` -> `{status,study_ready,version}`.
- `GET /patches/{id}.jpg` -> anonymous JPEG, or 404.
- `GET /audit` -> separate frozen study 10-group audit JSON (reference labels used only after fitting and selection).
- `GET /features` -> `{features:[{name,family,description}], ...}`.
- `POST /experiments` body `{k:2..15,variance:0.9|0.95|0.99,seed:0..9999,sample_size:200..3000,tsne_perplexity:10|30|50|null}` -> `{id,status}`. Backend may cap hosted samples, explicitly advertise in `/capabilities`.
- `GET /experiments/{id}` -> `{id,status:queued|running|completed|failed,stage,config,result?:{...run,points:[{id,pca,cluster,tsne?}],tsne?:{perplexity,trustworthiness,runtime_seconds},...},error?:string}`. An optional new t-SNE fit runs on the same retained PCA features and uses the same point IDs and existing K-Means group colours.
- `GET /experiments` -> `{experiments:[job...]}` newest first.
- `POST /analyze` multipart `file` and optional `?run_id=pca95-k10-s42` -> `{run_id,cluster,cluster_description,pca:[x,y],distance,alternate_cluster,alternate_distance,margin,relative_distance,reference_percentile,representatives:string[],neighbors:[{id,distance}],neighbor_scope,features:[{name,value,zscore}],warnings:string[],cohort_clusters?:number[]}`. The reference run is the default. The comparison returns `cohort_clusters` in the order of `study.points`. Distances and neighbors use the full retained PCA space. Neighbors are ranked within the assigned group of the bundled preview cohort. The browser can export this response as JSON without the input image.
- `GET /export/study.json`, `/export/metrics.csv`, `/export/config.json` -> downloadable recorded data. `GET /export/experiments/{id}.json` downloads a runtime job record.
- `GET /capabilities` -> `{max_experiment_samples,live_tsne:true,max_live_tsne_samples,upload_max_bytes,storage,reference_run_id,analysis_runs:string[]}`. Only bundled analysis runs are selectable.
- `POST /map-regions` multipart `file` (≥ 128 px, < 8 MB), form `count:auto|2..8` -> `{image,grid:{rows,cols},cells:number[],k,chosen:automatic|you,regions:[{region,letter,share,cells,description:string[],name,named_by:land model|colour and texture,confidence:high|medium|low,model_agreement:number|null}],candidates:[{k,inertia,silhouette}],silhouette,separation:clear|moderate|weak,unfamiliar_percent,warnings,accuracy:{scenes,ari,area_error_points,name_accuracy,named_share,zoomed_ari,colour_texture:{views,regions,accuracy,area_accuracy,clear_accuracy}}|null,naming:{method,unfamiliar_percent},land_cover:[{name,share}],method}`. Squares are clustered in a per-image standardised (capped) PCA space; `name` is one of trees, farmland, water, built, bare, mixed. Regions are named by the 30-group land model (`confidence: high`, `mixed` when no land type covers half the region) unless 30 % or more of its squares look unlike the training imagery; then `naming.method` is `colour and texture` and each region is read from greenness, brightness, smoothness, field rows and darkness (`confidence: medium`, or `low` for a best guess). `land_cover` sums region shares by name, largest first. A uniform image returns 422. `cells` gives each square's region in row order; regions are lettered largest first.
- `POST /sort-photos` multipart `files` (4–300 images, each ≥ 32 px and < 8 MB), form `groups:auto|2..12` -> `{photo_count,k,chosen:automatic|you,silhouette,davies_bouldin,separation:clear|moderate|weak,candidates:[{k,silhouette}],groups:[{group,size,members:number[],land_type,land_share,land_counts,description:string[],spread}],photos:[{index,name,group,land_type,distance,outlier,unfamiliar,pca:[x,y]}],unfamiliar_percent,land_run_id,method}`. `members` are photo indices in upload order, most typical first. Groups are ordered largest first.

FastAPI serves `/` and built frontend assets if `frontend/dist` exists. Vite dev proxies `/api` to `http://127.0.0.1:8000`. Frontend reads only this contract and must not fabricate fallback numbers if data unavailable.

## ML Python integration
`backend/terralens/features.py`: `extract_features(PIL.Image)->np.ndarray`, `FEATURE_NAMES`, feature dictionary.
`backend/terralens/inference.py`: `analyze_image(image, artifacts_dir, *, comparison=False)->dict` applies saved transforms and ranks reference patches.

`backend/terralens/landmodel.py`: `classify_features(raw, artifacts_dir)` projects descriptor rows with the frozen scaler and PCA and labels them with the 30-group land model (`artifacts/land-model.joblib`); group names come from the post-hoc land-model audit.

`backend/terralens/regions.py`: `map_regions(image, artifacts_dir, requested_k)` clusters the squares of one image with K-Means++ and the elbow method after standardising them within the image; the frozen study models supply descriptions and land-model names, and `reading.py` names regions of images unlike the training data from colour and texture.

`backend/terralens/sorting.py`: `sort_photos(photos, artifacts_dir, requested_k)` clusters uploaded images in the frozen PCA space with K-Means++ and automatic K. The application makes no outside network calls.


`backend/terralens/experiments.py`: `run_experiment(config, artifacts_dir)->dict` fits independently on the compact study feature matrix. The route modules in `backend/terralens/api/` handle the HTTP contract.
`scripts/prepare_study.py`: runnable full download/study command, configurable performance bounds; stores compact inference artifacts and reference JSON in `artifacts/`.
