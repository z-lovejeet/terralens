export type View = 'observatory' | 'radar' | 'area' | 'plant' | 'analyzer' | 'clusters' | 'diagnostics';
export interface PatchContext { runId: string; clusterId?: number; run?: Run; point?: Point; source?: 'live' }
export type XY = [number, number];
export interface Point { id: string; pca: XY; tsne?: XY; cluster: number }
export interface Feature { name: string; value: number; zscore: number }

export type LandType = 'trees' | 'farmland' | 'water' | 'built' | 'bare' | 'mixed';
export type Detail = 'low' | 'medium' | 'high';

export interface LandShare { land_type: LandType; label: string; tiles: number; percent: number }
export interface SceneReliability { level: 'high' | 'medium' | 'low'; unusual_percent: number; mixed_percent: number; note: string }
export interface GroupName { cluster: number; land_type: LandType; reliability: number }

export interface AreaTile { row: number; col: number; land_type: LandType; cluster: number; unusual: boolean }
export interface AreaProfile {
  headline: string;
  green_cover: { percent: number; label: 'High' | 'Good' | 'Moderate' | 'Low' };
  built_percent: number;
  water_percent: number;
  considerations: { topic: string; tone: 'good' | 'watch' | 'info'; text: string }[];
}
export interface ModelLand {
  run_id: string;
  grid: { rows: number; cols: number };
  tiles: AreaTile[];
  breakdown: LandShare[];
  reliability: SceneReliability;
  groups: GroupName[];
  method: string;
}
export interface AreaCell { row: number; col: number; land_type: LandType; shares: Record<Exclude<LandType, 'mixed'>, number> }
export interface AreaResult {
  image: string;
  grid: { rows: number; cols: number };
  tiles: AreaCell[];
  breakdown: LandShare[];
  profile: AreaProfile;
  reliability: { level: 'high' | 'medium' | 'low'; note: string };
  place: { setting: string; headline: string; summary: string; features: string[]; quality_notes: string[] };
  method: string;
  warnings: string[];
}

export type Severity = 'none' | 'low' | 'moderate' | 'high' | 'severe';
export interface CrisisAssessment {
  image_kind: 'satellite' | 'aerial' | 'ground_photo' | 'map_or_graphic' | 'other';
  status: 'crisis' | 'no_crisis' | 'uncertain';
  crisis_type: string;
  secondary_types: string[];
  severity: Severity;
  confidence: number | null;
  headline: string;
  summary: string;
  scene_description: string;
  affected_area_percent: number | null;
  regions: { label: string; top: number; left: number; width: number; height: number }[];
  evidence: string[];
  secondary_risks: string[];
  actions: string[];
  cloud_cover: 'none' | 'some' | 'heavy';
  quality_notes: string[];
  model: string;
}
export interface CrisisScanResult {
  image: string;
  assessment: CrisisAssessment | null;
  vision_error: { message: string; status: number } | null;
  land: ModelLand;
}

export interface ChangeTile { row: number; col: number; before: LandType; after: LandType; change: 'type' | 'look' | 'none'; movement: number }
export interface ChangeCheckResult {
  run_id: string;
  before_image: string;
  after_image: string;
  grid: { rows: number; cols: number };
  tiles: ChangeTile[];
  summary: { changed_percent: number; look_changed_percent: number; level: 'none' | 'small' | 'noticeable' | 'major' };
  verdict: { story: string; title: string; explanation: string; next_steps: string[] };
  deltas: { land_type: LandType; label: string; before: number; after: number; change: number }[];
  transitions: { from: LandType; to: LandType; tiles: number; percent: number }[];
  reliability: { before: SceneReliability; after: SceneReliability };
  groups: GroupName[];
  method: string;
  warnings: string[];
}

