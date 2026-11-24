export type View = 'observatory' | 'regions' | 'sort' | 'analyzer' | 'clusters' | 'diagnostics';
export interface PatchContext { runId: string; clusterId?: number; run?: Run; point?: Point; source?: 'live' }
export type XY = [number, number];
export interface Point { id: string; pca: XY; tsne?: XY; cluster: number }
export interface Feature { name: string; value: number; zscore: number }

export type LandType = 'trees' | 'farmland' | 'water' | 'built' | 'bare' | 'mixed';

export interface LandShare { land_type: LandType; label: string; tiles: number; percent: number }
export interface SceneReliability { level: 'high' | 'medium' | 'low'; unusual_percent: number; mixed_percent: number; note: string }
export interface GroupName { cluster: number; land_type: LandType; reliability: number }

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

export interface SortGroup { group: number; size: number; members: number[]; land_type: LandType; land_share: number; land_counts: Partial<Record<LandType, number>>; description: string[]; spread: number }
export interface SortPhoto { index: number; name: string; group: number; land_type: LandType; distance: number; outlier: boolean; unfamiliar: boolean; pca: XY }
export interface SortResult {
  photo_count: number;
  k: number;
  chosen: 'automatic' | 'you';
  silhouette: number | null;
  davies_bouldin: number | null;
  separation: 'clear' | 'moderate' | 'weak';
  candidates: { k: number; inertia: number; silhouette: number }[];
  groups: SortGroup[];
  photos: SortPhoto[];
  unfamiliar_percent: number;
  land_run_id: string;
  method: string;
}

export type NamingMethod = 'land model' | 'colour and texture';
export interface MapRegion {
  region: number; letter: string; share: number; cells: number; description: string[];
  name: LandType; named_by: NamingMethod; confidence: 'high' | 'medium' | 'low'; model_agreement: number | null;
}
export interface MapResult {
  image: string;
  grid: { rows: number; cols: number };
  cells: number[];
  k: number;
  chosen: 'automatic' | 'you';
  regions: MapRegion[];
  candidates: { k: number; inertia: number; silhouette: number }[];
  silhouette: number | null;
  separation: 'clear' | 'moderate' | 'weak';
  unfamiliar_percent: number;
  warnings: string[];
  accuracy: { scenes: number; ari: number; area_error_points: number; name_accuracy: number; named_share: number; zoomed_ari: number;
    colour_texture: { views: number; regions: number; accuracy: number; area_accuracy: number; clear_accuracy: number } } | null;
  naming: { method: NamingMethod; unfamiliar_percent: number };
  land_cover: { name: LandType; share: number }[];
  method: string;
}
