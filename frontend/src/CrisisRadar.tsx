import { useState } from 'react';
import { Siren } from '@phosphor-icons/react';
import { Segmented } from './scenes/SceneParts';
import CompareView from './radar/CompareView';
import ScanView from './radar/ScanView';
import './scenes/scenes.css';
import './radar/radar.css';
import type { Capabilities } from './types';

type Mode = 'scan' | 'compare';

export default function CrisisRadar({ capabilities }: { capabilities: Capabilities }) {
  const [mode, setMode] = useState<Mode>('scan');
  return <div className="view-panel scene-view radar-view">
    <div className="radar-head">
      <div>
        <span className="badge badge-primary"><Siren size={14} weight="bold"/> Everyday tool</span>
        <h1>Crisis Radar</h1>
        <p className="lead">{mode === 'scan'
          ? 'Upload one satellite or aerial image. Crisis Radar checks it for floods, fires, drought, landslides, storm damage and more, marks what it found, and says what to do next.'
          : 'Compare two views of the same place taken at different times to see what changed: water spreading, lakes shrinking, trees cleared or new buildings.'}</p>
      </div>
      <div className="no-print"><Segmented<Mode> label="Radar mode" value={mode} onChange={setMode} options={[{ id: 'scan', label: 'Scan one image' }, { id: 'compare', label: 'Compare before & after' }]}/></div>
    </div>
    {mode === 'scan' ? <ScanView capabilities={capabilities}/> : <CompareView capabilities={capabilities}/>}
  </div>;
}
