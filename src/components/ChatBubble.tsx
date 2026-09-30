import * as Speech from 'expo-speech';
import { useTranslation } from 'react-i18next';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { sendViaSms } from '@/ai/strategies/smsFallback';
import type { StoredMessage } from '@/db';
import { radius, spacing, usePackContext } from '@/theme';

import { SourceBadge } from './SourceBadge';

export function ChatBubble({ message, question }: { message: StoredMessage; question?: string }) {
  const { pack, locale, theme } = usePackContext();
  const { t } = useTranslation();
  const isUser = message.role === 'user';

  const onSms = async () => {
    const ok = await sendViaSms(pack, question ?? message.text);
    if (!ok) Alert.alert(t('chat.smsFailed'));
  };

  return (
    <View style={[styles.row, { justifyContent: isUser ? 'flex-end' : 'flex-start' }]}>
      <View
        style={[
          styles.bubble,
          isUser
            ? { backgroundColor: theme.primary, borderBottomRightRadius: 4 }
            : { backgroundColor: theme.card, borderColor: theme.border, borderWidth: StyleSheet.hairlineWidth, borderBottomLeftRadius: 4 },
        ]}>
        {!isUser && message.source && <SourceBadge source={message.source} />}
        <Text style={[styles.text, { color: isUser ? theme.primaryText : theme.text }]}>{message.text}</Text>
        {!isUser && (
          <View style={styles.actions}>
            {pack.features.voice && (
              <Pressable onPress={() => Speech.speak(message.text, { language: locale })} hitSlop={8}>
                <Text style={[styles.action, { color: theme.primary }]}>🔊 {t('chat.speak')}</Text>
              </Pressable>
            )}
            {message.suggestSms && pack.features.sms && (
              <Pressable onPress={onSms} hitSlop={8}>
                <Text style={[styles.action, { color: theme.primary }]}>✉️ {t('chat.sms')}</Text>
              </Pressable>
            )}
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', paddingHorizontal: spacing.md, marginVertical: spacing.xs },
  bubble: { maxWidth: '85%', borderRadius: radius.lg, padding: spacing.md, gap: spacing.xs },
  text: { fontSize: 16, lineHeight: 22 },
  actions: { flexDirection: 'row', gap: spacing.lg, marginTop: spacing.xs },
  action: { fontSize: 13, fontWeight: '600' },
});
