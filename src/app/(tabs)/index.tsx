import { Image } from 'expo-image';
import { useTranslation } from 'react-i18next';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { HomeCardView } from '@/components/HomeCardView';
import { OfflineBanner } from '@/components/OfflineBanner';
import { tr } from '@/packs/types';
import { useIsOnline } from '@/store/connectivity';
import { radius, spacing, usePackContext } from '@/theme';

export default function Home() {
  const { pack, locale, theme } = usePackContext();
  const online = useIsOnline();
  const { t } = useTranslation();

  return (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <OfflineBanner />
      <ScrollView contentContainerStyle={styles.content}>
        {/* The logo has a white background, so it sits on a white panel in dark mode too. */}
        <View style={styles.logoBox}>
          <Image
            source={require('@/assets/images/logo.png')}
            style={styles.logo}
            contentFit="contain"
            accessibilityLabel={pack.appName}
          />
        </View>
        <View style={styles.header}>
          <Text style={[styles.tagline, { color: theme.text }]}>{tr(pack.tagline, locale)}</Text>
          <Text style={{ color: online ? theme.success : theme.warning, fontWeight: '700' }}>
            ● {online ? t('common.online') : t('common.offline')}
          </Text>
        </View>

        {pack.homeCards.map((card) => (
          <HomeCardView key={card.id} card={card} />
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  logoBox: { backgroundColor: '#FFFFFF', borderRadius: radius.lg, padding: spacing.sm },
  logo: { width: '100%', aspectRatio: 1024 / 559 },
  header: { gap: spacing.xs, marginBottom: spacing.sm },
  tagline: { fontSize: 20, fontWeight: '800' },
});
