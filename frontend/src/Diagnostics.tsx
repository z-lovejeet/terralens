import { useState } from 'react';
import { ChartScatter, Flask, ShieldCheck, SlidersHorizontal } from '@phosphor-icons/react';
import Projections from './Projections';
import Experiments from './Experiments';
import Evidence from './Evidence';
import type { Capabilities, PatchContext, Run, Study } from './types';

interface DiagnosticsProps {
  study: Study;
  run: Run;
  capabilities: Capabilities;
  selectPatch: (id: string, context?: PatchContext) => void;
}

export default function Diagnostics({ study, run, capabilities, selectPatch }: DiagnosticsProps) {
  const [subTab, setSubTab] = useState<'manifolds' | 'benchmarks' | 'audit'>('manifolds');

  return (
    <div className="view-panel diagnostics-view">
      <div className="view-header">
        <div className="view-header-title">
          <span className="badge badge-secondary"><SlidersHorizontal size={14} weight="bold" /> Model Lab & Diagnostics</span>
          <h1>Algorithm Diagnostics & Scientific Benchmarks</h1>
          <p className="lead">
            Explore internal unsupervised mathematical foundations: PCA variance retention, t-SNE non-linear embeddings, K-Means hyperparameter sensitivity, and sealed reference audits.
          </p>
        </div>

        {/* Diagnostics Sub-Navigation */}
        <div className="diagnostics-subnav">
          <button
            className={`subnav-pill ${subTab === 'manifolds' ? 'is-active' : ''}`}
            onClick={() => setSubTab('manifolds')}
          >
            <ChartScatter size={18} weight={subTab === 'manifolds' ? 'fill' : 'regular'} />
            <span>Manifold Projections (PCA & t-SNE)</span>
          </button>
          <button
            className={`subnav-pill ${subTab === 'benchmarks' ? 'is-active' : ''}`}
            onClick={() => setSubTab('benchmarks')}
          >
            <Flask size={18} weight={subTab === 'benchmarks' ? 'fill' : 'regular'} />
            <span>Clustering Benchmarks (K-Means)</span>
          </button>
          <button
            className={`subnav-pill ${subTab === 'audit' ? 'is-active' : ''}`}
            onClick={() => setSubTab('audit')}
          >
            <ShieldCheck size={18} weight={subTab === 'audit' ? 'fill' : 'regular'} />
            <span>Methodology & Reference Audit</span>
          </button>
        </div>
      </div>

      {/* Render selected diagnostic tool */}
      <div className="diagnostics-body">
        {subTab === 'manifolds' && (
          <Projections study={study} run={run} selectPatch={id => selectPatch(id)} />
        )}
        {subTab === 'benchmarks' && (
          <Experiments study={study} run={run} capabilities={capabilities} selectPatch={selectPatch} />
        )}
        {subTab === 'audit' && (
          <Evidence study={study} run={run} />
        )}
      </div>
    </div>
  );
}
