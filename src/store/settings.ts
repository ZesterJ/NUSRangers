import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { config } from '@/config';
import { getPack } from '@/packs';

/**
 * auto    — offline knowledge first, then cloud, then on-device LLM, then SMS.
 * offline — never call the network (demo "no signal" mode).
 * cloud   — skip the offline matcher and always ask the backend.
 */
export type AiMode = 'auto' | 'offline' | 'cloud';

type SettingsState = {
  hydrated: boolean;
  onboarded: boolean;
  packId: string;
  locale: string;
  aiMode: AiMode;
  /** Pretend there is no connectivity, without touching the device's radios. */
  forceOffline: boolean;
  useMock: boolean;
  apiUrl: string;
  set: (patch: Partial<Omit<SettingsState, 'set' | 'hydrated'>>) => void;
};

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      hydrated: false,
      onboarded: false,
      packId: config.defaultPack,
      locale: getPack(config.defaultPack).defaultLocale,
      aiMode: 'auto',
      forceOffline: false,
      useMock: config.useMock,
      apiUrl: config.apiUrl,
      set: (patch) => set(patch),
    }),
    {
      name: 'settings',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: ({ hydrated, set, ...rest }) => rest,
      onRehydrateStorage: () => () => useSettings.setState({ hydrated: true }),
    },
  ),
);

/** Non-hook access for code outside React (AI router, API client, sync). */
export const getSettings = () => useSettings.getState();
