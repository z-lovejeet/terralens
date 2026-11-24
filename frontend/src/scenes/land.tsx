import { Buildings, Grains, Mountains, Question, Tree, Waves } from '@phosphor-icons/react';
import type { Icon } from '@phosphor-icons/react';
import type { LandType } from '../types';

export const LAND: Record<LandType, { label: string; color: string; Icon: Icon; plain: string }> = {
  trees: { label: 'Trees & greenery', color: 'var(--land-trees)', Icon: Tree, plain: 'Forests, parks, bushes and natural vegetation' },
  farmland: { label: 'Fields & farmland', color: 'var(--land-farmland)', Icon: Grains, plain: 'Crop fields, grass fields, orchards and grazing land' },
  water: { label: 'Water', color: 'var(--land-water)', Icon: Waves, plain: 'Rivers, lakes, ponds and the sea' },
  built: { label: 'Buildings & roads', color: 'var(--land-built)', Icon: Buildings, plain: 'Houses, factories, roads and paved areas' },
  bare: { label: 'Bare ground & sand', color: 'var(--land-bare)', Icon: Mountains, plain: 'Sand banks, dry soil, open yards and building sites' },
  mixed: { label: 'Mixed land', color: 'var(--land-mixed)', Icon: Question, plain: 'Tiles that look like a mix of several land types' },
};

export const LAND_ORDER: LandType[] = ['trees', 'farmland', 'water', 'built', 'mixed'];

export function LandChip({ type }: { type: LandType }) {
  const { Icon, label, color } = LAND[type];
  return <span className="land-chip"><span className="land-chip-icon" style={{ background: color }}><Icon size={13} weight="bold"/></span>{label}</span>;
}
