import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type ScrollViewProps,
  type ViewStyle,
} from 'react-native';

import { radius, spacing, usePackContext } from '@/theme';

/**
 * A scrolling screen that stays usable when the keyboard opens. On iOS the scroll area shrinks to
 * end above the keyboard, so every input can be scrolled into view; on Android the window pans
 * (`softwareKeyboardLayoutMode` in app.json). Taps on buttons work while the keyboard is up, and a tap
 * on empty space closes it.
 */
export function KeyboardScrollView({ style, ...props }: ScrollViewProps) {
  return (
    <KeyboardAvoidingView
      style={[styles.fill, style]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      // Height of the tab header above the scroll area.
      keyboardVerticalOffset={90}>
      <ScrollView keyboardShouldPersistTaps="handled" {...props} />
    </KeyboardAvoidingView>
  );
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  disabled,
  loading,
  style,
}: {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'outline';
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
}) {
  const { theme, scale } = usePackContext();
  const primary = variant === 'primary';
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.button,
        {
          backgroundColor: primary ? theme.primary : 'transparent',
          borderColor: theme.primary,
          opacity: disabled ? 0.5 : pressed ? 0.8 : 1,
        },
        style,
      ]}>
      {loading ? (
        <ActivityIndicator color={primary ? theme.primaryText : theme.primary} />
      ) : (
        <Text style={[styles.buttonText, { color: primary ? theme.primaryText : theme.primary, fontSize: 16 * scale }]}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  const { theme } = usePackContext();
  return (
    <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.border }, style]}>{children}</View>
  );
}

export function Chip({ label, selected, onPress }: { label: string; selected?: boolean; onPress: () => void }) {
  const { theme, scale } = usePackContext();
  return (
    <Pressable
      onPress={onPress}
      style={[
        styles.chip,
        { borderColor: theme.primary, backgroundColor: selected ? theme.primary : theme.card },
      ]}>
      <Text style={{ color: selected ? theme.primaryText : theme.primary, fontWeight: '600', fontSize: 15 * scale }}>{label}</Text>
    </Pressable>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  const { theme, scale } = usePackContext();
  return <Text style={[styles.section, { color: theme.textMuted, fontSize: 13 * scale }]}>{children}</Text>;
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  button: {
    minHeight: 48,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: { fontSize: 16, fontWeight: '700' },
  card: { borderRadius: radius.lg, borderWidth: StyleSheet.hairlineWidth, padding: spacing.lg, gap: spacing.sm },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 999,
    borderWidth: 1.5,
  },
  section: {
    fontSize: 13,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
});
