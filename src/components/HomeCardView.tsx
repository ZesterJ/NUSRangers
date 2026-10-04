import { router } from 'expo-router';
import { Linking, Pressable, StyleSheet, Text } from 'react-native';

import type { HomeCard } from '@/packs/types';
import { tr } from '@/packs/types';
import { usePackContext } from '@/theme';

import { Card } from './ui';

const KIND_ICON: Record<HomeCard['kind'], string> = { tip: '💡', alert: '⚠️', metric: '📈', action: '👉' };

export function HomeCardView({ card }: { card: HomeCard }) {
  const { locale, theme } = usePackContext();

  const onPress = () => {
    const a = card.action;
    if (!a) return;
    if (a.type === 'chat') router.push({ pathname: '/chat', params: { q: tr(a.prompt, locale) } });
    else if (a.type === 'capture') router.push('/capture');
    else if (a.type === 'intake') router.push('/intake');
    else if (a.type === 'scan') router.push('/scan');
    else if (a.type === 'scanCode') router.push({ pathname: '/scan', params: { mode: 'scan' } });
    else if (a.type === 'reports') router.push({ pathname: '/scan', params: { mode: 'reports' } });
    else if (a.type === 'records') router.push('/history');
    else Linking.openURL(a.url);
  };

  return (
    <Pressable onPress={onPress} disabled={!card.action}>
      <Card style={card.kind === 'alert' ? { borderColor: theme.warning, borderWidth: 1 } : undefined}>
        <Text style={[styles.title, { color: theme.text }]}>
          {card.icon ?? KIND_ICON[card.kind]} {tr(card.title, locale)}
        </Text>
        {card.value && <Text style={[styles.value, { color: theme.primary }]}>{card.value}</Text>}
        {card.body && <Text style={{ color: theme.textMuted, fontSize: 15 }}>{tr(card.body, locale)}</Text>}
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 16, fontWeight: '700' },
  value: { fontSize: 28, fontWeight: '800' },
});
