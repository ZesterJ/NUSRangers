import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, Card, Chip } from '@/components/ui';
import { tr } from '@/packs/types';
import { useSettings } from '@/store/settings';
import { radius, spacing, usePackContext } from '@/theme';

const NOTICE = ['notDiagnosis', 'guidance', 'emergency', 'stored', 'shared', 'location'] as const;

/** First screen: choose a language, then read and agree to the privacy and consent notice. */
export default function Onboarding() {
  const { pack, locale, theme, scale } = usePackContext();
  const set = useSettings((s) => s.set);
  const { t } = useTranslation();
  const body = { fontSize: 15 * scale, lineHeight: 22 * scale };

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.background }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.logoBox}>
          <Image source={require('@/assets/images/logo.png')} style={styles.logo} contentFit="contain" accessibilityLabel={pack.appName} />
        </View>
        <Text style={[styles.tagline, { color: theme.textMuted, fontSize: 16 * scale }]}>{tr(pack.tagline, locale)}</Text>

        <Text style={[styles.label, { color: theme.text, fontSize: 16 * scale }]}>{t('onboarding.chooseLanguage')}</Text>
        <View style={styles.chips}>
          {pack.locales.map((l) => (
            <Chip key={l.code} label={l.label} selected={locale === l.code} onPress={() => set({ locale: l.code })} />
          ))}
        </View>

        <Card>
          <Text style={[styles.label, { color: theme.text, fontSize: 17 * scale }]}>🔒 {t('consent.title')}</Text>
          {NOTICE.map((key) => (
            <Text key={key} style={[body, { color: theme.text }]}>
              • {t(`consent.${key}`)}
            </Text>
          ))}
          <Text style={[body, { color: theme.textMuted }]}>{t('consent.agreeNote')}</Text>
        </Card>

        <Button
          label={t('consent.agree')}
          onPress={() => {
            set({ onboarded: true, consented: true });
            router.replace('/');
          }}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { padding: spacing.xl, gap: spacing.lg },
  logoBox: { backgroundColor: '#FFFFFF', borderRadius: radius.lg, padding: spacing.sm },
  logo: { width: '100%', aspectRatio: 1024 / 559 },
  tagline: { textAlign: 'center' },
  label: { fontWeight: '700' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
});
