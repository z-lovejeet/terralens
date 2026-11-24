import { useEffect, useRef, useState } from 'react';
import { DownloadSimple, FolderOpen, Images, MagnifyingGlass, SquaresFour, Trash, UploadSimple, WarningCircle } from '@phosphor-icons/react';
import { downloadJson, format, request } from './api';
import { clusterColor } from './Charts';
import { Notice, Panel } from './UI';
import { LAND, LAND_ORDER, LandChip } from './scenes/land';
import { HowItWorks, Segmented } from './scenes/SceneParts';
import './scenes/scenes.css';
import './sort/sort.css';
import type { LandType, SortGroup, SortResult } from './types';

const MAX_PHOTOS = 300;
const MIN_PHOTOS = 4;
const SHRINK_TO = 192;  // px; the model reads 64 x 64 squares, so a small copy keeps uploads fast
type Prepared = { name: string; blob: Blob; url: string };
type ViewMode = 'look' | 'land';

/** Shrink each photo in the browser so a batch of hundreds uploads in seconds. */
async function shrink(file: File): Promise<Prepared> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, SHRINK_TO / Math.min(bitmap.width, bitmap.height));
  const canvas = Object.assign(document.createElement('canvas'), { width: Math.round(bitmap.width * scale), height: Math.round(bitmap.height * scale) });
  canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(b => (b ? resolve(b) : reject(new Error('Could not read ' + file.name))), 'image/jpeg', 0.9));
  return { name: file.name, blob, url: URL.createObjectURL(blob) };
}

