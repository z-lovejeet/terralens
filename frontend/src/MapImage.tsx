import { useState } from 'react';
import { DownloadSimple, Eye, EyeSlash, MapTrifold, MagnifyingGlass } from '@phosphor-icons/react';
import { downloadJson, format, request } from './api';
import { clusterColor } from './Charts';
import { Notice, Panel } from './UI';
import { LAND, LandChip } from './scenes/land';
import { HowItWorks, ImageDrop, Segmented } from './scenes/SceneParts';
import './scenes/scenes.css';
import './sort/sort.css';  // shared summary banner and elbow chart
import './map/map.css';
import type { Capabilities, MapRegion, MapResult } from './types';

const COUNTS = ['auto', '2', '3', '4', '5', '6', '7', '8'];
const pct = (value: number) => `${format(value * 100, 0)}%`;

export default function MapImage({ capabilities }: { capabilities: Capabilities }) {
  const [file, setFile] = useState<File | null>(null);
  const [count, setCount] = useState('auto');
  const [result, setResult] = useState<MapResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function run(chosen: File | null = file, regions: string = count) {
    if (!chosen) return;
    const form = new FormData();
    form.append('file', chosen);
    form.append('count', regions);
    setBusy(true); setError('');
    try { setResult(await request<MapResult>('/map-regions', { method: 'POST', body: form })); }
    catch (e) { setError((e as Error).message); setResult(null); }
    finally { setBusy(false); }
  }

  return <div className="view-panel scene-view map-view">
    <div className="view-header">
      <div className="view-header-title">
        <span className="badge badge-primary"><MapTrifold size={14} weight="bold"/> Unsupervised segmentation</span>
        <h1>Map my image</h1>
        <p className="lead">Upload one satellite image of a farm, town, reservoir or any area. TerraLens splits it into regions of similar-looking land, all by itself, names each one (trees, fields, water, buildings, bare ground) and tells you how much of the image it covers.</p>
      </div>
    </div>

    <Panel title="Upload a satellite image" detail="A top-down image at least 128 pixels on each side. Larger areas with a few different kinds of land work best." className="scene-controls no-print">
      <div className="upload-layout">
        <ImageDrop label="Your image" hint="A top-down satellite image" file={file} onChoose={next => { setFile(next); run(next); }} onClear={() => { setFile(null); setResult(null); }} disabled={busy} maxBytes={capabilities.upload_max_bytes}/>
        <div className="map-help">
          <h3>What you get</h3>
          <ul>
            <li>A colour map of the regions the model finds, with no categories given in advance.</li>
            <li>How much of the image each region covers.</li>
            <li>What makes each region look different, in plain words.</li>
            <li>A name for each region, such as trees, fields, water, buildings or bare ground, and how sure it is.</li>
          </ul>
        </div>
      </div>
      <div className="scene-run-row">
        <label className="group-count">Number of regions
          <select value={count} onChange={event => { setCount(event.target.value); if (file) run(file, event.target.value); }} disabled={busy}>
            {COUNTS.map(value => <option key={value} value={value}>{value === 'auto' ? 'Auto (recommended)' : `${value} regions`}</option>)}
          </select>
        </label>
        <button className="button button-primary" type="button" disabled={busy || !file} onClick={() => run()}>
          {busy ? <span className="loading-dots"/> : <MagnifyingGlass size={18}/>}{busy ? 'Mapping…' : 'Map regions'}
        </button>
      </div>
      {error ? <Notice warning>{error}</Notice> : null}
    </Panel>

    {result ? <MapReport result={result} busy={busy} onPickK={k => { setCount(String(k)); run(file, String(k)); }}/> : null}
  </div>;
}

const CONFIDENCE = {
  high: 'matches the land model',
  medium: 'likely, from colour and texture',
  low: 'best guess',
} as const;

function regionName(region: MapRegion) {
  return region.name === 'mixed' ? 'Mixed land' : LAND[region.name].label;
}

