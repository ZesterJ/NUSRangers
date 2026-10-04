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
  const role = useSettings((s) => s.role);
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
      {/* Until someone signs in on Home, only Home is reachable. The Intake tab is the
          patient's; clinic staff reach the same screen from the walk-in card on Home. */}
      <Tabs.Screen
        name="intake"
        options={{ title: t('tabs.intake'), tabBarIcon: icon('📝'), ...(role === 'patient' ? {} : { href: null }) }}
      />
      {/* The clinic screens are for clinic staff only. */}
      <Tabs.Screen
        name="scan"
        options={{ title: t('tabs.scan'), tabBarIcon: icon('🏥'), ...(role === 'clinic' ? {} : { href: null }) }}
      />
      <Tabs.Screen
        name="clinics"
        options={{ title: t('tabs.clinics'), tabBarIcon: icon('📍'), ...(role === 'patient' ? {} : { href: null }) }}
      />
      <Tabs.Screen
        name="guidance"
        options={{ title: t('tabs.guidance'), tabBarIcon: icon('📖'), ...(role === 'clinic' ? {} : { href: null }) }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: t('tabs.records'),
          tabBarIcon: icon('🗂️'),
          tabBarBadge: (role === 'clinic' && pending) || undefined,
          ...(role ? {} : { href: null }),
        }}
      />
      {/* Kept from the generic template, hidden for the health intake flow. */}
      <Tabs.Screen name="chat" options={{ href: null, title: t('tabs.chat') }} />
      <Tabs.Screen name="capture" options={{ href: null, title: t('tabs.capture') }} />
      {/* Settings hold the team's connection options; patients change language on Home instead. */}
      <Tabs.Screen
        name="settings"
        options={{ title: t('tabs.settings'), tabBarIcon: icon('⚙️'), ...(role === 'clinic' ? {} : { href: null }) }}
      />
    </Tabs>
  );
}
