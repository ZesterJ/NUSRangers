import { healthPack } from './health';
import type { DomainPack } from './types';

/** Register packs here. The app ships the health pack only. */
export const PACKS: Record<string, DomainPack> = {
  [healthPack.id]: healthPack,
};

/** Unknown ids (e.g. a pack saved on the phone before it was removed) fall back to health. */
export function getPack(id: string | undefined): DomainPack {
  return (id && PACKS[id]) || healthPack;
}

export * from './types';
