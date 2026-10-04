import { Image } from 'expo-image';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { HomeCardView } from '@/components/HomeCardView';
import { OfflineBanner } from '@/components/OfflineBanner';
import { Button, Card, Chip } from '@/components/ui';
import { config } from '@/config';
import { useIsOnline } from '@/store/connectivity';
import { useSettings } from '@/store/settings';
import { radius, spacing, usePackContext } from '@/theme';

export default function Home() {
  const { pack, theme } = usePackContext();
  const online = useIsOnline();
  const { t } = useTranslation();
  const role = useSettings((s) => s.role);
  const set = useSettings((s) => s.set);
  // The clinic view sits behind a PIN so a patient does not wander into it.
  const [unlocking, setUnlocking] = useState(false);
  const [pin, setPin] = useState('');
  const [wrong, setWrong] = useState(false);

  const unlock = () => {
    if (pin !== config.clinicPin) return setWrong(true);
    set({ role: 'clinic' });
    setUnlocking(false);
    setPin('');
    setWrong(false);
  };

  return (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <OfflineBanner />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
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
          <Text style={[styles.welcome, { color: theme.text }]}>{t('home.welcome')}</Text>
          <Text style={{ color: online ? theme.success : theme.warning, fontWeight: '700' }}>
            ● {online ? t('common.online') : t('common.offline')}
          </Text>
        </View>

        <View style={styles.chips}>
          <Chip
            label={`🙋 ${t('home.rolePatient')}`}
            selected={role === 'patient'}
            onPress={() => {
              set({ role: 'patient' });
              setUnlocking(false);
            }}
          />
          <Chip label={`🏥 ${t('home.roleClinic')}`} selected={role === 'clinic'} onPress={() => role !== 'clinic' && setUnlocking(true)} />
        </View>

        {unlocking && role !== 'clinic' && (
          <Card>
            <Text style={{ color: theme.text, fontWeight: '700' }}>🔒 {t('home.pinPrompt')}</Text>
            <TextInput
              style={[styles.input, { color: theme.text, borderColor: wrong ? theme.danger : theme.border, backgroundColor: theme.background }]}
              value={pin}
              onChangeText={(v) => {
                setPin(v);
                setWrong(false);
              }}
              keyboardType="number-pad"
              secureTextEntry
              maxLength={8}
              onSubmitEditing={unlock}
            />
            {wrong && <Text style={{ color: theme.danger }}>{t('home.pinWrong')}</Text>}
            <Button label={t('home.unlock')} disabled={!pin} onPress={unlock} />
          </Card>
        )}

        {pack.homeCards
          .filter((card) => !card.roles || card.roles.includes(role))
          .map((card) => (
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
  header: { gap: spacing.xs },
  welcome: { fontSize: 20, fontWeight: '800' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  input: { borderWidth: 1, borderRadius: radius.md, padding: spacing.md, fontSize: 18, marginVertical: spacing.sm },
});
