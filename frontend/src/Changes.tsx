import { useEffect, useState } from 'react';
import { ArrowClockwise, ArrowRight, CheckCircle, ClockClockwise, DownloadSimple, Info, ShieldWarning, Sparkle, UploadSimple, Warning } from '@phosphor-icons/react';
import { downloadJson, format, request } from './api';
import { Notice, Panel } from './UI';
import type { ChangeResult, Study } from './types';

interface ChangePreset {
  id: string;
  title: string;
  location: string;
  description: string;
}

export default function Changes({ study: _study }: { study?: Study }) {
  const [presets, setPresets] = useState<ChangePreset[]>([]);
  const [activePreset, setActivePreset] = useState<string>('deforestation');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<ChangeResult | null>(null);
  const [error, setError] = useState<string>('');
  const [beforeFile, setBeforeFile] = useState<File | null>(null);
  const [afterFile, setAfterFile] = useState<File | null>(null);

  useEffect(() => {
    request<ChangePreset[]>('/change/presets')
      .then(data => setPresets(data))
      .catch(() => {});
    executeChangeDetection('deforestation', null, null);
  }, []);

  const executeChangeDetection = async (
    presetId: string | null,
    bFile: File | null,
    aFile: File | null,
  ) => {
    setLoading(true);
    setError('');
    try {
      const formData = new FormData();
      if (bFile && aFile) {
        formData.append('before_file', bFile);
        formData.append('after_file', aFile);
      } else if (presetId) {
        formData.append('preset_id', presetId);
      }

      const res = await fetch('/api/change', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Change analysis failed with status ${res.status}`);
      }
      const data: ChangeResult = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || 'Failed to detect temporal change.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (id: string) => {
    setActivePreset(id);
    setBeforeFile(null);
    setAfterFile(null);
    executeChangeDetection(id, null, null);
  };

  const handleCustomUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (beforeFile && afterFile) {
      setActivePreset('');
      executeChangeDetection(null, beforeFile, afterFile);
    }
  };

  const currentPresetMeta = presets.find(p => p.id === activePreset);

  return (
    <div className="view-panel changes-view">
      <div className="view-header">
        <div className="view-header-title">
          <span className="badge badge-primary"><ClockClockwise size={14} weight="bold" /> Real-World Applied Core</span>
          <h1>Temporal Change & Deforestation Detector</h1>
          <p className="lead">
            Compare multi-temporal satellite passes of the same region to quantify land-use transitions, spectral drift, and environmental degradation.
          </p>
        </div>
      </div>

      {/* Preset selector */}
      <Panel title="Environmental Monitoring Scenario" className="changes-controls-panel">
        <div className="changes-controls-header">
          <div>
            <span className="workspace-label">Environmental Monitoring Scenario</span>
            <h3>Select a Verified Case Study or Upload Dual-Pass Imagery</h3>
          </div>
          <button
            className="button button-primary"
            disabled={loading}
            onClick={() => executeChangeDetection(activePreset || null, beforeFile, afterFile)}
          >
            <ArrowClockwise size={16} className={loading ? 'is-spinning' : ''} />
            <span>{loading ? 'Analyzing Transition...' : 'Run Change Detection'}</span>
          </button>
        </div>

        <div className="preset-chips-grid">
          {presets.map(p => (
            <button
              key={p.id}
              className={`preset-chip ${activePreset === p.id ? 'is-active' : ''}`}
              onClick={() => handleSelectPreset(p.id)}
            >
              <span className="preset-chip-title">{p.title}</span>
              <small className="preset-chip-location">{p.location}</small>
            </button>
          ))}
        </div>

        {currentPresetMeta && (
          <p className="preset-description-text">
            <Info size={16} /> <strong>{currentPresetMeta.location}:</strong> {currentPresetMeta.description}
          </p>
        )}

        {/* Custom Uploads Accordion */}
        <div className="custom-pair-upload-box">
          <span className="workspace-label">Or Compare Custom Satellite Passes</span>
          <div className="dual-upload-inputs">
            <label className="file-input-wrapper">
              <span>Time 1 (Before):</span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={e => setBeforeFile(e.target.files?.[0] || null)}
              />
            </label>
            <label className="file-input-wrapper">
              <span>Time 2 (After):</span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={e => setAfterFile(e.target.files?.[0] || null)}
              />
            </label>
            <button
              className="button button-secondary"
              disabled={!beforeFile || !afterFile || loading}
              onClick={handleCustomUpload}
            >
              <UploadSimple size={16} />
              <span>Compare Uploaded Pair</span>
            </button>
          </div>
        </div>
      </Panel>

      {error && <Notice warning>{error}</Notice>}

      {/* Results view */}
      {result && (
        <div className="changes-results-container">
          {/* Alert Status Banner */}
          <div className={`change-alert-banner alert-${result.alert.level.toLowerCase()}`}>
            <div className="alert-banner-icon">
              {result.alert.level === 'CRITICAL' ? (
                <ShieldWarning size={32} weight="fill" />
              ) : result.alert.level === 'WARNING' ? (
                <Warning size={32} weight="fill" />
              ) : (
                <CheckCircle size={32} weight="fill" />
              )}
            </div>
            <div className="alert-banner-content">
              <div className="alert-level-pill">
                <strong>{result.alert.level} STATUS</strong> · {result.alert.title}
              </div>
              <p className="alert-narrative-text">{result.alert.narrative}</p>
              <div className="alert-recommendation">
                <Sparkle size={15} weight="fill" />
                <strong>Recommended Operational Action:</strong> {result.alert.recommendation}
              </div>
            </div>
          </div>

          {/* Visual Pair Comparison */}
          <div className="visual-transition-grid">
            {/* Before Pass */}
            <Panel title="Time 1 Baseline Pass" className="transition-card before-card">
              <div className="transition-header">
                <span className="time-badge">Time 1 · Baseline Pass</span>
                <span className="color-dot" style={{ backgroundColor: result.before.color }} />
              </div>
              <div className="transition-image-wrapper">
                <img src={result.before.image_base64} alt="Before pass satellite patch" width="160" height="160" />
              </div>
              <div className="transition-meta">
                <h3>{result.before.cluster_name}</h3>
                <small>Assigned Group {String(result.before.cluster + 1).padStart(2, '0')}</small>
                <div className="transition-pca-coords">
                  <span>Centroid distance: <code>{format(result.before.distance)}</code></span>
                  <span>PCA: [<code>{format(result.before.pca[0])}</code>, <code>{format(result.before.pca[1])}</code>]</span>
                </div>
              </div>
            </Panel>

            {/* Transition Center Indicator */}
            <div className="transition-center-indicator">
              <div className="drift-badge">
                <span className="drift-label">28-PC Drift</span>
                <span className="drift-value">{format(result.pca_distance)}</span>
              </div>
              <div className="transition-arrow-circle">
                <ArrowRight size={24} weight="bold" />
              </div>
              <span className="transition-label">Multi-temporal Shift</span>
            </div>

            {/* After Pass */}
            <Panel title="Time 2 Recent Pass" className="transition-card after-card">
              <div className="transition-header">
                <span className="time-badge">Time 2 · Recent Pass</span>
                <span className="color-dot" style={{ backgroundColor: result.after.color }} />
              </div>
              <div className="transition-image-wrapper">
                <img src={result.after.image_base64} alt="After pass satellite patch" width="160" height="160" />
              </div>
              <div className="transition-meta">
                <h3>{result.after.cluster_name}</h3>
                <small>Assigned Group {String(result.after.cluster + 1).padStart(2, '0')}</small>
                <div className="transition-pca-coords">
                  <span>Centroid distance: <code>{format(result.after.distance)}</code></span>
                  <span>PCA: [<code>{format(result.after.pca[0])}</code>, <code>{format(result.after.pca[1])}</code>]</span>
                </div>
              </div>
            </Panel>
          </div>

          {/* Telemetry Drift Metrics */}
          <Panel title="Spectral & Texture Telemetry Drift" className="drift-metrics-panel">
            <div className="drift-metrics-header">
              <div>
                <span className="workspace-label">Spectral & Texture Telemetry Drift</span>
                <h3>Measured Feature Shift Between Passes</h3>
              </div>
              <button
                className="button button-small button-ghost"
                onClick={() => downloadJson(result, 'terralens-change-report.json')}
              >
                <DownloadSimple size={16} />
                <span>Export Change Report</span>
              </button>
            </div>

            <div className="drift-metrics-grid">
              <div className="drift-metric-card">
                <span className="metric-title">Chlorophyll Greenness Δ</span>
                <strong className={`metric-value ${result.deltas.greenness < 0 ? 'is-negative' : 'is-positive'}`}>
                  {result.deltas.greenness > 0 ? '+' : ''}{result.deltas.greenness}%
                </strong>
                <small>Green channel reflectance & circular hue</small>
              </div>

              <div className="drift-metric-card">
                <span className="metric-title">Surface Albedo Δ</span>
                <strong className={`metric-value ${result.deltas.albedo > 20 ? 'is-elevated' : ''}`}>
                  {result.deltas.albedo > 0 ? '+' : ''}{result.deltas.albedo}%
                </strong>
                <small>Mean surface brightness (HSV Value)</small>
              </div>

              <div className="drift-metric-card">
                <span className="metric-title">GLCM Texture Contrast Δ</span>
                <strong className="metric-value">
                  {result.deltas.contrast > 0 ? '+' : ''}{result.deltas.contrast}%
                </strong>
                <small>Spatial disparity & canopy granularity</small>
              </div>

              <div className="drift-metric-card">
                <span className="metric-title">Shannon Greyscale Entropy Δ</span>
                <strong className="metric-value">
                  {result.deltas.entropy > 0 ? '+' : ''}{result.deltas.entropy}%
                </strong>
                <small>Statistical randomness in intensity</small>
              </div>
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}
