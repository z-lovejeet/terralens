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
- `GET /capabilities` -> `{max_experiment_samples,live_tsne:true,max_live_tsne_samples,upload_max_bytes,storage,reference_run_id,analysis_runs:string[],crisis_scan:boolean}`. Only bundled analysis runs are selectable.
- `POST /area-check` multipart `file`, optional form `detail:low|medium|high` (default `medium`) -> `{image,grid:{rows,cols},tiles:[{row,col,land_type,shares:{trees,farmland,water,built,bare}}],breakdown:[{land_type,label,tiles,percent}],profile:{headline,green_cover:{percent,label},built_percent,water_percent,considerations:[{topic,tone,text}]},reliability:{level,note},place:{setting,headline,summary,features,quality_notes},method,warnings}`. `land_type` is one of `trees|farmland|water|built|bare|mixed`. Returns 503 when image reading is unavailable and 422 when the reading is incomplete. Images must be 128–4096 px per side and under 8 MB.
- `POST /crisis-scan` multipart `file` -> `{image,assessment:{image_kind,status:crisis|no_crisis|uncertain,crisis_type,secondary_types,severity:none|low|moderate|high|severe,confidence,headline,summary,scene_description,affected_area_percent,regions:[{label,top,left,width,height}],evidence,secondary_risks,actions,cloud_cover,quality_notes,model}|null,vision_error:{message,status}|null,land:{run_id,grid,tiles,breakdown,reliability,groups,method}}`. Region boxes are percentages of the returned image. `assessment` is null with a `vision_error` when the Gemini API is not configured or fails; the land map is still returned.
- `POST /plant-check` multipart `file`, form `area_width:street|colony|neighbourhood|large` (≈200 m, 500 m, 1 km, 3 km; default `colony`) -> `{image,grid,tiles:[{row,col,plantable,trees}],summary:{headline,text,trees_possible,plantable_percent,plantable_m2,tree_cover_now,tree_cover_after,area_width_m,spacing_m},spots:[{number,label,kind,priority:high|medium|low,reason,top,left,width,height,area_m2,trees}],ideas,before_you_plant:[{topic,text}],reliability,quality_notes,method,warnings}`. Trees assume 5 m spacing on 60% of the open ground. 503 when image reading is unavailable, 422 for incomplete readings or an unknown width.
- `POST /change-check` multipart `before` and `after`, optional `detail` -> `{run_id,before_image,after_image,grid,tiles:[{row,col,before,after,change:type|look|none,movement}],summary:{changed_percent,look_changed_percent,level:none|small|noticeable|major},verdict:{story:flood|drying|clearing|construction|regrowth|shift|none,title,explanation,next_steps},deltas:[{land_type,label,before,after,change}],transitions:[{from,to,tiles,percent}],reliability:{before,after},groups,method,warnings}`.

FastAPI serves `/` and built frontend assets if `frontend/dist` exists. Vite dev proxies `/api` to `http://127.0.0.1:8000`. Frontend reads only this contract and must not fabricate fallback numbers if data unavailable.

## ML Python integration
`backend/terralens/features.py`: `extract_features(PIL.Image)->np.ndarray`, `FEATURE_NAMES`, feature dictionary.
`backend/terralens/inference.py`: `analyze_image(image, artifacts_dir, *, comparison=False)->dict` applies saved transforms and ranks reference patches.

`backend/terralens/landscan.py`: `area_check(image, artifacts_dir, detail)` and `change_check(before, after, artifacts_dir, detail)` tile a scene and group every tile with the frozen model; group names come from the post-hoc audit.

`backend/terralens/vision.py`: `assess_crisis(image)->dict` calls the Gemini API with a JSON schema and validates the reply.

`backend/terralens/experiments.py`: `run_experiment(config, artifacts_dir)->dict` fits independently on the compact study feature matrix. The route modules in `backend/terralens/api/` handle the HTTP contract.
`scripts/prepare_study.py`: runnable full download/study command, configurable performance bounds; stores compact inference artifacts and reference JSON in `artifacts/`.
