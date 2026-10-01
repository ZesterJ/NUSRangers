import { Redirect, Tabs } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Text } from 'react-native';

import { useSyncStore } from '@/ai/sync';
import { useSettings } from '@/store/settings';
import { usePackContext } from '@/theme';

const icon = (emoji: string) =>
  function TabBarIcon() {
    return <Text style={{ fontSize: 20 }}>{emoji}</Text>;
  };

export default function TabsLayout() {
  const onboarded = useSettings((s) => s.onboarded);
  const pending = useSyncStore((s) => s.pending);
  const { pack, theme } = usePackContext();
  const { t } = useTranslation();

  if (!onboarded) return <Redirect href="/onboarding" />;

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: theme.primary,
        tabBarInactiveTintColor: theme.textMuted,
        tabBarStyle: { backgroundColor: theme.card, borderTopColor: theme.border },
        headerStyle: { backgroundColor: theme.primary },
        headerTintColor: theme.primaryText,
        headerTitle: `${pack.emoji} ${pack.appName}`,
      }}>
      <Tabs.Screen name="index" options={{ title: t('tabs.home'), tabBarIcon: icon('🏠') }} />
      <Tabs.Screen name="chat" options={{ title: t('tabs.chat'), tabBarIcon: icon('💬') }} />
      <Tabs.Screen name="capture" options={{ title: t('tabs.capture'), tabBarIcon: icon('📝') }} />
      <Tabs.Screen
        name="history"
        options={{ title: t('tabs.history'), tabBarIcon: icon('🗂️'), tabBarBadge: pending || undefined }}
      />
      <Tabs.Screen name="settings" options={{ title: t('tabs.settings'), tabBarIcon: icon('⚙️') }} />
    </Tabs>
  );
}
