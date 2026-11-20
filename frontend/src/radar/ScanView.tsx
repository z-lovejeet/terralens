import { useEffect, useRef, useState } from 'react';
import { ArrowCounterClockwise, CheckCircle, DownloadSimple, Printer, Question, UploadSimple, Warning, WarningOctagon } from '@phosphor-icons/react';
import { downloadJson, format, request } from '../api';
import { Notice } from '../UI';
import { LAND, LandLegend } from '../scenes/land';
import { ScreenshotTips, Segmented } from '../scenes/SceneParts';
import type { Capabilities, CrisisAssessment, CrisisScanResult } from '../types';
import { CRISIS, HAZARD_GROUPS, SEVERITY_SCALE, crisisInfo } from './crisisTypes';

type Layer = 'photo' | 'marks' | 'land';
const ACCEPT = 'image/jpeg,image/png,image/webp';
const COLUMNS = 'ABCDEFGHIJKL';
const IMAGE_KIND: Record<CrisisAssessment['image_kind'], string> = {
  satellite: 'Satellite', aerial: 'Aerial', ground_photo: 'Ground photo', map_or_graphic: 'Map or graphic', other: 'Other',
};

export default function ScanView({ capabilities }: { capabilities: Capabilities }) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [result, setResult] = useState<CrisisScanResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    if (!file) { setPreview(''); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function scan(chosen: File) {
    setFile(chosen); setResult(null); setError(''); setBusy(true);
    const form = new FormData();
    form.append('file', chosen);
    try { setResult(await request<CrisisScanResult>('/crisis-scan', { method: 'POST', body: form })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  const reset = () => { setFile(null); setResult(null); setError(''); };
  const picker = <input ref={input} type="file" accept={ACCEPT} className="visually-hidden" tabIndex={-1} aria-label="Upload a satellite image to scan"
    onChange={event => { const chosen = event.currentTarget.files?.[0]; event.currentTarget.value = ''; if (chosen) scan(chosen); }}/>;

  if (!file) return <section className="scan-start">
    <div className={`viewfinder ${dragging ? 'is-dragging' : ''}`}
      onDragOver={event => { event.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={event => { event.preventDefault(); setDragging(false); const dropped = event.dataTransfer.files[0]; if (dropped) scan(dropped); }}>
      <span className="corner tl"/><span className="corner tr"/><span className="corner bl"/><span className="corner br"/>
      <UploadSimple size={34} weight="light"/>
      <h2>Drop one satellite or aerial image</h2>
      <p>Crisis Radar looks for signs of disaster or damage and tells you what it finds, in plain words.</p>
      <button type="button" className="button button-primary" onClick={() => input.current?.click()}>Choose an image</button>
      <small>JPEG, PNG or WebP · 128 px to 4096 px · up to {format(capabilities.upload_max_bytes / 1024 / 1024, 0)} MB</small>
      {picker}
    </div>
    <aside className="scan-catalogue">
      <h3>What it can spot</h3>
      <dl>{HAZARD_GROUPS.map(group => <div key={group}><dt>{group}</dt><dd>{Object.values(CRISIS).filter(item => item.group === group).map(item => item.label).join(' · ')}</dd></div>)}</dl>
      <ScreenshotTips/>
      {capabilities.crisis_scan === false ? <Notice warning>Image scanning is not configured on this server yet.</Notice> : null}
    </aside>
  </section>;

  return <section className="scan-session">
    <div className="scan-toolbar no-print">
      <span className="scan-file"><strong>{file.name}</strong><small>{format(file.size / 1024, 0)} KB</small></span>
      <button type="button" className="button button-outline" disabled={busy} onClick={() => input.current?.click()}><ArrowCounterClockwise size={16}/>Scan another image</button>
      <button type="button" className="text-button" disabled={busy} onClick={reset}>Start over</button>
      {picker}
    </div>
    {error ? <Notice warning>{error}</Notice> : null}
    {busy ? <div className="scan-pending" role="status">
      <div className="scan-pending-image">{preview ? <img src={preview} alt="Image being scanned"/> : null}<span className="scanline" aria-hidden="true"/></div>
      <p><strong>Scanning the image…</strong> Mapping land cover and checking for hazards. This usually takes 5–15 seconds.</p>
    </div> : result ? <ScanReport result={result}/> : null}
  </section>;
}

function ScanReport({ result }: { result: CrisisScanResult }) {
  const { assessment, land } = result;
  const [layer, setLayer] = useState<Layer>(assessment?.regions.length ? 'marks' : 'photo');
  return <div className="scan-report">
    {assessment ? <IncidentCard assessment={assessment}/> : <div className="incident incident-offline">
      <Question size={30}/>
      <div><span className="incident-kicker">Hazard check unavailable</span><h2>Only the land map could be made</h2><p>{result.vision_error?.message}</p></div>
    </div>}

    <div className="scan-body">
      <figure className="scan-figure">
        <div className="scan-layer-bar no-print">
          <Segmented<Layer> label="Image layer" value={layer} onChange={setLayer} options={[{ id: 'photo', label: 'Photo' }, ...(assessment?.regions.length ? [{ id: 'marks' as Layer, label: 'Marked areas' }] : []), { id: 'land', label: 'Land cover' }]}/>
        </div>
        <div className="grid-frame" style={{ ['--cols' as string]: land.grid.cols, ['--rows' as string]: land.grid.rows }}>
          <div className="axis axis-top" aria-hidden="true">{Array.from({ length: land.grid.cols }, (_, i) => <span key={i}>{COLUMNS[i]}</span>)}</div>
          <div className="axis axis-left" aria-hidden="true">{Array.from({ length: land.grid.rows }, (_, i) => <span key={i}>{i + 1}</span>)}</div>
          <div className="scan-image" style={{ aspectRatio: `${land.grid.cols} / ${land.grid.rows}` }}>
            <img src={result.image} alt="Scanned satellite image"/>
            <div className={`scan-grid ${layer === 'land' ? 'is-land' : ''}`} style={{ gridTemplateColumns: `repeat(${land.grid.cols}, 1fr)` }} aria-hidden="true">
              {land.tiles.map(tile => <span key={`${tile.row}-${tile.col}`} title={LAND[tile.land_type].label} style={layer === 'land' ? { background: `color-mix(in oklch, ${LAND[tile.land_type].color} 55%, transparent)` } : undefined}/>)}
            </div>
            {layer === 'marks' && assessment ? assessment.regions.map((region, index) => <div key={index} className="mark" style={{ top: `${region.top}%`, left: `${region.left}%`, width: `${region.width}%`, height: `${region.height}%` }}><b>{index + 1}</b></div>) : null}
          </div>
        </div>
        <figcaption>
          {layer === 'marks' && assessment ? <ol className="mark-key">{assessment.regions.map((region, index) => <li key={index}><b>{index + 1}</b>{region.label}</li>)}</ol>
            : layer === 'land' ? <LandLegend types={land.breakdown.filter(item => item.tiles).map(item => item.land_type)}/>
            : <span>Grid squares match the land-cover map. Use the letters and numbers to point at a spot.</span>}
        </figcaption>
      </figure>

      <div className="scan-details">
        {assessment ? <AssessmentDetails assessment={assessment}/> : null}
        <section className="scan-section">
          <h3>Land cover in this image</h3>
          <div className="land-stack" aria-hidden="true">{land.breakdown.filter(item => item.tiles).map(item => <i key={item.land_type} style={{ width: `${item.percent}%`, background: LAND[item.land_type].color }}/>)}</div>
          <ul className="land-inline">{land.breakdown.filter(item => item.tiles).map(item => <li key={item.land_type}><i style={{ background: LAND[item.land_type].color }}/>{item.label}<b>{format(item.percent, 0)}%</b></li>)}</ul>
          <p className="fine">Measured square by square from colour and texture. Reliability: {land.reliability.level}.</p>
        </section>
      </div>
    </div>

    <div className="report-actions no-print">
      <button type="button" className="button button-primary" onClick={() => window.print()}><Printer size={17}/>Save report as PDF</button>
      <button type="button" className="button button-outline" onClick={() => downloadJson({ ...result, image: undefined }, 'terralens-crisis-scan.json')}><DownloadSimple size={17}/>Download data</button>
    </div>
    {assessment ? <p className="source-note">An AI-assisted estimate from the image, which can be wrong. For real emergencies, follow official alerts and local authorities.</p> : null}
  </div>;
}

function IncidentCard({ assessment }: { assessment: CrisisAssessment }) {
  const info = crisisInfo(assessment.crisis_type);
  const tone = assessment.status === 'no_crisis' ? 'clear' : assessment.status === 'uncertain' ? 'unsure' : assessment.severity;
  const StatusIcon = assessment.status === 'no_crisis' ? CheckCircle : assessment.status === 'uncertain' ? Question : assessment.severity === 'severe' || assessment.severity === 'high' ? WarningOctagon : Warning;
  const kicker = assessment.status === 'no_crisis' ? 'No crisis visible' : assessment.status === 'uncertain' ? 'Cannot tell from this image' : `${info.group ?? 'Hazard'} · ${SEVERITY_SCALE.find(s => s.id === assessment.severity)?.label} severity`;
  const severityIndex = SEVERITY_SCALE.findIndex(step => step.id === assessment.severity);
  return <div className={`incident incident-${tone}`}>
    <div className="incident-type"><StatusIcon size={30} weight="fill"/>{assessment.status === 'crisis' ? <span><info.Icon size={16} weight="bold"/>{info.label}</span> : null}</div>
    <div className="incident-copy">
      <span className="incident-kicker">{kicker}</span>
      <h2>{assessment.headline}</h2>
      <p>{assessment.status === 'no_crisis' ? assessment.scene_description || assessment.summary : assessment.summary}</p>
      {assessment.secondary_types.length ? <p className="incident-also">Also possible: {assessment.secondary_types.map(type => crisisInfo(type).label).join(', ')}</p> : null}
    </div>
    <dl className="incident-facts">
      {assessment.status === 'crisis' ? <div className="fact-severity"><dt>Severity</dt><dd><span className="severity-meter" aria-label={`Severity ${assessment.severity}`}>{SEVERITY_SCALE.slice(1).map((step, index) => <i key={step.id} className={index < severityIndex ? 'is-on' : ''}/>)}</span>{SEVERITY_SCALE[severityIndex]?.label}</dd></div> : null}
      {assessment.status === 'crisis' && assessment.affected_area_percent != null ? <div><dt>Area affected</dt><dd>about {format(assessment.affected_area_percent, 0)}%</dd></div> : null}
      {assessment.confidence != null ? <div><dt>Scanner confidence</dt><dd>{format(assessment.confidence * 100, 0)}%</dd></div> : null}
      <div><dt>Image</dt><dd>{IMAGE_KIND[assessment.image_kind]}{assessment.cloud_cover !== 'none' ? `, ${assessment.cloud_cover} cloud` : ''}</dd></div>
    </dl>
  </div>;
}

function AssessmentDetails({ assessment }: { assessment: CrisisAssessment }) {
  return <>
    {assessment.evidence.length ? <section className="scan-section"><h3>What the scanner sees</h3><ul className="evidence">{assessment.evidence.map(item => <li key={item}>{item}</li>)}</ul></section> : null}
    {assessment.actions.length ? <section className="scan-section"><h3>{assessment.status === 'crisis' ? 'What to do now' : 'Suggested next steps'}</h3><ol className="next-steps">{assessment.actions.map(item => <li key={item}>{item}</li>)}</ol></section> : null}
    {assessment.secondary_risks.length ? <section className="scan-section"><h3>Also watch for</h3><ul className="evidence watch">{assessment.secondary_risks.map(item => <li key={item}>{item}</li>)}</ul></section> : null}
    {assessment.quality_notes.length ? <section className="scan-section"><h3>About this image</h3><ul className="evidence quiet">{assessment.quality_notes.map(item => <li key={item}>{item}</li>)}</ul></section> : null}
  </>;
}
