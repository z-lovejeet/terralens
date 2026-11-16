import { useEffect, useState } from 'react';
import { ArrowClockwise, CheckCircle, DownloadSimple, Eye, EyeSlash, GridFour, Info, Sparkle, UploadSimple } from '@phosphor-icons/react';
import { downloadJson, format, percent, request } from './api';
import { Notice, Panel } from './UI';
import type { ScannerResult, ScannerTile, Study } from './types';

interface PresetItem {
  id: string;
  title: string;
  location: string;
  description: string;
}

export default function Scanner({ study: _study }: { study?: Study }) {
  const [presets, setPresets] = useState<PresetItem[]>([]);
  const [activePreset, setActivePreset] = useState<string>('rhine_valley');
  const gridSize = 4;
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<ScannerResult | null>(null);
  const [selectedTile, setSelectedTile] = useState<ScannerTile | null>(null);
  const [showOverlay, setShowOverlay] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [customFile, setCustomFile] = useState<File | null>(null);

  useEffect(() => {
    request<PresetItem[]>('/scan/presets')
      .then(data => setPresets(data))
      .catch(() => {});
    executeScan('rhine_valley', null, 4);
  }, []);

  const executeScan = async (presetId: string | null, file: File | null, grid: number) => {
    setLoading(true);
    setError('');
    setSelectedTile(null);
    try {
      const formData = new FormData();
      if (file) {
        formData.append('file', file);
      } else if (presetId) {
        formData.append('preset_id', presetId);
      }
      formData.append('grid_size', String(grid));

      const res = await fetch('/api/scan', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Scan failed with status ${res.status}`);
      }
      const data: ScannerResult = await res.json();
      setResult(data);
      if (data.tiles?.length) {
        setSelectedTile(data.tiles[0]);
      }
    } catch (e: any) {
      setError(e.message || 'Failed to scan regional scene.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (id: string) => {
    setActivePreset(id);
    setCustomFile(null);
    executeScan(id, null, gridSize);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setCustomFile(file);
      setActivePreset('');
      executeScan(null, file, gridSize);
    }
  };

  const currentPresetMeta = presets.find(p => p.id === activePreset);

  return (
    <div className="view-panel scanner-view">
      <div className="view-header">
        <div className="view-header-title">
          <span className="badge badge-primary"><GridFour size={14} weight="bold" /> Real-World Applied Core</span>
          <h1>Regional Scene Scanner & Grid Segmentation</h1>
          <p className="lead">
            Tile continuous wide-area satellite passes into 64×64 patches and generate an automated unsupervised land-cover segmentation heatmap.
          </p>
        </div>
      </div>

      {/* Preset and upload selector */}
      <Panel title="Target Regional Landscape" className="scanner-controls-panel">
        <div className="scanner-controls-header">
          <div>
            <span className="workspace-label">Target Regional Landscape</span>
            <h3>Select a European Observation Scene or Upload Custom Image</h3>
          </div>
          <div className="scanner-actions-row">
            <label className="file-upload-button button button-secondary">
              <UploadSimple size={16} />
              <span>{customFile ? customFile.name : 'Upload Satellite Scene'}</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleFileUpload} style={{ display: 'none' }} />
            </label>
            <button
              className="button button-primary"
              disabled={loading}
              onClick={() => executeScan(activePreset || null, customFile, gridSize)}
            >
              <ArrowClockwise size={16} className={loading ? 'is-spinning' : ''} />
              <span>{loading ? 'Segmenting Scene...' : 'Re-scan Scene'}</span>
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
      </Panel>

      {error && <Notice warning>{error}</Notice>}

      {/* Results grid */}
      {result && (
        <div className="scanner-results-layout">
          {/* Left Column: Interactive Heatmap */}
          <Panel title="Spatial Segmentation Heatmap" className="scanner-canvas-card">
            <div className="canvas-header-bar">
              <div>
                <span className="workspace-label">Spatial Segmentation Heatmap</span>
                <h4>{result.total_tiles} Tiles ({result.grid_size}×{result.grid_size} Grid · 64×64 px each)</h4>
              </div>
              <div className="canvas-toggles">
                <button
                  className={`button button-small ${showOverlay ? 'button-secondary' : 'button-ghost'}`}
                  onClick={() => setShowOverlay(!showOverlay)}
                  title="Toggle cluster color wash"
                >
                  {showOverlay ? <Eye size={16} /> : <EyeSlash size={16} />}
                  <span>{showOverlay ? 'Hide Land Colors' : 'Show Land Colors'}</span>
                </button>
                <button
                  className="button button-small button-ghost"
                  onClick={() => downloadJson(result, 'terralens-regional-scan.json')}
                  title="Export survey JSON"
                >
                  <DownloadSimple size={16} />
                  <span>Export JSON</span>
                </button>
              </div>
            </div>

            <div className="scanner-canvas-container">
              <div className="scanner-viewport">
                <img
                  src={result.image_base64}
                  alt="Scanned regional satellite view"
                  className="scanner-base-image"
                />
                <div
                  className="scanner-grid-overlay"
                  style={{
                    gridTemplateColumns: `repeat(${result.grid_size}, 1fr)`,
                    gridTemplateRows: `repeat(${result.grid_size}, 1fr)`,
                  }}
                >
                  {result.tiles.map(tile => {
                    const isSelected = selectedTile?.row === tile.row && selectedTile?.col === tile.col;
                    return (
                      <div
                        key={`${tile.row}-${tile.col}`}
                        className={`scanner-tile ${isSelected ? 'is-selected' : ''}`}
                        onClick={() => setSelectedTile(tile)}
                        style={{
                          backgroundColor: showOverlay ? `${tile.color}88` : 'transparent',
                          borderColor: isSelected ? '#FFFFFF' : 'rgba(255,255,255,0.3)',
                        }}
                      >
                        <span className="tile-badge">
                          {String(tile.cluster_id + 1).padStart(2, '0')}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <p className="canvas-footer-tip">
              Click on any grid tile to inspect its individual spectral telemetry and PCA coordinates.
            </p>
          </Panel>

          {/* Right Column: Tile Inspector & Acreage Distribution */}
          <div className="scanner-telemetry-column">
            {/* Selected Tile Inspector */}
            {selectedTile ? (
              <Panel title="Selected Tile Telemetry" className="selected-tile-panel">
                <div className="panel-badge-row">
                  <span className="badge badge-secondary">
                    Tile ({selectedTile.row + 1}, {selectedTile.col + 1}) of {result.grid_size}×{result.grid_size}
                  </span>
                  <span className="confidence-pill" style={{ borderColor: selectedTile.color }}>
                    <CheckCircle size={14} color={selectedTile.color} weight="fill" />
                    <span>{percent(selectedTile.confidence)} match</span>
                  </span>
                </div>

                <div className="tile-title-row">
                  <span className="color-swatch" style={{ backgroundColor: selectedTile.color }} />
                  <div>
                    <h3 className="tile-class-name">
                      Group {String(selectedTile.cluster_id + 1).padStart(2, '0')} · {selectedTile.cluster_name}
                    </h3>
                    <small className="tile-centroid-distance">
                      Euclidean distance to centroid: <code>{format(selectedTile.distance)}</code>
                    </small>
                  </div>
                </div>

                <div className="tile-features-summary">
                  <span className="workspace-label">Tile Telemetry</span>
                  <p>{selectedTile.summary}</p>
                  <div className="tile-coords-box">
                    <span>PCA Axis 1: <code>{format(selectedTile.pca[0])}</code></span>
                    <span>PCA Axis 2: <code>{format(selectedTile.pca[1])}</code></span>
                  </div>
                </div>
              </Panel>
            ) : null}

            {/* Acreage Distribution Breakdown */}
            <Panel title="Surveyed Acreage Breakdown" className="acreage-distribution-panel">
              <span className="workspace-label">Automated Land-Cover Distribution</span>
              <h3>Surveyed Acreage Breakdown</h3>
              <p className="distribution-intro">Proportional coverage across the {result.total_tiles} surveyed tiles:</p>

              <div className="distribution-bars-list">
                {result.distribution.map(item => (
                  <div key={item.cluster_id} className="distribution-bar-item">
                    <div className="bar-labels-row">
                      <span className="bar-class-title">
                        <span className="bar-swatch" style={{ backgroundColor: item.color }} />
                        <strong>Group {String(item.cluster_id + 1).padStart(2, '0')}</strong> · {item.name}
                      </span>
                      <span className="bar-percentage-label">
                        <strong>{item.percentage}%</strong> ({item.count} {item.count === 1 ? 'tile' : 'tiles'})
                      </span>
                    </div>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{ width: `${item.percentage}%`, backgroundColor: item.color }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Panel>

            {/* Ecological Assessment Narrative */}
            <Panel title="Automated Survey Intelligence" className="ecological-assessment-card">
              <div className="assessment-header">
                <Sparkle size={18} color="#205B4D" weight="fill" />
                <span className="workspace-label">Automated Survey Intelligence</span>
              </div>
              <p className="assessment-body">{result.assessment}</p>
            </Panel>
          </div>
        </div>
      )}
    </div>
  );
}
