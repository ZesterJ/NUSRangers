import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { HomeCardView } from '@/components/HomeCardView';
import { LanguageSwitch } from '@/components/LanguageSwitch';
import { Button, Card, KeyboardScrollView } from '@/components/ui';
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
  // Clinic staff sign in with the clinic PIN, so a patient does not wander into the clinic view.
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
      <KeyboardScrollView contentContainerStyle={styles.content}>
        <LanguageSwitch />
        {/* The logo has a white background, so it sits on a white panel in dark mode too. */}
        <View style={styles.logoBox}>
          <Image
            source={require('@/assets/images/logo.png')}
            style={styles.logo}
            contentFit="contain"
            accessibilityLabel={pack.appName}
          />
        </View>
        {role === null ? (
          // ---------- Sign in ----------
          <>
            <View style={styles.header}>
              <Text style={[styles.welcome, { color: theme.text }]}>{t('home.signInTitle')}</Text>
              <Text style={{ color: theme.textMuted }}>{t('home.signInHint')}</Text>
            </View>
            <Button label={`🙋 ${t('home.rolePatient')}`} onPress={() => set({ role: 'patient' })} />
            <Button label={`🏥 ${t('home.roleClinic')}`} variant="outline" onPress={() => setUnlocking(true)} />
            {unlocking && (
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
                  autoFocus
                  onSubmitEditing={unlock}
                />
                {wrong && <Text style={{ color: theme.danger }}>{t('home.pinWrong')}</Text>}
                <Button label={t('home.signIn')} disabled={!pin} onPress={unlock} />
              </Card>
            )}
            <Pressable onPress={() => router.push('/onboarding')}>
              <Text style={{ color: theme.primary, textAlign: 'center', fontWeight: '600' }}>🔒 {t('consent.title')}</Text>
            </Pressable>
          </>
        ) : (
          // ---------- Signed in: choose what to do ----------
          <>
            <View style={styles.header}>
              <Text style={[styles.welcome, { color: theme.text }]}>{t('home.welcome')}</Text>
              <Text style={{ color: online ? theme.success : theme.warning, fontWeight: '700' }}>
                ● {online ? t('common.online') : t('common.offline')}
              </Text>
            </View>
            {pack.homeCards
              .filter((card) => !card.roles || card.roles.includes(role))
              .map((card) => (
                <HomeCardView key={card.id} card={card} />
              ))}
            <View style={styles.signedIn}>
              <Text style={{ color: theme.textMuted, flex: 1 }}>
                {t('home.signedInAs', { role: t(role === 'clinic' ? 'home.roleClinic' : 'home.rolePatient') })}
              </Text>
              <Button label={t('home.signOut')} variant="outline" onPress={() => set({ role: null })} />
            </View>
          </>
        )}
      </KeyboardScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  logoBox: { backgroundColor: '#FFFFFF', borderRadius: radius.lg, padding: spacing.sm },
  logo: { width: '100%', aspectRatio: 1024 / 559 },
  header: { gap: spacing.xs },
  welcome: { fontSize: 20, fontWeight: '800' },
  signedIn: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, marginTop: spacing.md },
  input: { borderWidth: 1, borderRadius: radius.md, padding: spacing.md, fontSize: 18, marginVertical: spacing.sm },
});
