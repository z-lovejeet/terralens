import { useEffect, useRef, useState, type ReactNode } from 'react';
import { CaretDown, ImageSquare, Lightbulb, UploadSimple, X } from '@phosphor-icons/react';
import { format } from '../api';

export interface MapCell { color: string | null; label: string; emphasis?: 'strong' | 'dim' | 'outline' }

/** A satellite image with an optional colour-coded tile grid laid over it. */
export function SceneMap({ image, rows, cols, cells, overlay, alt, caption }: {
  image: string; rows: number; cols: number; cells: MapCell[]; overlay: boolean; alt: string; caption?: ReactNode;
}) {
  return <figure className="scene-map">
    <div className="scene-map-frame" style={{ aspectRatio: `${cols} / ${rows}` }}>
      <img src={image} alt={alt}/>
      <div className={`scene-grid ${overlay ? 'is-visible' : ''}`} style={{ gridTemplateColumns: `repeat(${cols}, 1fr)`, gridTemplateRows: `repeat(${rows}, 1fr)` }} aria-hidden="true">
        {cells.map((cell, index) => <span key={index} title={cell.label} className={cell.emphasis ? `is-${cell.emphasis}` : undefined} style={cell.color ? { ['--cell' as string]: cell.color } : undefined}/>)}
      </div>
    </div>
    {caption ? <figcaption>{caption}</figcaption> : null}
  </figure>;
}

/** Drop zone for one image, with preview. */
export function ImageDrop({ label, hint, file, onChoose, onClear, disabled, maxBytes }: {
  label: string; hint: string; file: File | null; onChoose: (file: File) => void; onClear: () => void; disabled?: boolean; maxBytes: number;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState('');
  const [dragging, setDragging] = useState(false);
  useEffect(() => {
    if (!file) { setPreview(''); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  return <div className={['image-drop', dragging && 'is-dragging', file && 'has-image'].filter(Boolean).join(' ')}
    onDragOver={event => { event.preventDefault(); if (!disabled) setDragging(true); }}
    onDragLeave={() => setDragging(false)}
    onDrop={event => { event.preventDefault(); setDragging(false); const dropped = event.dataTransfer.files[0]; if (dropped && !disabled) onChoose(dropped); }}>
    <span className="image-drop-label">{label}</span>
    {file && preview ? <>
      <img src={preview} alt={`${label} preview`}/>
      <div className="image-drop-file"><ImageSquare size={16}/><span>{file.name}</span><small>{format(file.size / 1024, 0)} KB</small></div>
      <button type="button" className="icon-button image-drop-remove" aria-label={`Remove ${label.toLowerCase()} image`} onClick={onClear} disabled={disabled}><X size={16}/></button>
    </> : <button type="button" className="image-drop-empty" onClick={() => input.current?.click()} disabled={disabled}>
      <UploadSimple size={28} weight="light"/>
      <strong>Drop or choose an image</strong>
      <small>{hint}</small>
      <small>JPEG, PNG or WebP · up to {format(maxBytes / 1024 / 1024, 0)} MB</small>
    </button>}
    <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="visually-hidden" tabIndex={-1} aria-label={`Upload ${label.toLowerCase()} image`} disabled={disabled}
      onChange={event => { const chosen = event.currentTarget.files?.[0]; event.currentTarget.value = ''; if (chosen) onChoose(chosen); }}/>
  </div>;
}

export function Segmented<T extends string>({ value, onChange, options, label }: { value: T; onChange: (value: T) => void; options: { id: T; label: string }[]; label: string }) {
  return <div className="segmented" role="radiogroup" aria-label={label}>{options.map(option => <button type="button" role="radio" aria-checked={value === option.id} key={option.id} className={value === option.id ? 'is-active' : ''} onClick={() => onChange(option.id)}>{option.label}</button>)}</div>;
}

export function ScreenshotTips() {
  return <details className="tips">
    <summary><Lightbulb size={17}/>How do I get a satellite image of my area?<CaretDown size={14}/></summary>
    <ol>
      <li>Open <strong>Google Maps</strong> (or Bing Maps) and switch to <strong>Satellite</strong> view.</li>
      <li>Turn off labels if you can, and keep the view flat (no 3D tilt).</li>
      <li>Zoom out until a whole neighbourhood or a few fields fill the screen, roughly 1–3 km across.</li>
      <li>Take a screenshot and upload it here. For before/after, take both at the same zoom and position.</li>
    </ol>
  </details>;
}

export function HowItWorks({ method, children }: { method: string; children?: ReactNode }) {
  return <details className="how-it-works">
    <summary>How does this work?<CaretDown size={14}/></summary>
    <div><p>{method}</p>{children}</div>
  </details>;
}
