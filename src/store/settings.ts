import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { config } from '@/config';
import { PACKS, getPack } from '@/packs';

/**
 * auto    — offline knowledge first, then cloud, then on-device LLM, then SMS.
 * offline — never call the network (demo "no signal" mode).
 * cloud   — skip the offline matcher and always ask the backend.
 */
export type AiMode = 'auto' | 'offline' | 'cloud';

/** Who is using this phone: a patient or caregiver, or clinic staff (reception, nurse, doctor). */
export type Role = 'patient' | 'clinic';

type SettingsState = {
  hydrated: boolean;
  onboarded: boolean;
  /** The person agreed to the privacy and consent notice on this phone. */
  consented: boolean;
  /** null = nobody is signed in yet; Home shows the sign-in screen. */
  role: Role | null;
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
      consented: false,
      role: null,
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
      onRehydrateStorage: () => () => {
        const { packId, locale } = useSettings.getState();
        // A pack saved on this phone may no longer exist (agri/tourism were removed): switch to the current one.
        const pack = getPack(packId);
        const patch: Partial<SettingsState> = { hydrated: true };
        if (!PACKS[packId]) patch.packId = pack.id;
        if (!pack.locales.some((l) => l.code === locale)) patch.locale = pack.defaultLocale;
        useSettings.setState(patch);
      },
    },
  ),
);

/** Non-hook access for code outside React (AI router, API client, sync). */
export const getSettings = () => useSettings.getState();
