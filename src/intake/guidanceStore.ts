import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { isOnline } from '@/store/connectivity';
import { getSettings } from '@/store/settings';

import { BUNDLED_REGISTRY, type GuidanceRegistry } from './guidance';

function isRegistry(value: unknown): value is GuidanceRegistry {
  const r = value as GuidanceRegistry;
  return (
    !!r &&
    typeof r.version === 'number' &&
    typeof r.updated === 'string' &&
    typeof r.sources === 'object' &&
    Array.isArray(r.entries) &&
    r.entries.every((e) => typeof e.id === 'string' && Array.isArray(e.points) && !!r.sources[e.sourceId])
  );
}

/** A registry downloaded from the backend, kept only when it is newer than the one shipped in the app. */
const useDownloaded = create<{ registry: GuidanceRegistry | null }>()(
  persist(() => ({ registry: null as GuidanceRegistry | null }), {
    name: 'guidance-registry',
    storage: createJSONStorage(() => AsyncStorage),
  }),
);

/** The newest registry on this phone. */
export function useGuidanceRegistry(): GuidanceRegistry {
  const downloaded = useDownloaded((s) => s.registry);
  return downloaded && downloaded.version > BUNDLED_REGISTRY.version ? downloaded : BUNDLED_REGISTRY;
}

/** Fetch a newer registry when there is signal. Safe to call often; failures leave the current one in place. */
export async function refreshGuidance() {
  const { useMock, aiMode, apiUrl } = getSettings();
  if (!isOnline() || aiMode === 'offline' || useMock) return;
  try {
    const res = await fetch(`${apiUrl.replace(/\/$/, '')}/guidance`);
    if (!res.ok) return;
    const registry: unknown = await res.json();
    const current = useDownloaded.getState().registry?.version ?? BUNDLED_REGISTRY.version;
    if (isRegistry(registry) && registry.version > current) useDownloaded.setState({ registry });
  } catch (e) {
    console.warn('[guidance] refresh failed, keeping the registry on this phone', e);
  }
}
