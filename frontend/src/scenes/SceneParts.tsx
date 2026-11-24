import { useEffect, useRef, useState, type ReactNode } from 'react';
import { CaretDown, ImageSquare, UploadSimple, X } from '@phosphor-icons/react';
import { format } from '../api';

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

export function HowItWorks({ method, children }: { method: string; children?: ReactNode }) {
  return <details className="how-it-works">
    <summary>How does this work?<CaretDown size={14}/></summary>
    <div><p>{method}</p>{children}</div>
  </details>;
}
