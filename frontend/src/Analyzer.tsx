import { useEffect, useRef, useState } from 'react';
import { format, patchUrl, request } from './api';
import { Scatter } from './Charts';
import { FeatureProfile, Notice, PageTitle, Panel } from './UI';
import AnalysisResult from './analyzer/AnalysisResult';
import UploadPanel from './analyzer/UploadPanel';
import type { Analysis, Capabilities, PatchContext, Run, Study } from './types';
import './analyzer/analyzer.css';

interface AnalyzerProps {
  study: Study;
  run: Run;
  capabilities: Capabilities;
  selectPatch: (id: string, context?: PatchContext) => void;
}

const imageFormats = ['image/jpeg', 'image/png', 'image/webp'];

export default function Analyzer({ study, run, capabilities, selectPatch }: AnalyzerProps) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Analysis | null>(null);
  const [runId, setRunId] = useState(run.id);
  const [activity, setActivity] = useState<'example' | 'analysis' | null>(null);
  const [error, setError] = useState('');
  const activeRequest = useRef<AbortController | null>(null);
  const analysisRuns = (capabilities.analysis_runs ?? []).flatMap(id => {
    const savedRun = study.runs.find(item => item.id === id);
    return savedRun ? [savedRun] : [];
  });
  const analysisRun = analysisRuns.find(item => item.id === runId) ?? run;
  const isReference = analysisRun.id === run.id;
  const cohortClusters = result?.cohort_clusters;
  const cohortPoints = isReference
    ? study.points
    : cohortClusters?.length === study.points.length
      ? study.points.map((point, index) => ({ id: point.id, pca: point.pca, cluster: cohortClusters[index] }))
      : [];

  useEffect(() => () => activeRequest.current?.abort(), []);

  function clearImage() {
    setFile(null);
    setResult(null);
    setError('');
  }

  function chooseImage(next: File) {
    clearImage();
    if (!imageFormats.includes(next.type)) {
      setError('Choose a JPEG, PNG, or WebP image.');
    } else if (next.size > capabilities.upload_max_bytes) {
      setError('Choose a file up to ' + format(capabilities.upload_max_bytes / 1024 / 1024, 0) + ' MB.');
    } else if (!next.size) {
      setError('This file is empty. Choose another image.');
    } else {
      setFile(next);
    }
  }

  function changeRun(id: string) {
    setRunId(id);
    setResult(null);
    setError('');
  }

  function inspectPatch(id: string) {
    const point = cohortPoints.find(item => item.id === id);
    selectPatch(id, { runId: analysisRun.id, clusterId: point?.cluster ?? result?.cluster, point });
  }

  async function analyze() {
    if (!file || activeRequest.current) return;
    const controller = new AbortController();
    activeRequest.current = controller;
    setActivity('analysis');
    setError('');
    setResult(null);

    try {
      const body = new FormData();
      body.append('file', file);
      const route = isReference ? '/analyze' : `/analyze?run_id=${encodeURIComponent(analysisRun.id)}`;
      const analysis = await request<Analysis>(route, {
        method: 'POST', body, signal: controller.signal,
      });
      if ((analysis.run_id ?? run.id) !== analysisRun.id) {
        throw new Error('The analysis returned a different grouping. Please try again.');
      }
      if (!controller.signal.aborted) setResult(analysis);
    } catch (cause) {
      if (!controller.signal.aborted) setError((cause as Error).message);
    } finally {
      if (!controller.signal.aborted) setActivity(null);
      activeRequest.current = null;
    }
  }

  async function loadPresetPatch(id: string) {
    if (activeRequest.current) return;
    const controller = new AbortController();
    activeRequest.current = controller;
    setActivity('example');
    setError('');
    try {
      const response = await fetch(patchUrl(id), { signal: controller.signal });
      if (!response.ok) throw new Error('Could not load preset patch.');
      const blob = await response.blob();
      const presetFile = new File([blob], `${id}.jpg`, { type: 'image/jpeg' });
      chooseImage(presetFile);
      const body = new FormData();
      body.append('file', presetFile);
      const route = isReference ? '/analyze' : `/analyze?run_id=${encodeURIComponent(analysisRun.id)}`;
      setActivity('analysis');
      const analysis = await request<Analysis>(route, { method: 'POST', body, signal: controller.signal });
      setResult(analysis);
    } catch (cause) {
      if (!controller.signal.aborted) setError((cause as Error).message);
    } finally {
      if (!controller.signal.aborted) setActivity(null);
      activeRequest.current = null;
    }
  }

  async function useExample() {
    if (activeRequest.current) return;
    const id = run.clusters[0]?.representatives[0] || study.points[0]?.id;
    if (!id) {
      setError('No example patch is available. Choose an image from your computer.');
      return;
    }

    const controller = new AbortController();
    activeRequest.current = controller;
    setActivity('example');
    setError('');
    try {
      const response = await fetch(patchUrl(id), { signal: controller.signal });
      if (!response.ok) throw new Error('The example patch could not be loaded. Choose an image from your computer.');
      const blob = await response.blob();
      if (!controller.signal.aborted) {
        chooseImage(new File([blob], 'eurosat-example.jpg', { type: 'image/jpeg' }));
      }
    } catch (cause) {
      if (!controller.signal.aborted) setError((cause as Error).message);
    } finally {
      if (!controller.signal.aborted) setActivity(null);
      activeRequest.current = null;
    }
  }

  return (
    <>
      <PageTitle
        title="Patch analyzer"
        text="Compare a satellite image with the visual groups discovered in EuroSAT."
      />

      <div className="analyzer-presets-bar" style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flexWrap: 'wrap',
        marginBottom: '16px',
        padding: '10px 14px',
        backgroundColor: '#E5EADF',
        borderRadius: '8px'
      }}>
        <span style={{ fontSize: '12px', fontWeight: 700, color: '#0E3A2F', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Instant Test Presets:
        </span>
        {[
          { id: 'pe0bce20c66ac24a69c02', label: 'Dense Forest' },
          { id: 'p4c4d3414ff772fda8d8b', label: 'River Waterway' },
          { id: 'pc3e5311f7c0a3428ea84', label: 'Industrial Complex' },
          { id: 'p4ad8538c80a0317ebcc1', label: 'Residential Area' },
          { id: 'pf86a09867b8db213f801', label: 'Agricultural Crops' },
        ].map(p => (
          <button
            key={p.id}
            className="button button-small button-secondary"
            onClick={() => loadPresetPatch(p.id)}
            disabled={activity !== null}
            style={{ fontSize: '12px', padding: '4px 10px' }}
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="analyzer-grid">
        <UploadPanel
          file={file}
          maxBytes={capabilities.upload_max_bytes}
          analyzing={activity === 'analysis'}
          loadingExample={activity === 'example'}
          error={error}
          modes={analysisRuns.map(item => ({
            id: item.id, label: `${item.id === run.id ? 'Reference' : 'Finer comparison'} · ${item.k} visual groups`,
          }))}
          selectedMode={analysisRun.id}
          onModeChange={changeRun}
          onChoose={chooseImage}
          onClear={clearImage}
          onAnalyze={() => { void analyze(); }}
          onExample={() => { void useExample(); }}
        />
        <AnalysisResult result={result} run={analysisRun} isReference={isReference}
          analyzing={activity === 'analysis'} selectPatch={inspectPatch}/>
      </div>
      {result && (
        <div className="analysis-grid">
          <Panel
            title="Your patch in PCA space"
            detail={`The crosshair marks your upload. The dots use the saved ${analysisRun.k}-group assignment.`}
          >
            {cohortPoints.length ? (
              <Scatter
                points={cohortPoints}
                projection="pca"
                marker={result.pca}
                filter={result.cluster}
                onSelect={inspectPatch}
              />
            ) : <Notice>The saved cohort assignments are unavailable for this grouping.</Notice>}
          </Panel>
          <Panel title="What the image contains" detail="Feature measurements relative to the study distribution.">
            <FeatureProfile features={result.features} title="Your patch’s feature profile"/>
          </Panel>
        </div>
      )}
      <Notice>
        Use this tool to compare visual similarity. A different capture scale, a photograph, or a screenshot can produce a misleading assignment.
      </Notice>
    </>
  );
}
