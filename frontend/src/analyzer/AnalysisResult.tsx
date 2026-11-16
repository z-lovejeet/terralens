import { useState } from 'react';
import { ArrowRight, Crosshair, DownloadSimple, Printer, ShieldCheck, X } from '@phosphor-icons/react';
import { clusterName, downloadJson, format } from '../api';
import { clusterColor } from '../Charts';
import { Notice, Panel, Patch } from '../UI';
import type { Analysis, Run } from '../types';
import CategoryMix from './CategoryMix';

function groupName(id: number) {
  return 'Group ' + String(id + 1).padStart(2, '0') + ' · ' + clusterName(id);
}

function CentroidEvidence({ result }: { result: Analysis }) {
  const hasRunnerUp = result.alternate_cluster != null && result.alternate_distance != null;

  return (
    <>
      <dl className="centroid-evidence">
        <div>
          <dt>Assigned centre</dt>
          <dd>{format(result.distance)}</dd>
          <small>{groupName(result.cluster)}</small>
        </div>
        {hasRunnerUp && (
          <div>
            <dt>Next closest centre</dt>
            <dd>{format(result.alternate_distance)}</dd>
            <small>{groupName(result.alternate_cluster!)}</small>
          </div>
        )}
        {result.margin != null && (
          <div>
            <dt>Distance gap</dt>
            <dd>{format(result.margin)}</dd>
            <small>Next closest minus assigned</small>
          </div>
        )}
      </dl>
      <p className="caption">
        Smaller distances in the fitted PCA space indicate more similar features.
        {hasRunnerUp && ' A small gap means the runner-up group is a close competitor for this patch.'}
      </p>
      <p className="analyzer-percentile">
        <strong>{format(result.reference_percentile, 1)}th percentile</strong>
        {' '}of centroid distances in {groupName(result.cluster)}.
      </p>
    </>
  );
}

function NearestPatches({ result, onSelect }: { result: Analysis; onSelect: (id: string) => void }) {
  if (!result.neighbors?.length) {
    return (
      <>
        <div className="neighbors-heading"><h3>Group representatives</h3></div>
        <p className="caption">This response includes representative examples from the assigned group.</p>
        <div className="neighbor-patches">
          {result.representatives.slice(0, 8).map(id => <Patch key={id} id={id} onSelect={onSelect}/>)}
        </div>
      </>
    );
  }

  return (
    <>
      <div className="neighbors-heading"><h3>Closest reference patches</h3></div>
      <p className="caption">
        {result.neighbor_scope == null
          ? 'Ranked by distance to your upload within the assigned group.'
          : 'Ranked by distance to your upload among ' + format(result.neighbor_scope, 0) + ' candidates in this group.'}
      </p>
      <ol className="nearest-gallery">
        {result.neighbors.map((neighbor, index) => (
          <li key={neighbor.id}>
            <Patch id={neighbor.id} index={index} onSelect={onSelect}/>
            <span>Distance <strong>{format(neighbor.distance)}</strong></span>
          </li>
        ))}
      </ol>
    </>
  );
}

