import { useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { ask } from '@/ai/AiRouter';
import { refreshPending, useSyncStore, type QueuedChat } from '@/ai/sync';
import type { ChatMessage } from '@/api/types';
import { ChatBubble } from '@/components/ChatBubble';
import { OfflineBanner } from '@/components/OfflineBanner';
import { Chip } from '@/components/ui';
import { addMessage, clearMessages, enqueue, listMessages, type StoredMessage } from '@/db';
import { tr } from '@/packs/types';
import { radius, spacing, usePackContext } from '@/theme';

export default function Chat() {
  const { pack, locale, theme } = usePackContext();
  const { t } = useTranslation();
  const { q } = useLocalSearchParams<{ q?: string }>();
  const syncVersion = useSyncStore((s) => s.version);

  const [messages, setMessages] = useState<StoredMessage[]>([]);
  const [input, setInput] = useState(q ?? '');
  const [prevQ, setPrevQ] = useState(q);
  const [thinking, setThinking] = useState(false);
  const listRef = useRef<FlatList<StoredMessage>>(null);

  const reload = useCallback(async () => setMessages(await listMessages(pack.id)), [pack.id]);

  useEffect(() => {
    let cancelled = false;
    listMessages(pack.id).then((m) => !cancelled && setMessages(m));
    return () => {
      cancelled = true;
    };
  }, [pack.id, syncVersion]);

  // Prefill from a Home card action (the tab stays mounted, so react to param changes).
  if (q !== prevQ) {
    setPrevQ(q);
    if (q) setInput(q);
  }

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || thinking) return;
    setInput('');
    const history: ChatMessage[] = messages.slice(-8).map((m) => ({ role: m.role, content: m.text }));
    await addMessage(pack.id, { role: 'user', text: question });
    await reload();
    setThinking(true);
    try {
      const reply = await ask({ pack, locale, question, history });
      await addMessage(pack.id, {
        role: 'assistant',
        text: reply.text,
        source: reply.source,
        suggestSms: reply.suggestSms,
      });
      if (reply.source === 'fallback') {
        const payload: QueuedChat = { packId: pack.id, locale, question, history };
        await enqueue('chat', 0, payload);
        await refreshPending();
      }
    } finally {
      setThinking(false);
      await reload();
    }
  };

  const greeting: StoredMessage = {
    id: -1,
    role: 'assistant',
    text: tr(pack.greeting, locale),
    source: null,
    suggestSms: false,
    createdAt: 0,
  };
  const data = [greeting, ...messages];

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: theme.background }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}>
      <OfflineBanner />
      <FlatList
        ref={listRef}
        data={data}
        keyExtractor={(m) => String(m.id)}
        renderItem={({ item, index }) => (
          <ChatBubble message={item} question={index > 0 ? data[index - 1]?.text : undefined} />
        )}
        contentContainerStyle={{ paddingVertical: spacing.md }}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        ListFooterComponent={
          thinking ? <Text style={[styles.thinking, { color: theme.textMuted }]}>{t('chat.thinking')}</Text> : null
        }
      />

      {messages.length === 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quick}>
          {pack.quickReplies.map((qr) => (
            <Chip key={qr.en} label={tr(qr, locale)} onPress={() => send(tr(qr, locale))} />
          ))}
        </ScrollView>
      )}

      <View style={[styles.inputRow, { borderTopColor: theme.border, backgroundColor: theme.card }]}>
        {messages.length > 0 && (
          <Pressable
            accessibilityLabel={t('chat.clear')}
            onPress={async () => {
              await clearMessages(pack.id);
              reload();
            }}
            hitSlop={8}>
            <Text style={{ fontSize: 20 }}>🗑️</Text>
          </Pressable>
        )}
        <TextInput
          style={[styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.background }]}
          value={input}
          onChangeText={setInput}
          placeholder={t('chat.placeholder')}
          placeholderTextColor={theme.textMuted}
          onSubmitEditing={() => send(input)}
          returnKeyType="send"
          multiline
        />
        <Pressable
          onPress={() => send(input)}
          disabled={!input.trim() || thinking}
          style={[styles.send, { backgroundColor: theme.primary, opacity: !input.trim() || thinking ? 0.5 : 1 }]}>
          <Text style={{ color: theme.primaryText, fontWeight: '700' }}>{t('chat.send')}</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  thinking: { paddingHorizontal: spacing.lg, fontStyle: 'italic' },
  quick: { gap: spacing.sm, paddingHorizontal: spacing.md, paddingBottom: spacing.sm },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: spacing.sm,
    padding: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: 16,
  },
  send: { height: 44, paddingHorizontal: spacing.lg, borderRadius: radius.md, justifyContent: 'center' },
});
