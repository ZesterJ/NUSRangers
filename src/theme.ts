import { useColorScheme } from 'react-native';

import { getPack } from '@/packs';
import { useSettings } from '@/store/settings';

const palettes = {
  light: {
    text: '#11181C',
    textMuted: '#60646C',
    background: '#F7F7F8',
    card: '#FFFFFF',
    border: '#E0E1E6',
    bubbleUser: '#E8F0FE',
    danger: '#C62828',
    warning: '#B26A00',
    success: '#2E7D32',
  },
  dark: {
    text: '#ECEDEE',
    textMuted: '#9BA1A6',
    background: '#0E0F10',
    card: '#1A1C1E',
    border: '#2E3135',
    bubbleUser: '#1F2A3A',
    danger: '#EF5350',
    warning: '#FFB74D',
    success: '#66BB6A',
  },
};

export type Theme = (typeof palettes)['light'] & { primary: string; primaryText: string };

/** Active pack + locale + colours, in one hook for screens. */
export function usePackContext() {
  const packId = useSettings((s) => s.packId);
  const locale = useSettings((s) => s.locale);
  const scheme = useColorScheme() === 'dark' ? 'dark' : 'light';
  const pack = getPack(packId);
  const theme: Theme = { ...palettes[scheme], ...pack.theme };
  return { pack, locale, theme };
}

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 };
export const radius = { sm: 8, md: 12, lg: 18 };
