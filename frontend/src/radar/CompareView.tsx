import { useState } from 'react';
import { ArrowRight, CheckCircle, DownloadSimple, MagnifyingGlass, Printer, Warning, WarningOctagon } from '@phosphor-icons/react';
import { downloadJson, format, request } from '../api';
import { Notice, Panel } from '../UI';
import { GroupNames, LAND, LAND_ORDER, LandChip, LandLegend } from '../scenes/land';
import { HowItWorks, ImageDrop, SceneMap, ScreenshotTips, Segmented, type MapCell } from '../scenes/SceneParts';
import type { Capabilities, ChangeCheckResult } from '../types';

type MapMode = 'changes' | 'land';
const LEVEL_TEXT = { none: 'All clear', small: 'Small change', noticeable: 'Noticeable change', major: 'Major change' } as const;

export default function CompareView({ capabilities }: { capabilities: Capabilities }) {
  const [before, setBefore] = useState<File | null>(null);
  const [after, setAfter] = useState<File | null>(null);
  const [result, setResult] = useState<ChangeCheckResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function run(files: [File | null, File | null] = [before, after]) {
    const [first, second] = files;
    if (!first || !second) return;
    const form = new FormData();
    form.append('detail', 'medium');  // the clustering model reads best at this square size
    form.append('before', first);
    form.append('after', second);
    setBusy(true); setError('');
    try { setResult(await request<ChangeCheckResult>('/change-check', { method: 'POST', body: form })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return <>
    <Panel title="Upload a before and an after image" detail="Two screenshots of the same place, at the same zoom, taken at different times." className="scene-controls no-print">
      <div className="upload-layout">
        <div className="pair-drops">
          <ImageDrop label="Before (older)" hint="The earlier view" file={before} onChoose={file => { setBefore(file); run([file, after]); }} onClear={() => setBefore(null)} disabled={busy} maxBytes={capabilities.upload_max_bytes}/>
          <ImageDrop label="After (newer)" hint="Same place, later" file={after} onChoose={file => { setAfter(file); run([before, file]); }} onClear={() => setAfter(null)} disabled={busy} maxBytes={capabilities.upload_max_bytes}/>
        </div>
        <ScreenshotTips/>
      </div>
      <div className="scene-run-row">
        <button className="button button-primary" type="button" disabled={busy || !(before && after)} onClick={() => run()}>
          {busy ? <span className="loading-dots"/> : <MagnifyingGlass size={18}/>}{busy ? 'Comparing…' : 'Find changes'}
        </button>
      </div>
      {error ? <Notice warning>{error}</Notice> : null}
    </Panel>
    {result ? <ChangeReport result={result} busy={busy}/> : busy ? <div className="view-skeleton" role="status" aria-label="Comparing images"><div/><div/><div/></div> : null}
  </>;
}

function ChangeReport({ result, busy }: { result: ChangeCheckResult; busy: boolean }) {
  const [mode, setMode] = useState<MapMode>('changes');
  const { summary, verdict } = result;
  const cellsFor = (side: 'before' | 'after'): MapCell[] => result.tiles.map(tile => {
    const type = tile[side];
    if (mode === 'land') return { color: LAND[type].color, label: LAND[type].label };
    if (tile.change === 'type') return { color: LAND[type].color, label: `${LAND[tile.before].label} → ${LAND[tile.after].label}`, emphasis: 'strong' };
    if (tile.change === 'look') return { color: null, label: 'Same land type, but looks different', emphasis: 'outline' };
    return { color: null, label: 'No change', emphasis: 'dim' };
  });
  const changedTypes = [...new Set(result.tiles.filter(tile => tile.change === 'type').flatMap(tile => [tile.before, tile.after]))];
  const legendTypes = mode === 'land' ? LAND_ORDER.filter(type => result.tiles.some(tile => tile.before === type || tile.after === type)) : LAND_ORDER.filter(type => changedTypes.includes(type));
  const LevelIcon = summary.level === 'major' ? WarningOctagon : summary.level === 'none' ? CheckCircle : Warning;

  return <section className={`scene-report ${busy ? 'is-updating' : ''}`} aria-live="polite">
    <div className={`verdict verdict-${summary.level}`}>
      <LevelIcon size={40} weight="fill"/>
      <div>
        <span className="verdict-level">{LEVEL_TEXT[summary.level]} · {format(summary.changed_percent, 0)}% of the area changed</span>
        <h2>{verdict.title}</h2>
        <p>{verdict.explanation}</p>
      </div>
    </div>

    <Panel title="Before and after" detail={mode === 'changes' ? 'Coloured squares changed land type. Faded squares stayed the same.' : 'Every square coloured by the land type the model sees.'} action={<Segmented<MapMode> label="Map view" value={mode} onChange={setMode} options={[{ id: 'changes', label: 'Changes only' }, { id: 'land', label: 'All land types' }]}/>}>
      <div className="pair-maps">
        <SceneMap image={result.before_image} rows={result.grid.rows} cols={result.grid.cols} cells={cellsFor('before')} overlay alt="Before view" caption={<strong>Before</strong>}/>
        <SceneMap image={result.after_image} rows={result.grid.rows} cols={result.grid.cols} cells={cellsFor('after')} overlay alt="After view" caption={<strong>After</strong>}/>
      </div>
      {legendTypes.length ? <LandLegend types={legendTypes}/> : <p className="caption">No squares changed land type.</p>}
      {mode === 'changes' && summary.look_changed_percent > 0 ? <p className="caption">Squares with a dashed outline kept their land type but look noticeably different ({format(summary.look_changed_percent, 0)}% of the area).</p> : null}
    </Panel>

    <div className="report-grid report-grid-even">
      <Panel title="What changed">
        <table className="delta-table">
          <thead><tr><th scope="col">Land type</th><th scope="col">Before</th><th scope="col">After</th><th scope="col">Change</th></tr></thead>
          <tbody>{result.deltas.filter(row => row.before || row.after).map(row => <tr key={row.land_type}><td><LandChip type={row.land_type}/></td><td>{format(row.before, 0)}%</td><td>{format(row.after, 0)}%</td><td className={row.change > 0 ? 'is-up' : row.change < 0 ? 'is-down' : ''}>{row.change === 0 ? 'No change' : `${row.change > 0 ? '▲ +' : '▼ −'}${format(Math.abs(row.change), 0)} pts`}</td></tr>)}</tbody>
        </table>
        {result.transitions.length ? <><h3 className="sub-heading">Biggest shifts</h3><ul className="shift-list">{result.transitions.map(item => <li key={`${item.from}-${item.to}`}><LandChip type={item.from}/><ArrowRight size={14}/><LandChip type={item.to}/><b>{format(item.percent, 0)}%</b></li>)}</ul></> : null}
      </Panel>
      <Panel title="What you can do">
        <ol className="next-steps">{verdict.next_steps.map(step => <li key={step}>{step}</li>)}</ol>
        <p className="caption">These are general suggestions based on the pattern of change. Always confirm with local authorities or news before acting.</p>
      </Panel>
    </div>

    {result.warnings.map(warning => <Notice key={warning} warning>{warning}</Notice>)}
    {(['before', 'after'] as const).filter(side => result.reliability[side].level !== 'high').map(side => <Notice key={side}><strong>{side === 'before' ? 'Before' : 'After'} image reliability: {result.reliability[side].level}.</strong> {result.reliability[side].note}</Notice>)}

    <div className="report-actions no-print">
      <button type="button" className="button button-primary" onClick={() => window.print()}><Printer size={17}/>Save report as PDF</button>
      <button type="button" className="button button-outline" onClick={() => downloadJson({ ...result, before_image: undefined, after_image: undefined }, 'terralens-crisis-radar.json')}><DownloadSimple size={17}/>Download data</button>
    </div>
    <HowItWorks method={result.method}><GroupNames groups={result.groups}/></HowItWorks>
    <p className="caption print-only">TerraLens · Crisis Radar · model {result.run_id}. An educational estimate from satellite imagery; confirm with local authorities before acting.</p>
  </section>;
}
