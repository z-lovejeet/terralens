import { useState } from 'react';
import { CheckSquare, DownloadSimple, MagnifyingGlass, Plant, Printer, Ruler } from '@phosphor-icons/react';
import { downloadJson, format, request } from './api';
import { Notice, Panel } from './UI';
import { HowItWorks, ImageDrop, ScreenshotTips, Segmented } from './scenes/SceneParts';
import './scenes/scenes.css';
import './radar/radar.css';
import './plant/plant.css';
import type { AreaWidth, Capabilities, PlantResult, PlantSpot } from './types';

const WIDTHS: { id: AreaWidth; label: string; hint: string }[] = [
  { id: 'street', label: 'A street', hint: 'about 200 m across' },
  { id: 'colony', label: 'A colony or campus', hint: 'about 500 m across' },
  { id: 'neighbourhood', label: 'A neighbourhood', hint: 'about 1 km across' },
  { id: 'large', label: 'A larger area', hint: 'about 3 km across' },
];
const KIND: Record<string, string> = {
  open_plot: 'Open plot', roadside: 'Roadside', park_or_lawn: 'Park or lawn', courtyard: 'Courtyard',
  field_edge: 'Field edge', school_or_campus: 'School or campus', riverbank: 'Stream or pond bank', other: 'Open ground',
};
const COLUMNS = 'ABCDEFGHIJKL';
type Layer = 'spots' | 'ground' | 'photo';

const area = (m2: number) => m2 >= 10000 ? `${format(m2 / 10000, 1)} hectares` : `${format(m2, 0)} m²`;

