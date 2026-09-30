import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import type { AiSource } from '@/ai/types';

const STYLE: Record<AiSource, { icon: string; bg: string; fg: string }> = {
  offline: { icon: '📱', bg: '#E8F5E9', fg: '#1B5E20' },
  cache: { icon: '💾', bg: '#EDE7F6', fg: '#4527A0' },
  'on-device': { icon: '🧠', bg: '#E3F2FD', fg: '#0D47A1' },
  cloud: { icon: '☁️', bg: '#E0F7FA', fg: '#006064' },
  fallback: { icon: '⏳', bg: '#FFF3E0', fg: '#E65100' },
};

/** Shows where an answer came from — the visible proof of the hybrid "Small AI" design. */
export function SourceBadge({ source }: { source: AiSource }) {
  const { t } = useTranslation();
  const s = STYLE[source];
  return (
    <View style={[styles.badge, { backgroundColor: s.bg }]}>
      <Text style={[styles.text, { color: s.fg }]}>
        {s.icon} {t(`source.${source}`)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { alignSelf: 'flex-start', borderRadius: 999, paddingHorizontal: 8, paddingVertical: 2 },
  text: { fontSize: 11, fontWeight: '700' },
});
