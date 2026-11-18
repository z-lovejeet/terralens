import { useState, useEffect } from 'react';
import { 
  Flame, 
  Waves, 
  Tree, 
  CloudRain, 
  SunHorizon,
  UploadSimple, 
  ArrowClockwise, 
  Warning, 
  ShieldWarning, 
  CheckCircle, 
  DownloadSimple,
  Sparkle,
  Info,
  Compass
} from '@phosphor-icons/react';
import { Panel, Notice } from './UI';
import { request } from './api';
import type { Study, DisasterPreset, DisasterResult } from './types';

interface DisasterProps {
  study: Study;
}

function getDisasterIcon(type: string) {
  const t = type.toLowerCase();
  if (t.includes('fire')) return <Flame size={16} weight="fill" />;
  if (t.includes('tsunami') || t.includes('wave') || t.includes('surge')) return <Waves size={16} weight="fill" />;
  if (t.includes('forest') || t.includes('tree') || t.includes('canopy')) return <Tree size={16} weight="fill" />;
  if (t.includes('flood') || t.includes('rain')) return <CloudRain size={16} weight="fill" />;
  if (t.includes('drought') || t.includes('heat') || t.includes('sun')) return <SunHorizon size={16} weight="fill" />;
  return <Compass size={16} weight="fill" />;
}

