import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, Chip } from '@/components/ui';
import { tr } from '@/packs/types';
import { useSettings } from '@/store/settings';
import { spacing, usePackContext } from '@/theme';

export default function Onboarding() {
  const { pack, locale, theme } = usePackContext();
  const set = useSettings((s) => s.set);
  const { t } = useTranslation();

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.background }]}>
      <View style={styles.hero}>
        <Text style={styles.emoji}>{pack.emoji}</Text>
        <Text style={[styles.title, { color: theme.text }]}>
          {t('onboarding.welcome')} — {pack.appName}
        </Text>
        <Text style={[styles.tagline, { color: theme.textMuted }]}>{tr(pack.tagline, locale)}</Text>
      </View>

      <Text style={[styles.label, { color: theme.text }]}>{t('onboarding.chooseLanguage')}</Text>
      <View style={styles.chips}>
        {pack.locales.map((l) => (
          <Chip key={l.code} label={l.label} selected={locale === l.code} onPress={() => set({ locale: l.code })} />
        ))}
      </View>

      <Button
        label={t('onboarding.start')}
        style={{ marginTop: 'auto' }}
        onPress={() => {
          set({ onboarded: true });
          router.replace('/');
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, padding: spacing.xl, gap: spacing.lg },
  hero: { alignItems: 'center', marginTop: spacing.xl * 2, gap: spacing.sm },
  emoji: { fontSize: 72 },
  title: { fontSize: 26, fontWeight: '800', textAlign: 'center' },
  tagline: { fontSize: 16, textAlign: 'center' },
  label: { fontSize: 16, fontWeight: '700', marginTop: spacing.xl },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
});
