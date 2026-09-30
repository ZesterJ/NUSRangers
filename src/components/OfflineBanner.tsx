import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import { useIsOnline } from '@/store/connectivity';

export function OfflineBanner() {
  const online = useIsOnline();
  const { t } = useTranslation();
  if (online) return null;
  return (
    <View style={styles.banner} accessibilityRole="alert">
      <Text style={styles.text}>📴 {t('offlineBanner')}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: { backgroundColor: '#FFF3E0', paddingHorizontal: 16, paddingVertical: 8 },
  text: { color: '#E65100', fontSize: 13, fontWeight: '600' },
});
