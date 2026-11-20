import { Buildings, Grains, Mountains, Question, Tree, Waves } from '@phosphor-icons/react';
import type { Icon } from '@phosphor-icons/react';
import type { GroupName, LandType } from '../types';

export const LAND: Record<LandType, { label: string; color: string; Icon: Icon; plain: string }> = {
  trees: { label: 'Trees & greenery', color: 'var(--land-trees)', Icon: Tree, plain: 'Forests, parks, bushes and natural vegetation' },
  farmland: { label: 'Fields & farmland', color: 'var(--land-farmland)', Icon: Grains, plain: 'Crop fields, grass fields, orchards and grazing land' },
  water: { label: 'Water', color: 'var(--land-water)', Icon: Waves, plain: 'Rivers, lakes, ponds and the sea' },
  built: { label: 'Buildings & roads', color: 'var(--land-built)', Icon: Buildings, plain: 'Houses, factories, roads and paved areas' },
  bare: { label: 'Bare ground & open plots', color: 'var(--land-bare)', Icon: Mountains, plain: 'Bare soil, sand, empty plots and construction sites' },
  mixed: { label: 'Mixed land', color: 'var(--land-mixed)', Icon: Question, plain: 'Tiles that look like a mix of several land types' },
};

export const LAND_ORDER: LandType[] = ['trees', 'farmland', 'water', 'built', 'bare', 'mixed'];

export function LandLegend({ types = LAND_ORDER }: { types?: LandType[] }) {
  return <ul className="land-legend" aria-label="Map colours">{types.map(type => <li key={type}><i style={{ background: LAND[type].color }}/>{LAND[type].label}</li>)}</ul>;
}

/** How the ten unsupervised groups were given everyday names after fitting. */
export function GroupNames({ groups }: { groups: GroupName[] }) {
  return <div className="group-names">
    <p>The model sorted 21,600 satellite patches into 10 groups by colour and texture alone, without ever seeing a label. We named each group afterwards by checking what it mostly contained:</p>
    <table>
      <thead><tr><th scope="col">Group</th><th scope="col">Shown as</th><th scope="col">Matches that type</th></tr></thead>
      <tbody>{groups.map(group => <tr key={group.cluster}><td>Group {String(group.cluster + 1).padStart(2, '0')}</td><td><LandChip type={group.land_type}/></td><td><span className="match-bar"><i style={{ width: `${group.reliability * 100}%` }}/></span>{Math.round(group.reliability * 100)}%</td></tr>)}</tbody>
    </table>
    <p>A group gets a land type when at least half of it is that type. Groups that are mostly vegetation split between trees and fields take whichever is larger. Anything less clear is shown as <strong>Mixed land</strong> rather than guessed.</p>
  </div>;
}

export function LandChip({ type }: { type: LandType }) {
  const { Icon, label, color } = LAND[type];
  return <span className="land-chip"><span className="land-chip-icon" style={{ background: color }}><Icon size={13} weight="bold"/></span>{label}</span>;
}
