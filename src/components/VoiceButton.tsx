import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
} from 'expo-audio';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text } from 'react-native';

import { transcribe } from '@/intake/services';
import { radius, spacing, usePackContext } from '@/theme';

type Props = {
  /** Called with the transcript, or null when speech could not be turned into text. */
  onText: (text: string | null) => void;
};

/** Step 1–2: record one answer, then send it for speech-to-text. */
export function VoiceButton({ onText }: Props) {
  const { locale, theme } = usePackContext();
  const { t } = useTranslation();
  // LOW_QUALITY keeps uploads small on weak connections; speech models only need ~16 kHz mono.
  const recorder = useAudioRecorder(RecordingPresets.LOW_QUALITY);
  const [state, setState] = useState<'idle' | 'recording' | 'transcribing'>('idle');

  const start = async () => {
    const perm = await requestRecordingPermissionsAsync();
    if (!perm.granted) return;
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
    await recorder.prepareToRecordAsync();
    recorder.record();
    setState('recording');
  };

  const stop = async () => {
    await recorder.stop();
    setState('transcribing');
    const text = recorder.uri ? await transcribe(recorder.uri, locale) : null;
    setState('idle');
    onText(text);
  };

  const recording = state === 'recording';
  return (
    <Pressable
      accessibilityRole="button"
      onPress={recording ? stop : start}
      disabled={state === 'transcribing'}
      style={[
        styles.button,
        { backgroundColor: recording ? theme.danger : theme.primary, opacity: state === 'transcribing' ? 0.6 : 1 },
      ]}>
      <Text style={[styles.text, { color: theme.primaryText }]}>
        {state === 'idle' && `🎙 ${t('intake.speak')}`}
        {recording && `■ ${t('intake.stop')} · ${t('intake.listening')}`}
        {state === 'transcribing' && t('intake.transcribing')}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: { minHeight: 56, borderRadius: radius.lg, alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing.lg },
  text: { fontSize: 17, fontWeight: '700' },
});