function MapReport({ result, busy, onPickK }: { result: MapResult; busy: boolean; onPickK: (k: number) => void }) {
  const [overlay, setOverlay] = useState(true);
  const [colourBy, setColourBy] = useState<'land' | 'region'>('land');
  const [focus, setFocus] = useState<number | null>(null);
  const maxInertia = Math.max(...result.candidates.map(item => item.inertia), 0.0001);
  const accuracy = result.accuracy;
  const byRegion = new Map(result.regions.map(region => [region.region, region]));
  const fill = (region: MapRegion) => colourBy === 'land' ? LAND[region.name].color : clusterColor(region.region);
  const read = result.naming.method === 'colour and texture';

  function exportCsv() {
    const rows = [['region', 'name', 'confidence', 'named_by', 'share_percent', 'description'], ...result.regions.map(region => [region.letter, regionName(region), CONFIDENCE[region.confidence], region.named_by, String(region.share), region.description.join('; ')])];
    const url = URL.createObjectURL(new Blob([rows.map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(',')).join('\n')], { type: 'text/csv' }));
    const link = Object.assign(document.createElement('a'), { href: url, download: 'terralens-regions.csv' });
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <section className={`scene-report ${busy ? 'is-updating' : ''}`} aria-live="polite">
    <div className="sort-summary map-summary">
      <div>
        <span className="workspace-label">What is in your image</span>
        <h2>{result.land_cover.slice(0, 2).map(item => `${format(item.share, 0)}% ${(item.name === 'mixed' ? 'mixed land' : LAND[item.name].label.toLowerCase())}`).join(', ')}{result.land_cover.length > 2 ? ' and more' : ''}</h2>
        <p>{result.chosen === 'automatic' ? `The model found ${result.k} regions on its own (elbow method). ` : `You asked for ${result.k} regions. `}
          {result.separation === 'clear' ? 'They look clearly different from each other.' : result.separation === 'moderate' ? 'They are somewhat different, with soft edges between them.' : 'They overlap a lot, so treat the boundaries as rough.'}</p>
        <div className="share-strip" aria-label="Share of the image covered by each kind of land">
          {result.land_cover.map(item => <i key={item.name} style={{ width: `${item.share}%`, background: LAND[item.name].color }} title={`${LAND[item.name].label}: ${item.share}%`}/>)}
        </div>
        <ul className="cover-legend">{result.land_cover.map(item => <li key={item.name}><LandChip type={item.name}/><b>{format(item.share, 0)}%</b></li>)}</ul>
      </div>
      <figure className="k-chart" aria-label="Spread inside the regions for each number of regions">
        <figcaption>Spread inside the regions for each number of regions. The elbow is where adding more stops helping much. Click a bar to try it.</figcaption>
        <div className="k-bars">{result.candidates.map(item => <button type="button" key={item.k} className={item.k === result.k ? 'is-chosen' : ''} onClick={() => onPickK(item.k)} disabled={busy} title={`${item.k} regions: spread ${item.inertia.toFixed(0)}`}>
          <i style={{ height: `${Math.max(6, (item.inertia / maxInertia) * 100)}%` }}/><span>{item.k}</span>
        </button>)}</div>
      </figure>
    </div>

    {result.warnings.map(warning => <Notice key={warning}>{warning}</Notice>)}
    {read ? <Notice>This image is sharper than, or different from, the satellite images the land model learned from ({format(result.naming.unfamiliar_percent, 0)}% of its squares look unfamiliar), so each region is named from its colour and texture instead. Names marked "best guess" are less certain; trees and crop fields are the pair most often mixed up.</Notice> : null}

    <div className="map-body">
      <Panel title="Region map" detail="Click a region in the list to highlight it." action={<div className="map-tools no-print">
        <Segmented label="Colour the map by" value={colourBy} onChange={setColourBy} options={[{ id: 'land', label: 'Land type' }, { id: 'region', label: 'Region' }]}/>
        <button type="button" className="text-button" onClick={() => setOverlay(!overlay)}>{overlay ? <EyeSlash size={15}/> : <Eye size={15}/>}{overlay ? 'Hide colours' : 'Show colours'}</button>
      </div>}>
        <div className="region-frame" style={{ aspectRatio: `${result.grid.cols} / ${result.grid.rows}` }}>
          <img src={result.image} alt="Your satellite image"/>
          <div className={`region-grid ${overlay ? 'is-on' : ''}`} style={{ gridTemplateColumns: `repeat(${result.grid.cols}, 1fr)` }} aria-hidden="true">
            {result.cells.map((value, index) => {
              const region = byRegion.get(value)!;
              return <span key={index} title={`Region ${region.letter}: ${regionName(region)}`}
                className={focus != null && focus !== value ? 'is-faded' : ''} style={{ ['--region' as string]: fill(region) }}/>;
            })}
          </div>
        </div>
      </Panel>
      <Panel title="Regions" detail="Largest first">
        <ul className="region-list">{result.regions.map(region => <li key={region.region}>
          <button type="button" className={focus === region.region ? 'is-active' : ''} aria-pressed={focus === region.region} onClick={() => setFocus(focus === region.region ? null : region.region)}>
            <span className="region-swatch" style={{ background: fill(region) }}>{region.letter}</span>
            <span className="region-text">
              <span className="region-head"><strong>{regionName(region)}</strong><b>{format(region.share, 0)}%</b></span>
              <span className="region-bar"><i style={{ width: `${region.share}%`, background: fill(region) }}/></span>
              <span className="region-meta">
                <span className={`confidence is-${region.confidence}`}>{region.named_by === 'land model' && region.model_agreement != null && region.name !== 'mixed' ? `${pct(region.model_agreement)} of the region matches the land model` : region.name === 'mixed' && region.named_by === 'land model' ? 'no single land type covers half of it' : CONFIDENCE[region.confidence]}</span>
                <span className="region-letter">Region {region.letter}</span>
              </span>
              <span className="region-desc">{region.description.join(' · ')}</span>
            </span>
          </button>
        </li>)}</ul>
      </Panel>
    </div>

    {accuracy ? <Panel title="How accurate is this?" detail={`Regions measured on ${accuracy.scenes} test scenes built from held-out satellite patches with a known layout`}>
      <ul className="accuracy-list">
        <li><b>{format(accuracy.ari, 2)}</b><span>agreement between the found regions and the true layout (adjusted Rand index; 1 is perfect, 0 is chance). Enlarged three times, as in a close-up screenshot: {format(accuracy.zoomed_ari, 2)}.</span></li>
        <li><b>±{format(accuracy.area_error_points, 0)}</b><span>percentage points: typical gap between a region's share of the image and the true share.</span></li>
        <li><b>{pct(accuracy.name_accuracy)}</b><span>of region names from the land model were right on those scenes; {pct(accuracy.named_share)} of regions got a name and the rest were called mixed land.</span></li>
        <li><b>{pct(accuracy.colour_texture.accuracy)}</b><span>of region names from colour and texture were right on {accuracy.colour_texture.views} public satellite views checked by eye (lakes, rivers, sea fronts, forests, farms and towns); {pct(accuracy.colour_texture.clear_accuracy)} when not marked "best guess". Buildings and water were never named wrongly; trees and crop fields were the pair most often confused.</span></li>
      </ul>
    </Panel> : null}

    <div className="report-actions no-print">
      <button type="button" className="button button-primary" onClick={exportCsv}><DownloadSimple size={17}/>Download regions (CSV)</button>
      <button type="button" className="button button-outline" onClick={() => downloadJson({ ...result, image: undefined }, 'terralens-regions.json')}><DownloadSimple size={17}/>Download full result</button>
    </div>
    <HowItWorks method={result.method}/>
  </section>;
}
