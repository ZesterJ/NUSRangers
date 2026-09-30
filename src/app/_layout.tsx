import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { flushOutbox, refreshPending } from '@/ai/sync';
import { getDb } from '@/db';
import i18n from '@/i18n';
import { startConnectivityWatcher, useIsOnline } from '@/store/connectivity';
import { useSettings } from '@/store/settings';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const hydrated = useSettings((s) => s.hydrated);
  const locale = useSettings((s) => s.locale);
  const online = useIsOnline();

  useEffect(() => startConnectivityWatcher(), []);

  useEffect(() => {
    getDb().then(refreshPending).catch((e) => console.warn('[db] init failed', e));
  }, []);

  useEffect(() => {
    i18n.changeLanguage(locale);
  }, [locale]);

  // Whenever we (re)gain connectivity, retry everything queued offline.
  useEffect(() => {
    if (online && hydrated) flushOutbox();
  }, [online, hydrated]);

  useEffect(() => {
    if (hydrated) SplashScreen.hideAsync();
  }, [hydrated]);

  if (!hydrated) return null;

  return (
    <>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="onboarding" options={{ presentation: 'modal' }} />
      </Stack>
    </>
  );
}