export default function Disaster(_props: DisasterProps) {
  const [presets, setPresets] = useState<DisasterPreset[]>([]);
  const [activePreset, setActivePreset] = useState<string>('wildfire_burn_scar');
  const [customFile, setCustomFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<DisasterResult | null>(null);

  // Fetch presets on load
  useEffect(() => {
    request<DisasterPreset[]>('/disaster/presets')
      .then(data => {
        setPresets(data);
        if (data.length > 0) {
          executeDisasterAnalysis(data[0].id, null);
        }
      })
      .catch(err => {
        setError('Failed to load disaster presets: ' + err.message);
      });
  }, []);

  async function executeDisasterAnalysis(presetId: string | null, file: File | null) {
    setLoading(true);
    setError('');
    try {
      const formData = new FormData();
      if (presetId && !file) {
        formData.append('preset_id', presetId);
      } else if (file) {
        formData.append('file', file);
      }

      const res = await request<DisasterResult>('/disaster', {
        method: 'POST',
        body: formData,
      });
      setResult(res);
    } catch (err: any) {
      setError('Disaster analysis failed: ' + (err.message || String(err)));
    } finally {
      setLoading(false);
    }
  }

  function handleSelectPreset(id: string) {
    setActivePreset(id);
    setCustomFile(null);
    executeDisasterAnalysis(id, null);
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      setCustomFile(file);
      setActivePreset('');
      executeDisasterAnalysis(null, file);
    }
  }

  function downloadJson(data: any, filename: string) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  const currentPresetMeta = presets.find(p => p.id === activePreset);
  const cr = result?.crisis_report;

  return (
    <div className="view-panel disaster-view">
      <div className="view-header">
        <div className="view-header-title">
          <span className="badge badge-primary">
            <Sparkle size={14} weight="fill" /> Zero-Shot Vision Foundation Core
          </span>
          <h1>Natural Disaster & Catastrophe Reconnaissance</h1>
          <p className="lead">
            Autonomous zero-shot damage assessment, multi-spectral crisis anomaly detection, and emergency dispatch analysis powered by Gemini 3.5 Flash-Lite Vision.
          </p>
        </div>
      </div>

      {/* Preset and upload scenario selector */}
      <Panel title="Emergency Reconnaissance Scenario" className="disaster-controls-panel">
        <div className="changes-controls-header">
          <div>
            <span className="workspace-label">Environmental Catastrophe Scenarios</span>
            <h3>Select a Verified Disaster Pass or Upload Custom Aerial Image</h3>
          </div>
          <div className="disaster-actions-row">
            <label className="file-upload-button button button-secondary">
              <UploadSimple size={16} />
              <span>{customFile ? customFile.name : 'Upload Disaster Imagery'}</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleFileUpload} style={{ display: 'none' }} />
            </label>
            <button
              className="button button-primary"
              disabled={loading}
              onClick={() => executeDisasterAnalysis(activePreset || null, customFile)}
            >
              <ArrowClockwise size={16} className={loading ? 'is-spinning' : ''} />
              <span>{loading ? 'Analyzing Scene...' : 'Scan Catastrophe'}</span>
            </button>
          </div>
        </div>

        <div className="preset-chips-grid">
          {presets.map(p => (
            <button
              key={p.id}
              className={`preset-chip ${activePreset === p.id ? 'is-active' : ''}`}
              onClick={() => handleSelectPreset(p.id)}
            >
              <span className="preset-chip-title">
                {getDisasterIcon(p.type)}
                <span>{p.title}</span>
              </span>
              <small className="preset-chip-location">{p.location}</small>
            </button>
          ))}
        </div>

        {currentPresetMeta && (
          <p className="preset-description-text">
            <Info size={16} /> <strong>{currentPresetMeta.location}:</strong> {currentPresetMeta.description}
          </p>
        )}
      </Panel>

      {error && <Notice warning>{error}</Notice>}

      {/* Results View */}
      {cr && result && (
        <div className="disaster-results-container">
          {/* Prominent Alert Status Banner */}
          <div className={`change-alert-banner alert-${cr.severity_level.toLowerCase()}`}>
            <div className="alert-banner-icon">
              {cr.severity_level === 'CRITICAL' ? (
                <ShieldWarning size={36} weight="fill" />
              ) : cr.severity_level === 'HIGH' ? (
                <Warning size={36} weight="fill" />
              ) : (
                <CheckCircle size={36} weight="fill" />
              )}
            </div>
            <div className="alert-banner-content">
              <div className="alert-level-pill">
                <strong>{cr.severity_level} EMERGENCY STATUS</strong> · {cr.disaster_type}
                <span className="severity-score-badge">Severity {cr.severity_score}/100</span>
              </div>
              <h4 className="alert-headline">{cr.headline}</h4>
              <p className="alert-narrative-text">{cr.damage_assessment}</p>
              <div className="alert-recommendation">
                <Sparkle size={16} weight="fill" />
                <strong>Automated Operational Dispatch:</strong> {cr.operational_dispatch}
              </div>
            </div>
          </div>

          {/* Main Inspection Grid */}
          <div className="disaster-inspection-layout">
            {/* Left: Satellite Crisis Viewport */}
            <div className="disaster-image-column">
              <Panel title="Observation Viewport" className="disaster-viewport-panel">
                <div className="viewport-header-tag">
                  <span>Spectral Surface Extent</span>
                  <span className="model-watermark">Engine: Gemini 3.5 Flash-Lite Vision</span>
                </div>
                <div className="disaster-image-frame">
                  <img 
                    src={result.image_base64} 
                    alt="Satellite crisis observation pass" 
                    className="disaster-primary-image"
                  />
                  <div className="damage-extent-tag">
                    <span>Estimated Damage: {cr.affected_area_percentage}% of Frame</span>
                  </div>
                </div>
                <div className="viewport-meta-footer">
                  <span>Resolution: 10m GSD</span>
                  <span>Confidence: {(cr.confidence_score * 100).toFixed(0)}%</span>
                  <span>Model: Zero-Shot Vision Transformer</span>
                </div>
              </Panel>
            </div>

            {/* Right: Spectral Telemetry & Detected Anomalies */}
            <div className="disaster-telemetry-column">
              {/* Spectral Anomalies Grid */}
              <Panel title="Multi-Spectral Anomaly Vector" className="anomaly-panel">
                <div className="anomaly-panel-header">
                  <div>
                    <span className="workspace-label">Unsupervised Spectral Decomposition</span>
                    <h3>Physical Anomaly Deltas</h3>
                  </div>
                  <button
                    className="button button-small button-ghost"
                    onClick={() => downloadJson(result, 'terralens-disaster-report.json')}
                  >
                    <DownloadSimple size={15} />
                    <span>Export Crisis Report</span>
                  </button>
                </div>

                <div className="drift-metrics-grid">
                  <div className="drift-metric-card">
                    <span className="metric-title">Thermal Albedo Shift</span>
                    <strong className="metric-value is-elevated">
                      {cr.spectral_anomalies.thermal_albedo_shift}
                    </strong>
                    <small>Radiant temperature spike</small>
                  </div>

                  <div className="drift-metric-card">
                    <span className="metric-title">Photosynthetic Loss</span>
                    <strong className="metric-value is-negative">
                      {cr.spectral_anomalies.chlorophyll_depletion}
                    </strong>
                    <small>Vegetative chlorophyll collapse</small>
                  </div>

                  <div className="drift-metric-card">
                    <span className="metric-title">Moisture Deficit / Delta</span>
                    <strong className="metric-value">
                      {cr.spectral_anomalies.moisture_delta}
                    </strong>
                    <small>Hydrological delta (surge/drought)</small>
                  </div>

                  <div className="drift-metric-card">
                    <span className="metric-title">Structural Entropy Δ</span>
                    <strong className="metric-value">
                      {cr.spectral_anomalies.texture_entropy}
                    </strong>
                    <small>Biomass & terrain disorder</small>
                  </div>
                </div>
              </Panel>

              {/* Observed Physical Signatures */}
              <Panel title="Visual Crisis Signatures" className="features-panel">
                <span className="workspace-label">Zero-Shot Pattern Discovery</span>
                <h3>Identified Ground-Level Phenomenon</h3>
                <div className="disaster-features-tags">
                  {cr.detected_features.map((feat, idx) => (
                    <div key={idx} className="disaster-feature-chip">
                      <Compass size={14} weight="bold" />
                      <span>{feat}</span>
                    </div>
                  ))}
                </div>
              </Panel>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