export default function SortPhotos() {
  const fileInput = useRef<HTMLInputElement>(null);
  const folderInput = useRef<HTMLInputElement>(null);
  const [photos, setPhotos] = useState<Prepared[]>([]);
  const [groups, setGroups] = useState<string>('auto');
  const [result, setResult] = useState<SortResult | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);

  useEffect(() => () => photos.forEach(photo => URL.revokeObjectURL(photo.url)), [photos]);

  async function add(files: FileList | File[]) {
    const images = [...files].filter(file => /^image\/(jpeg|png|webp)$/.test(file.type));
    if (!images.length) { setError('Choose JPEG, PNG or WebP satellite images.'); return; }
    const room = MAX_PHOTOS - photos.length;
    setPreparing(true); setError('');
    try {
      const ready = await Promise.all(images.slice(0, room).map(shrink));
      setPhotos(current => [...current, ...ready]);
      setResult(null);
      if (images.length > room) setError(`Only the first ${MAX_PHOTOS} photos are used.`);
    } catch (e) { setError((e as Error).message); }
    finally { setPreparing(false); }
  }

  async function sort(choice: string = groups) {
    if (photos.length < MIN_PHOTOS) { setError(`Add at least ${MIN_PHOTOS} photos.`); return; }
    const form = new FormData();
    photos.forEach(photo => form.append('files', photo.blob, photo.name));
    form.append('groups', choice);
    setBusy(true); setError('');
    try { setResult(await request<SortResult>('/sort-photos', { method: 'POST', body: form })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  const clear = () => { setPhotos([]); setResult(null); setError(''); };
  useEffect(() => { if (groups !== 'auto' && photos.length > 0 && Number(groups) >= photos.length) setGroups('auto'); }, [photos.length, groups]);
  const MAX_GROUPS = 12;
  const groupOptions = ['auto', ...Array.from({ length: MAX_GROUPS - 1 }, (_, i) => String(i + 2))];
  // A count is only possible when there are more photos than groups; before any photos are added, every option is shown.
  const tooFew = (value: string) => value !== 'auto' && photos.length > 0 && Number(value) >= photos.length;

  return <div className="view-panel scene-view sort-view">
    <div className="view-header">
      <div className="view-header-title">
        <span className="badge badge-primary"><SquaresFour size={14} weight="bold"/> Unsupervised sorting</span>
        <h1>Sort my photos</h1>
        <p className="lead">Drop a batch of satellite land images. TerraLens groups them by how they look, without being told any categories, finds a sensible number of groups by itself, and points out photos that don't fit.</p>
      </div>
    </div>

    <Panel title="Add your satellite images" detail={`Between ${MIN_PHOTOS} and ${MAX_PHOTOS} top-down land images: fields, forests, towns, rivers and so on.`} className="scene-controls no-print">
      <div className={['batch-drop', dragging && 'is-dragging'].filter(Boolean).join(' ')}
        onDragOver={event => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={event => { event.preventDefault(); setDragging(false); add(event.dataTransfer.files); }}>
        {photos.length ? <div className="batch-strip">{photos.slice(0, 40).map((photo, index) => <img key={photo.url} src={photo.url} alt={photo.name} title={photo.name} loading={index > 20 ? 'lazy' : 'eager'}/>)}{photos.length > 40 ? <span className="batch-more">+{photos.length - 40}</span> : null}</div>
          : <div className="batch-empty"><Images size={34} weight="light"/><strong>Drop satellite images here</strong><small>JPEG, PNG or WebP. Each photo is shrunk in your browser before upload.</small></div>}
        <div className="batch-actions">
          <button type="button" className="button button-outline" onClick={() => fileInput.current?.click()} disabled={busy || preparing}><UploadSimple size={16}/>Choose photos</button>
          <button type="button" className="button button-outline" onClick={() => folderInput.current?.click()} disabled={busy || preparing}><FolderOpen size={16}/>Choose a folder</button>
          {photos.length ? <button type="button" className="text-button" onClick={clear} disabled={busy}><Trash size={15}/>Remove all</button> : null}
          <span className="batch-count">{preparing ? 'Preparing photos…' : `${photos.length} photo${photos.length === 1 ? '' : 's'} ready`}</span>
        </div>
        <input ref={fileInput} type="file" multiple accept="image/jpeg,image/png,image/webp" className="visually-hidden" tabIndex={-1} aria-label="Choose satellite photos"
          onChange={event => { if (event.currentTarget.files) add(event.currentTarget.files); event.currentTarget.value = ''; }}/>
        <input ref={folderInput} type="file" multiple className="visually-hidden" tabIndex={-1} aria-label="Choose a folder of satellite photos"
          {...({ webkitdirectory: '' } as Record<string, string>)}
          onChange={event => { if (event.currentTarget.files) add(event.currentTarget.files); event.currentTarget.value = ''; }}/>
      </div>
      <div className="scene-run-row">
        <label className="group-count">Number of groups
          <select value={groups} onChange={event => { setGroups(event.target.value); if (result) sort(event.target.value); }} disabled={busy}>
            {groupOptions.map(value => <option key={value} value={value} disabled={tooFew(value)}>{value === 'auto' ? 'Auto (recommended)' : `${value} groups`}{tooFew(value) ? ' (add more photos)' : ''}</option>)}
          </select>
        </label>
        <button className="button button-primary" type="button" disabled={busy || preparing || photos.length < MIN_PHOTOS} onClick={() => sort()}>
          {busy ? <span className="loading-dots"/> : <MagnifyingGlass size={18}/>}{busy ? 'Sorting…' : 'Sort photos'}
        </button>
      </div>
      {error ? <Notice warning>{error}</Notice> : null}
    </Panel>

    {result ? <SortReport result={result} photos={photos} busy={busy} onPickK={k => { setGroups(String(k)); sort(String(k)); }}/> : null}
  </div>;
}

function SortReport({ result, photos, busy, onPickK }: { result: SortResult; photos: Prepared[]; busy: boolean; onPickK: (k: number) => void }) {
  const [mode, setMode] = useState<ViewMode>('look');
  const byLand = LAND_ORDER.map(type => ({ type, members: result.photos.filter(photo => photo.land_type === type).map(photo => photo.index) })).filter(entry => entry.members.length);
  const outliers = result.photos.filter(photo => photo.outlier || photo.unfamiliar);
  const maxInertia = Math.max(...result.candidates.map(item => item.inertia), 0.0001);

  function exportCsv() {
    const rows = [['file', 'group', 'land_type', 'does_not_fit', 'unfamiliar'], ...result.photos.map(photo => [photo.name, String(photo.group + 1), LAND[photo.land_type].label, photo.outlier ? 'yes' : 'no', photo.unfamiliar ? 'yes' : 'no'])];
    const text = rows.map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([text], { type: 'text/csv' }));
    const link = Object.assign(document.createElement('a'), { href: url, download: 'terralens-photo-groups.csv' });
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <section className={`scene-report ${busy ? 'is-updating' : ''}`} aria-live="polite">
    <div className="sort-summary">
      <div>
        <span className="workspace-label">Result</span>
        <h2>{result.photo_count} photos sorted into {result.k} groups</h2>
        <p>{result.chosen === 'automatic' ? 'The number of groups was chosen automatically with the elbow method: ' : 'You chose the number of groups. '}
          {result.separation === 'clear' ? 'the groups are clearly different from each other.' : result.separation === 'moderate' ? 'the groups are somewhat different, with some overlap.' : 'the groups overlap a lot, so treat them as rough.'}</p>
        <div className="hero-stats sort-stats">
          <div><span>Separation</span><strong className={`sep-${result.separation}`}>{result.separation === 'clear' ? 'Clear' : result.separation === 'moderate' ? 'Moderate' : 'Weak'}</strong></div>
          <div><span>Silhouette score</span><strong>{result.silhouette == null ? '—' : format(result.silhouette, 2)}</strong></div>
          <div><span>Don't fit well</span><strong>{outliers.length}</strong></div>
        </div>
      </div>
      {result.candidates.length ? <figure className="k-chart" aria-label="Spread inside the groups for each number of groups">
        <figcaption>Spread inside the groups for each number of groups. More groups are always tighter; the elbow is where adding more stops helping much. Click a bar to try it.</figcaption>
        <div className="k-bars">{result.candidates.map(item => <button type="button" key={item.k} className={item.k === result.k ? 'is-chosen' : ''} onClick={() => onPickK(item.k)} disabled={busy} title={`${item.k} groups: spread ${item.inertia.toFixed(0)}, silhouette ${item.silhouette.toFixed(2)}`}>
          <i style={{ height: `${Math.max(6, (item.inertia / maxInertia) * 100)}%` }}/><span>{item.k}</span>
        </button>)}</div>
      </figure> : null}
    </div>

    {result.unfamiliar_percent >= 30 ? <Notice warning>{format(result.unfamiliar_percent, 0)}% of these photos don't look like the satellite land images the model learned from. Use top-down satellite views of land for meaningful groups.</Notice> : null}

    <div className="sort-toolbar no-print">
      <Segmented<ViewMode> label="Group photos by" value={mode} onChange={setMode} options={[{ id: 'look', label: 'Similar look' }, { id: 'land', label: 'Land type' }]}/>
      <span className="caption">{mode === 'look' ? 'Groups discovered from your photos alone.' : 'Each photo labelled by the 30-group land model.'}</span>
    </div>

    <div className="sort-groups">
      {mode === 'look'
        ? result.groups.map(group => <GroupCard key={group.group} group={group} result={result} photos={photos}/>)
        : byLand.map(entry => <LandCard key={entry.type} type={entry.type} members={entry.members} result={result} photos={photos}/>)}
    </div>

    <div className="report-grid report-grid-even">
      <Panel title="Map of your photos" detail="Photos close together look alike. Positions use the study's first two principal components.">
        <PhotoMap result={result}/>
      </Panel>
      <Panel title="Photos that don't fit well" detail="Far from the rest of their group, or unlike satellite land.">
        {outliers.length ? <ul className="outlier-list">{outliers.map(photo => <li key={photo.index}>
          <img src={photos[photo.index]?.url} alt=""/>
          <span><strong>{photo.name}</strong><small>{photo.unfamiliar ? "Doesn't look like satellite land" : `Unusual for group ${photo.group + 1}`}</small></span>
        </li>)}</ul> : <p className="fine">Every photo sits comfortably in its group.</p>}
      </Panel>
    </div>

    <div className="report-actions no-print">
      <button type="button" className="button button-primary" onClick={exportCsv}><DownloadSimple size={17}/>Download groups (CSV)</button>
      <button type="button" className="button button-outline" onClick={() => downloadJson(result, 'terralens-photo-groups.json')}><DownloadSimple size={17}/>Download full result</button>
    </div>
    <HowItWorks method={result.method}>
      <p>Measured on held-out EuroSAT patches: when photos show clearly different land (for example forest, lakes and towns), groups are about 76–80% pure. When they are broad mixes of similar-looking land, groups are only about half pure, because colour and texture alone cannot separate them. The land-type view matches the reference land type for 69.6% of held-out patches.</p>
    </HowItWorks>
  </section>;
}

function Thumbs({ members, result, photos }: { members: number[]; result: SortResult; photos: Prepared[] }) {
  return <div className="thumbs">{members.map((index, position) => {
    const photo = result.photos[index];
    return <figure key={index} className={[photo.outlier && 'is-outlier', photo.unfamiliar && 'is-unfamiliar'].filter(Boolean).join(' ')} title={`${photo.name} · ${LAND[photo.land_type].label}${photo.outlier ? ' · does not fit well' : ''}`}>
      <img src={photos[index]?.url} alt={photo.name} loading="lazy"/>
      {position === 0 ? <figcaption>Most typical</figcaption> : photo.outlier || photo.unfamiliar ? <figcaption className="warn"><WarningCircle size={11}/>Odd one out</figcaption> : null}
    </figure>;
  })}</div>;
}

function GroupCard({ group, result, photos }: { group: SortGroup; result: SortResult; photos: Prepared[] }) {
  return <section className="sort-group">
    <header>
      <i className="colour-dot" style={{ background: clusterColor(group.group) }}/>
      <h3>Group {group.group + 1}</h3>
      <span className="group-size">{group.size} photo{group.size === 1 ? '' : 's'}</span>
    </header>
    <p className="group-land"><LandChip type={group.land_type}/><span>{Math.round(group.land_share * 100)}% of this group</span></p>
    <p className="group-desc">{group.description.join(' · ')}</p>
    <Thumbs members={group.members} result={result} photos={photos}/>
  </section>;
}

function LandCard({ type, members, result, photos }: { type: LandType; members: number[]; result: SortResult; photos: Prepared[] }) {
  return <section className="sort-group">
    <header><LandChip type={type}/><span className="group-size">{members.length} photo{members.length === 1 ? '' : 's'}</span></header>
    <p className="group-desc">{LAND[type].plain}</p>
    <Thumbs members={members} result={result} photos={photos}/>
  </section>;
}

function PhotoMap({ result }: { result: SortResult }) {
  const xs = result.photos.map(photo => photo.pca[0]), ys = result.photos.map(photo => photo.pca[1]);
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const sx = (x: number) => 20 + ((x - minX) / (maxX - minX || 1)) * 360;
  const sy = (y: number) => 260 - ((y - minY) / (maxY - minY || 1)) * 240;
  return <svg className="photo-map" viewBox="0 0 400 280" role="img" aria-label="Scatter map of the photos coloured by group">
    <rect x="0" y="0" width="400" height="280" rx="8" className="photo-map-bg"/>
    {result.photos.map(photo => <circle key={photo.index} cx={sx(photo.pca[0])} cy={sy(photo.pca[1])} r={photo.outlier ? 5.5 : 4.5}
      fill={clusterColor(photo.group)} stroke={photo.outlier ? 'var(--color-danger)' : 'var(--color-surface)'} strokeWidth={photo.outlier ? 2 : 1}>
      <title>{photo.name} · group {photo.group + 1}</title>
    </circle>)}
  </svg>;
}
