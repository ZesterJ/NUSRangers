import { agriPack } from './agri';
import { healthPack } from './health';
import { tourismPack } from './tourism';
import type { DomainPack } from './types';

/** Register new packs here. */
export const PACKS: Record<string, DomainPack> = {
  [agriPack.id]: agriPack,
  [healthPack.id]: healthPack,
  [tourismPack.id]: tourismPack,
};

export function getPack(id: string | undefined): DomainPack {
  return (id && PACKS[id]) || agriPack;
}

export * from './types';