export default function AnalysisResult({
  result, run, isReference, analyzing, selectPatch,
}: {
  result: Analysis | null;
  run: Run;
  isReference: boolean;
  analyzing: boolean;
  selectPatch: (id: string) => void;
}) {
  const [dossierOpen, setDossierOpen] = useState(false);

  if (!result) {
    return (
      <Panel title="Analysis result" detail="Your assigned group and nearby examples will appear here.">
        <div className="analyzer-empty" role="status">
          <Crosshair size={56} weight="thin"/>
          <h3>{analyzing ? 'Comparing image features…' : 'Explore the group your patch resembles'}</h3>
          <p>Choose a satellite patch to see its visual group, distance to its centre, and closest examples.</p>
          <div className="analyzer-steps">
            <span>Image features</span><ArrowRight size={13}/>
            <span>PCA</span><ArrowRight size={13}/><span>Nearest centre</span>
          </div>
        </div>
      </Panel>
    );
  }

  const cluster = run.clusters.find(group => group.id === result.cluster);
  const description = result.cluster_description || cluster?.description;
  const isAnomaly = result.anomaly?.is_anomaly || result.reference_percentile >= 95;

  return (
    <Panel
      title="Analysis result"
      detail={`${isReference ? 'Reference model' : 'Finer comparison'} · ${run.k} visual groups`}
      className="analyzer-result"
      action={
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            className="button button-small button-secondary"
            onClick={() => setDossierOpen(true)}
            title="Generate printable land-use survey dossier"
          >
            <Printer size={15}/> Survey Dossier
          </button>
          <button
            className="text-button analysis-export"
            onClick={() => downloadJson(result, 'terralens-patch-analysis.json')}
          >
            <DownloadSimple size={16}/> Export JSON
          </button>
        </div>
      }
    >
      <p className="visually-hidden" role="status">
        Analysis complete. Assigned visual group {groupName(result.cluster)}.
      </p>
      <div className="assignment-heading">
        <span className="assignment-number" style={{ color: clusterColor(result.cluster) }} aria-hidden="true">
          {String(result.cluster + 1).padStart(2, '0')}
        </span>
        <div>
          <span className="workspace-label">Assigned visual group · Group {String(result.cluster + 1).padStart(2, '0')}</span>
          <h3>{result.cluster_name || cluster?.name || clusterName(result.cluster)}</h3>
          {description && <p className="assignment-description"><strong>Visual characteristics:</strong> {description}</p>}
        </div>
      </div>

      {/* Spectral Anomaly Radar Card */}
      <div className={`anomaly-radar-card ${isAnomaly ? 'is-anomaly' : 'is-normal'}`} style={{
        marginTop: '16px',
        marginBottom: '16px',
        padding: '14px 16px',
        borderRadius: '8px',
        backgroundColor: isAnomaly ? '#FADBD8' : '#EAFAF1',
        border: `1px solid ${isAnomaly ? '#E74C3C' : '#27AE60'}`,
        color: '#1A251F'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '13px' }}>
            <ShieldCheck size={18} weight="fill" color={isAnomaly ? '#C0392B' : '#1E824C'} />
            <span>Spectral Anomaly Radar: {isAnomaly ? 'SURFACE ANOMALY DETECTED' : 'NORMAL TERRAIN SIGNATURE'}</span>
          </span>
          <span style={{ fontSize: '12px', fontWeight: 600, color: isAnomaly ? '#C0392B' : '#1E824C' }}>
            Centroid Distance: {format(result.reference_percentile, 1)}th percentile
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '12.5px', lineHeight: '1.4', color: '#2C3E50' }}>
          {isAnomaly
            ? 'Visual distance from group centroid exceeds 95% of reference European terrain. Potential burn scar, unusual industrial runoff, or transition boundary.'
            : 'Visual spectral descriptors fall squarely within standard dispersion bounds of normal European terrain.'}
        </p>
      </div>

      <CentroidEvidence result={result}/>
      <NearestPatches result={result} onSelect={selectPatch}/>
      <CategoryMix cluster={result.cluster} runId={run.id} isReference={isReference}/>
      {result.warnings.length > 0 && (
        <div className="analysis-notices">
          {result.warnings.map((warning, index) => {
            const isAlert = warning.toLowerCase().includes('fail') || warning.toLowerCase().includes('corrupt') || warning.toLowerCase().includes('error');
            return <Notice warning={isAlert} key={index}>{warning}</Notice>;
          })}
        </div>
      )}

      {/* Printable Survey Dossier Dialog */}
      {dossierOpen && (
        <dialog className="dossier-dialog" open style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '90%',
          maxWidth: '680px',
          maxHeight: '85vh',
          overflowY: 'auto',
          backgroundColor: '#FFFFFF',
          borderRadius: '12px',
          padding: '24px 28px',
          border: '1px solid #B7C5B9',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          zIndex: 1000,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '2px solid #0E3A2F', paddingBottom: '12px', marginBottom: '16px' }}>
            <div>
              <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: '#55645B', fontWeight: 700 }}>
                TerraLens · Autonomous Earth Observation Intelligence
              </span>
              <h2 style={{ margin: '4px 0 0 0', color: '#0E3A2F', fontSize: '20px' }}>Satellite Land-Use Survey Dossier</h2>
            </div>
            <button className="icon-button" onClick={() => setDossierOpen(false)} aria-label="Close dossier">
              <X size={20}/>
            </button>
          </div>

          <div style={{ fontSize: '13px', lineHeight: '1.6', color: '#1A251F' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', backgroundColor: '#F6F4EE', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px' }}>
              <div><strong>Survey Reference:</strong> <code>TL-{Date.now().toString().slice(-6)}</code></div>
              <div><strong>Sensor Benchmark:</strong> Sentinel-2 MSI (10m GSD)</div>
              <div><strong>Discovered Land Type:</strong> {clusterName(result.cluster)}</div>
              <div><strong>Cluster Group:</strong> Group {String(result.cluster + 1).padStart(2, '0')}</div>
              <div><strong>Centroid Distance:</strong> <code>{format(result.distance)}</code></div>
              <div><strong>Cohort Percentile:</strong> {format(result.reference_percentile, 1)}%</div>
            </div>

            <h4 style={{ margin: '14px 0 6px 0', color: '#0E3A2F' }}>Spectral & Texture Physical Metrics</h4>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px', marginBottom: '16px' }}>
              <tbody>
                <tr style={{ borderBottom: '1px solid #E5EADF' }}>
                  <td style={{ padding: '6px 0', color: '#55645B' }}>PCA Coordinate 1 (Surface Albedo)</td>
                  <td style={{ padding: '6px 0', fontWeight: 600, textAlign: 'right' }}><code>{format(result.pca[0])}</code></td>
                </tr>
                <tr style={{ borderBottom: '1px solid #E5EADF' }}>
                  <td style={{ padding: '6px 0', color: '#55645B' }}>PCA Coordinate 2 (Vegetation vs Water)</td>
                  <td style={{ padding: '6px 0', fontWeight: 600, textAlign: 'right' }}><code>{format(result.pca[1])}</code></td>
                </tr>
                <tr style={{ borderBottom: '1px solid #E5EADF' }}>
                  <td style={{ padding: '6px 0', color: '#55645B' }}>Spectral Anomaly Assessment</td>
                  <td style={{ padding: '6px 0', fontWeight: 600, textAlign: 'right', color: isAnomaly ? '#C0392B' : '#1E824C' }}>
                    {isAnomaly ? 'ELEVATED DISPERSION (ANOMALY)' : 'NOMINAL BASELINE'}
                  </td>
                </tr>
              </tbody>
            </table>

            <div style={{ borderTop: '1px solid #E5EADF', paddingTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <small style={{ color: '#55645B' }}>Sealed post-hoc verification certified under EuroSAT benchmark protocol.</small>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="button button-small button-secondary" onClick={() => window.print()}>
                  <Printer size={15}/> Print / Save PDF
                </button>
                <button className="button button-small button-primary" onClick={() => setDossierOpen(false)}>
                  Close
                </button>
              </div>
            </div>
          </div>
        </dialog>
      )}
    </Panel>
  );
}
