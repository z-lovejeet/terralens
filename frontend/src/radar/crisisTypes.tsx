import { Buildings, CheckCircle, CloudFog, Drop, DropSlash, Factory, Fire, Flame, Hurricane, Mountains, Plant, Question, Snowflake, SunHorizon, TreeEvergreen, Waves, Wind } from '@phosphor-icons/react';
import type { Icon } from '@phosphor-icons/react';
import type { Severity } from '../types';

export type HazardGroup = 'Water' | 'Fire' | 'Land' | 'Structures' | 'Pollution' | 'Weather';

export const CRISIS: Record<string, { label: string; group: HazardGroup | null; Icon: Icon }> = {
  none: { label: 'No crisis', group: null, Icon: CheckCircle },
  flood: { label: 'Flood', group: 'Water', Icon: Waves },
  tsunami: { label: 'Tsunami or storm surge', group: 'Water', Icon: Waves },
  coastal_erosion: { label: 'Coastal erosion', group: 'Water', Icon: Waves },
  wildfire: { label: 'Wildfire', group: 'Fire', Icon: Fire },
  burn_scar: { label: 'Burn scar', group: 'Fire', Icon: Flame },
  smoke_plume: { label: 'Smoke plume', group: 'Fire', Icon: CloudFog },
  volcanic_activity: { label: 'Volcanic activity', group: 'Fire', Icon: Mountains },
  industrial_accident: { label: 'Industrial accident', group: 'Fire', Icon: Factory },
  drought: { label: 'Drought', group: 'Land', Icon: DropSlash },
  deforestation: { label: 'Deforestation', group: 'Land', Icon: TreeEvergreen },
  landslide: { label: 'Landslide', group: 'Land', Icon: Mountains },
  desertification: { label: 'Desertification', group: 'Land', Icon: SunHorizon },
  mining_damage: { label: 'Mining damage', group: 'Land', Icon: Mountains },
  earthquake_damage: { label: 'Earthquake damage', group: 'Structures', Icon: Buildings },
  structural_damage: { label: 'Building damage', group: 'Structures', Icon: Buildings },
  storm_damage: { label: 'Storm damage', group: 'Weather', Icon: Hurricane },
  dust_storm: { label: 'Dust storm', group: 'Weather', Icon: Wind },
  snow_ice_hazard: { label: 'Snow or ice hazard', group: 'Weather', Icon: Snowflake },
  oil_spill: { label: 'Oil spill', group: 'Pollution', Icon: Drop },
  algal_bloom: { label: 'Algal bloom', group: 'Pollution', Icon: Plant },
  other: { label: 'Other hazard', group: null, Icon: Question },
};

export const crisisInfo = (type: string) => CRISIS[type] ?? CRISIS.other;

export const HAZARD_GROUPS: HazardGroup[] = ['Water', 'Fire', 'Land', 'Structures', 'Weather', 'Pollution'];

export const SEVERITY_SCALE: { id: Severity; label: string }[] = [
  { id: 'none', label: 'None' },
  { id: 'low', label: 'Low' },
  { id: 'moderate', label: 'Moderate' },
  { id: 'high', label: 'High' },
  { id: 'severe', label: 'Severe' },
];