export interface AnomalyInfo {
  is_anomaly: boolean;
  status: 'NORMAL' | 'BORDERLINE' | 'ANOMALY_DETECTED';
  score: number;
  description: string;
}
export interface Metrics {
  silhouette: number | null;
  davies_bouldin: number | null;
  calinski_harabasz: number | null;
  inertia: number | null;
  silhouette_original: number | null;
}
export interface Cluster {
  id: number; count: number; name?: string; description: string; representatives: string[];
  boundary_samples: string[]; feature_profile: Feature[];
}
export interface Run {
  id: string; k: number; variance: number | null; components: number; seed: number;
  metrics: Metrics; runtime_seconds: number; stability: number | null; clusters: Cluster[];
  selection_reason?: string; holdout_metrics?: Record<string, number | null>;
}
export interface TSNERun {
  id: string; perplexity: number; seed: number; trustworthiness: number;
  runtime_seconds: number; points: XY[];
}
export interface ScreeningRun { k: number; variance: number | null; components: number; seed: number; metrics: Metrics; runtime_seconds: number; sample_size: number }
export interface StudyExperiments { screening?: ScreeningRun[]; screening_sample_size?: number; full_metric_sample_size?: number; ablations?: { name: string; k: number; components: number; metrics: Metrics; runtime_seconds: number }[]; reconstruction?: { variance: number; components: number; study_mse: number; holdout_mse: number }[]; comparison_rules?: string[]; units?: Record<string, string> }
export interface Study {
  project: { name: string; title: string; problem_id: string; course: string };
  dataset: { name: string; source_url: string; total_images: number; valid_images: number; image_width: number; image_height: number; channels: number; archive_sha256: string };
  preprocessing: { description: string; scaling: string; missing_value_policy: string; categorical_encoding: string; label_policy: string };
  split: { study_count: number; holdout_count: number; seed: number };
  quality: { unreadable_images: number; duplicate_images: number; missing_values: number; constant_features: number | string[]; notes: string[] };
  feature_names: string[];
  feature_families: { name: string; count: number; description: string }[];
  pca: { explained_variance_ratio: number[]; cumulative_variance: number[]; thresholds: { variance: number; components: number }[]; loadings: { component: number; features: { name: string; loading: number }[] }[]; pca2_trustworthiness?: number };
  selected_run_id: string;
  runs: Run[];
  points: Point[];
  tsne_runs: TSNERun[];
  experiments: StudyExperiments;
  limitations: string[];
  provenance: { created_at: string; seed: number; versions: Record<string, string>; selection_rule: string; metric_space: string; visual_sample_size: number; notes: string[] };
}
export interface Capabilities {
  max_experiment_samples: number;
  max_live_tsne_samples?: number;
  live_tsne: boolean;
  upload_max_bytes: number;
  storage: string;
  reference_run_id: string;
  analysis_runs?: string[];
  crisis_scan?: boolean;
}
export type LivePerplexity = 10 | 30 | 50;
export interface ExperimentConfig {
  k: number;
  variance: number;
  seed: number;
  sample_size: number;
  tsne_perplexity?: LivePerplexity | null;
}
export interface ExperimentResult extends Run {
  points: Point[];
  retained_variance?: number;
  tsne?: { perplexity: number; trustworthiness: number; runtime_seconds: number } | null;
}
export interface Experiment {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  stage?: string;
  config: ExperimentConfig;
  result?: ExperimentResult;
  error?: string;
  created_at?: string;
}
export interface Analysis {
  run_id?: string;
  cluster: number;
  cluster_name?: string;
  cluster_description?: string;
  cohort_clusters?: number[];
  pca: XY;
  distance: number;
  relative_distance: number | null;
  reference_percentile: number;
  anomaly?: AnomalyInfo;
  alternate_cluster?: number | null;
  alternate_distance?: number | null;
  margin?: number | null;
  neighbors?: { id: string; distance: number }[];
  neighbor_scope?: number;
  representatives: string[];
  features: Feature[];
  warnings: string[];
}
export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

export type AreaWidth = 'street' | 'colony' | 'neighbourhood' | 'large';
export interface PlantSpot { number: number; label: string; kind: string; priority: 'high' | 'medium' | 'low'; reason: string; top: number; left: number; width: number; height: number; area_m2: number; trees: number }
export interface PlantResult {
  image: string;
  grid: { rows: number; cols: number };
  tiles: { row: number; col: number; plantable: number; trees: number }[];
  summary: { headline: string; text: string; trees_possible: number; plantable_percent: number; plantable_m2: number; tree_cover_now: number; tree_cover_after: number; area_width_m: number; spacing_m: number };
  spots: PlantSpot[];
  ideas: string[];
  before_you_plant: { topic: string; text: string }[];
  reliability: { level: 'high' | 'medium' | 'low'; note: string };
  quality_notes: string[];
  method: string;
  warnings: string[];
}
