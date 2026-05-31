import type { QueryResponse } from 'seal';
import fixtures from '@/data/demo-fixtures.json';

export interface DemoPreset {
  id: string;
  label: string;
  query: string;
  response: QueryResponse;
}

export interface DemoFixturesFile {
  version: string;
  presets: DemoPreset[];
}

const data = fixtures as DemoFixturesFile;

export const demoPresets = data.presets;
export const demoVersion = data.version;

export function getPresetById(id: string): DemoPreset | undefined {
  return demoPresets.find((p) => p.id === id);
}
