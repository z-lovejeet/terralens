import { useState } from 'react';
import { CheckCircle, DownloadSimple, Eye, EyeSlash, HouseLine, Info, MagnifyingGlass, Printer, Warning } from '@phosphor-icons/react';
import { downloadJson, format, request } from './api';
import { Notice, Panel } from './UI';
import { LAND, LAND_ORDER, LandLegend } from './scenes/land';
import { HowItWorks, ImageDrop, SceneMap, ScreenshotTips } from './scenes/SceneParts';
import './scenes/scenes.css';
import type { AreaResult, Capabilities } from './types';

export default function AreaCheck({ capabilities }: { capabilities: Capabilities }) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<AreaResult | null>(null);
  const [overlay, setOverlay] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function run(chosen: File | null = file) {
    if (!chosen) { setError('Upload a satellite image of your area first.'); return; }
    const form = new FormData();
    form.append('detail', 'high');
    form.append('file', chosen);
    setBusy(true); setError('');
    try { setResult(await request<AreaResult>('/area-check', { method: 'POST', body: form })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return <div className="view-panel scene-view">
    <div className="view-header">
      <div className="view-header-title">
        <span className="badge badge-primary"><HouseLine size={14} weight="bold"/> Everyday tool</span>
        <h1>Check my area</h1>
        <p className="lead">See how much of any neighbourhood, farm or town is greenery, farmland, water or buildings. Useful before buying a home, planning a garden or farm, or simply understanding the place you live.</p>
      </div>
    </div>

    <Panel title="Upload a satellite image of your area" detail="A top-down screenshot works best: a whole neighbourhood or a few fields, roughly 1–3 km across." className="scene-controls no-print">
      <div className="upload-layout">
        <ImageDrop label="Your area" hint="A top-down satellite screenshot" file={file} onChoose={next => { setFile(next); setResult(null); run(next); }} onClear={() => { setFile(null); setResult(null); }} disabled={busy} maxBytes={capabilities.upload_max_bytes}/>
        <div className="area-help">
          <ScreenshotTips/>
          <ul className="area-uses">
            <li><strong>Buying or renting a home?</strong> Check how green the neighbourhood is and whether water is close by.</li>
            <li><strong>Farming or gardening?</strong> See how much of the land around you is fields, trees or buildings.</li>
            <li><strong>Curious about your town?</strong> Compare your area with somewhere else you know.</li>
          </ul>
        </div>
      </div>
      <div className="scene-run-row">
        <button className="button button-primary" type="button" disabled={busy || !file} onClick={() => run()}>
          {busy ? <span className="loading-dots"/> : <MagnifyingGlass size={18}/>}{busy ? 'Checking…' : 'Check this area'}
        </button>
      </div>
      {error ? <Notice warning>{error}</Notice> : null}
    </Panel>

    {busy ? <p className="reading-status" role="status"><span className="loading-dots"/>Reading your area square by square. This usually takes 10–20 seconds.</p> : null}
    {result ? <AreaReport result={result} placeName={file?.name} overlay={overlay} setOverlay={setOverlay} busy={busy}/> : busy ? <div className="view-skeleton" aria-hidden="true"><div/><div/><div/></div> : null}
  </div>;
}

function AreaReport({ result, placeName, overlay, setOverlay, busy }: { result: AreaResult; placeName?: string; overlay: boolean; setOverlay: (value: boolean) => void; busy: boolean }) {
  const { profile, reliability, place } = result;
  const columns = 'ABCDEFGHIJKL';
  const cells = result.tiles.map(tile => {
    const mix = LAND_ORDER.filter(type => type !== 'mixed' && tile.shares[type as keyof typeof tile.shares] >= 5)
      .sort((a, b) => tile.shares[b as keyof typeof tile.shares] - tile.shares[a as keyof typeof tile.shares])
      .map(type => `${LAND[type].label} ${Math.round(tile.shares[type as keyof typeof tile.shares])}%`).join(', ');
    return { color: LAND[tile.land_type].color, label: `${columns[tile.col]}${tile.row + 1}: ${mix || LAND[tile.land_type].label}` };
  });
  const shown = result.breakdown.filter(item => item.percent > 0);
  const greenAngle = Math.min(profile.green_cover.percent, 100) * 3.6;
  return <section className={`scene-report ${busy ? 'is-updating' : ''}`} aria-live="polite">
    <div className="report-hero">
      <div className="report-hero-copy">
        <span className="workspace-label">Your area report{placeName ? ` · ${placeName}` : ''}</span>
        <h2>{place.headline || profile.headline}</h2>
        {place.summary ? <p className="hero-summary">{place.summary}</p> : null}
        <div className="hero-stats">
          <div><span>Buildings & roads</span><strong>{format(profile.built_percent, 0)}%</strong></div>
          <div><span>Water</span><strong>{format(profile.water_percent, 0)}%</strong></div>
          <div><span>Result reliability</span><strong className={`reliability-${reliability.level}`}>{reliability.level === 'high' ? 'High' : reliability.level === 'medium' ? 'Medium' : 'Low'}</strong></div>
        </div>
      </div>
      <div className="green-score" style={{ ['--angle' as string]: `${greenAngle}deg` }} role="img" aria-label={`Green cover ${profile.green_cover.percent} percent, rated ${profile.green_cover.label}`}>
        <div><strong>{format(profile.green_cover.percent, 0)}%</strong><span>green cover</span><em>{profile.green_cover.label}</em></div>
      </div>
    </div>

    <div className="report-grid">
      <Panel title="Land map" detail="Each square shows its main land type. Hover a square to see its full mix." action={<button type="button" className="text-button no-print" onClick={() => setOverlay(!overlay)}>{overlay ? <EyeSlash size={15}/> : <Eye size={15}/>}{overlay ? 'Hide colours' : 'Show colours'}</button>}>
        <SceneMap image={result.image} rows={result.grid.rows} cols={result.grid.cols} cells={cells} overlay={overlay} alt="Satellite view with land types coloured" caption={<LandLegend types={LAND_ORDER.filter(type => result.tiles.some(tile => tile.land_type === type))}/>}/>
      </Panel>
      <div className="report-side">
        <Panel title="What this area is made of" detail="Share of the whole image, including small patches inside squares">
          <div className="land-stack" aria-hidden="true">{shown.map(item => <i key={item.land_type} style={{ width: `${item.percent}%`, background: LAND[item.land_type].color }}/>)}</div>
          <ul className="land-rows">{LAND_ORDER.filter(type => type !== 'mixed').map(type => { const item = result.breakdown.find(entry => entry.land_type === type); const { Icon } = LAND[type]; return <li key={type} className={item && item.percent > 0 ? '' : 'is-empty'}><span className="land-row-icon" style={{ background: LAND[type].color }}><Icon size={15} weight="bold"/></span><span><strong>{LAND[type].label}</strong><small>{LAND[type].plain}</small></span><b>{format(item?.percent ?? 0, 0)}%</b></li>; })}</ul>
        </Panel>
        {place.features.length ? <Panel title="What stands out"><ul className="evidence">{place.features.map(item => <li key={item}>{item}</li>)}</ul></Panel> : null}
        <Panel title="Things to consider">
          <ul className="considerations">{profile.considerations.map(item => <li key={item.topic} className={`tone-${item.tone}`}>{item.tone === 'good' ? <CheckCircle size={19} weight="fill"/> : item.tone === 'watch' ? <Warning size={19} weight="fill"/> : <Info size={19} weight="fill"/>}<span><strong>{item.topic}</strong>{item.text}</span></li>)}</ul>
        </Panel>
      </div>
    </div>

    {result.warnings.map(warning => <Notice key={warning}>{warning}</Notice>)}
    {place.quality_notes.length ? <Notice><strong>About this image:</strong> {place.quality_notes.join(' ')}</Notice> : null}
    <Notice warning={reliability.level === 'low'}><strong>Reliability: {reliability.level}.</strong> {reliability.note}</Notice>

    <div className="report-actions no-print">
      <button type="button" className="button button-primary" onClick={() => window.print()}><Printer size={17}/>Save report as PDF</button>
      <button type="button" className="button button-outline" onClick={() => downloadJson({ ...result, image: undefined }, 'terralens-area-report.json')}><DownloadSimple size={17}/>Download data</button>
    </div>
    <HowItWorks method={result.method}/>
    <p className="source-line">An AI-assisted estimate from the image, not a survey or legal record.</p>
  </section>;
}