export default function PlantTrees({ capabilities }: { capabilities: Capabilities }) {
  const [file, setFile] = useState<File | null>(null);
  const [width, setWidth] = useState<AreaWidth>('colony');
  const [result, setResult] = useState<PlantResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function run(chosen: File | null = file, areaWidth: AreaWidth = width) {
    if (!chosen) { setError('Upload a satellite image of the place first.'); return; }
    const form = new FormData();
    form.append('file', chosen);
    form.append('area_width', areaWidth);
    setBusy(true); setError('');
    try { setResult(await request<PlantResult>('/plant-check', { method: 'POST', body: form })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return <div className="view-panel scene-view plant-view">
    <div className="view-header">
      <div className="view-header-title">
        <span className="badge badge-primary"><Plant size={14} weight="bold"/> Everyday tool</span>
        <h1>Where can we plant trees?</h1>
        <p className="lead">Upload a satellite view of your colony, campus or street. TerraLens marks the open ground where trees could grow, estimates how many would fit, and gives a checklist to get a planting drive started.</p>
      </div>
    </div>

    <Panel title="Upload a satellite image of the place" detail="A top-down screenshot works best. Include the roads, plots and parks you want to look at." className="scene-controls no-print">
      <div className="upload-layout">
        <ImageDrop label="Your place" hint="A top-down satellite screenshot" file={file} onChoose={next => { setFile(next); setResult(null); run(next); }} onClear={() => { setFile(null); setResult(null); }} disabled={busy} maxBytes={capabilities.upload_max_bytes}/>
        <div className="area-help">
          <fieldset className="width-picker" disabled={busy}>
            <legend><Ruler size={16}/>How wide is the area in your image?</legend>
            <div className="width-options">{WIDTHS.map(option => <button type="button" key={option.id} className={width === option.id ? 'is-active' : ''} aria-pressed={width === option.id} onClick={() => { setWidth(option.id); if (result) run(file, option.id); }}>
              <strong>{option.label}</strong><small>{option.hint}</small>
            </button>)}</div>
            <p className="caption">Use the scale bar in the corner of Google Maps to judge. This only affects how many trees are estimated.</p>
          </fieldset>
          <ScreenshotTips/>
        </div>
      </div>
      <div className="scene-run-row">
        <button className="button button-primary" type="button" disabled={busy || !file} onClick={() => run()}>
          {busy ? <span className="loading-dots"/> : <MagnifyingGlass size={18}/>}{busy ? 'Looking for spots…' : 'Find planting spots'}
        </button>
      </div>
      {error ? <Notice warning>{error}</Notice> : null}
    </Panel>

    {busy ? <p className="reading-status" role="status"><span className="loading-dots"/>Looking for open ground square by square. This usually takes 10–20 seconds.</p> : null}
    {result ? <PlantReport result={result} placeName={file?.name} busy={busy}/> : busy ? <div className="view-skeleton" aria-hidden="true"><div/><div/><div/></div> : null}
  </div>;
}

function PlantReport({ result, placeName, busy }: { result: PlantResult; placeName?: string; busy: boolean }) {
  const [layer, setLayer] = useState<Layer>(result.spots.length ? 'spots' : 'ground');
  const { summary } = result;
  const gain = Math.max(0, summary.tree_cover_after - summary.tree_cover_now);
  return <section className={`scene-report ${busy ? 'is-updating' : ''}`} aria-live="polite">
    <div className="plant-hero">
      <div className="plant-hero-count">
        <span className="workspace-label">Planting report{placeName ? ` · ${placeName}` : ''}</span>
        <strong>{summary.trees_possible > 0 ? `About ${format(summary.trees_possible, 0)}` : 'Very few'}</strong>
        <span>trees could be planted here</span>
        <small>at about {summary.spacing_m} m apart on the open ground found</small>
      </div>
      <div className="plant-hero-copy">
        <h2>{summary.headline}</h2>
        {summary.text ? <p>{summary.text}</p> : null}
        <div className="cover-meter" aria-label={`Tree cover ${summary.tree_cover_now} percent now, up to ${summary.tree_cover_after} percent after planting`}>
          <div className="cover-track"><i className="cover-now" style={{ width: `${summary.tree_cover_now}%` }}/><i className="cover-gain" style={{ width: `${gain}%` }}/></div>
          <div className="cover-labels"><span><b>{format(summary.tree_cover_now, 0)}%</b> tree cover today</span><span><b>up to {format(summary.tree_cover_after, 0)}%</b> once the new trees grow</span></div>
        </div>
        <div className="hero-stats">
          <div><span>Open ground found</span><strong>{format(summary.plantable_percent, 0)}%</strong></div>
          <div><span>That is roughly</span><strong>{area(summary.plantable_m2)}</strong></div>
          <div><span>Planting spots</span><strong>{result.spots.length}</strong></div>
        </div>
      </div>
    </div>

    <div className="scan-body">
      <figure className="scan-figure">
        <div className="scan-layer-bar no-print">
          <Segmented<Layer> label="Map layer" value={layer} onChange={setLayer} options={[...(result.spots.length ? [{ id: 'spots' as Layer, label: 'Planting spots' }] : []), { id: 'ground', label: 'Open ground' }, { id: 'photo', label: 'Photo' }]}/>
        </div>
        <div className="grid-frame" style={{ ['--cols' as string]: result.grid.cols, ['--rows' as string]: result.grid.rows }}>
          <div className="axis axis-top" aria-hidden="true">{Array.from({ length: result.grid.cols }, (_, i) => <span key={i}>{COLUMNS[i]}</span>)}</div>
          <div className="axis axis-left" aria-hidden="true">{Array.from({ length: result.grid.rows }, (_, i) => <span key={i}>{i + 1}</span>)}</div>
          <div className="scan-image" style={{ aspectRatio: `${result.grid.cols} / ${result.grid.rows}` }}>
            <img src={result.image} alt="Satellite view of the place"/>
            <div className="scan-grid" style={{ gridTemplateColumns: `repeat(${result.grid.cols}, 1fr)` }} aria-hidden="true">
              {result.tiles.map(tile => <span key={`${tile.row}-${tile.col}`} title={`${COLUMNS[tile.col]}${tile.row + 1}: ${Math.round(tile.plantable)}% open ground, ${Math.round(tile.trees)}% trees`}
                style={layer === 'ground' ? { background: `color-mix(in oklch, var(--plant-open) ${Math.min(85, Math.round(tile.plantable * 1.6))}%, transparent)` } : undefined}/>)}
            </div>
            {layer === 'spots' ? result.spots.map(spot => <div key={spot.number} className={`mark plant-mark priority-${spot.priority}`} style={{ top: `${spot.top}%`, left: `${spot.left}%`, width: `${spot.width}%`, height: `${spot.height}%` }}><b>{spot.number}</b></div>) : null}
          </div>
        </div>
        <figcaption>
          {layer === 'spots' ? <span className="priority-key"><i className="priority-high"/>High priority<i className="priority-medium"/>Medium<i className="priority-low"/>Low</span>
            : layer === 'ground' ? <span className="ground-key"><i/>Darker green means more open ground in that square. Hover a square for its numbers.</span>
            : <span>Grid letters and numbers help you point at a spot when you talk to neighbours or officials.</span>}
        </figcaption>
      </figure>

      <div className="scan-details">
        <section className="scan-section">
          <h3>Best places to plant</h3>
          {result.spots.length ? <ol className="spot-list">{result.spots.map(spot => <SpotItem key={spot.number} spot={spot}/>)}</ol>
            : <p className="fine">No clear open spots were found in this image. Try a wider view that includes parks, plots or wide roads.</p>}
        </section>
        {result.ideas.length ? <section className="scan-section"><h3>Ideas for this place</h3><ul className="evidence">{result.ideas.map(idea => <li key={idea}>{idea}</li>)}</ul></section> : null}
      </div>
    </div>

    <Panel title="Before you plant" detail="A short checklist for residents, schools and societies">
      <ul className="checklist">{result.before_you_plant.map(item => <li key={item.topic}><CheckSquare size={20}/><span><strong>{item.topic}</strong>{item.text}</span></li>)}</ul>
    </Panel>

    {result.warnings.map(warning => <Notice key={warning}>{warning}</Notice>)}
    {result.quality_notes.length ? <Notice><strong>About this image:</strong> {result.quality_notes.join(' ')}</Notice> : null}
    <Notice warning={result.reliability.level === 'low'}><strong>Reliability: {result.reliability.level}.</strong> {result.reliability.note}</Notice>

    <div className="report-actions no-print">
      <button type="button" className="button button-primary" onClick={() => window.print()}><Printer size={17}/>Save report as PDF</button>
      <button type="button" className="button button-outline" onClick={() => downloadJson({ ...result, image: undefined }, 'terralens-planting-report.json')}><DownloadSimple size={17}/>Download data</button>
    </div>
    <HowItWorks method={result.method}/>
    <p className="source-line">An AI-assisted estimate from the image, assuming the image is about {format(summary.area_width_m, 0)} m wide. Check ownership and permissions on the ground before planting.</p>
  </section>;
}

function SpotItem({ spot }: { spot: PlantSpot }) {
  return <li className={`spot priority-${spot.priority}`}>
    <b className="spot-number">{spot.number}</b>
    <div>
      <div className="spot-head"><strong>{spot.label}</strong><span className="spot-priority">{spot.priority} priority</span></div>
      <p>{spot.reason}</p>
      <small>{KIND[spot.kind] ?? 'Open ground'} · about {area(spot.area_m2)} · room for roughly {format(spot.trees, 0)} trees</small>
    </div>
  </li>;
}
