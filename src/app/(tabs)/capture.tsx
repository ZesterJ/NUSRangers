import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';

import { refreshPending, type QueuedReport } from '@/ai/sync';
import type { AiSource } from '@/ai/types';
import { api } from '@/api/client';
import { AssessmentCard } from '@/components/AssessmentCard';
import { FormFieldInput } from '@/components/FormFieldInput';
import { OfflineBanner } from '@/components/OfflineBanner';
import { Button } from '@/components/ui';
import { addReport, enqueue, setReportResult } from '@/db';
import type { Assessment, FormValues } from '@/packs/types';
import { tr } from '@/packs/types';
import { isOnline } from '@/store/connectivity';
import { getSettings } from '@/store/settings';
import { spacing, usePackContext } from '@/theme';

export default function Capture() {
  const { pack } = usePackContext();
  // Remount on pack switch so form state resets.
  return <CaptureScreen key={pack.id} />;
}

function CaptureScreen() {
  const { pack, locale, theme } = usePackContext();
  const { t } = useTranslation();
  const form = pack.captureForm;

  const [values, setValues] = useState<FormValues>({});
  const [photo, setPhoto] = useState<string>();
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ assessment: Assessment; source: AiSource } | null>(null);

  const submit = async () => {
    const missing = form.fields.find((f) => f.required && (values[f.key] === undefined || values[f.key] === ''));
    if (missing) return Alert.alert(t('capture.required', { field: tr(missing.label, locale) }));

    setSubmitting(true);
    // The photo URI is device-local; only the base64 travels to the backend.
    const { [form.fields.find((f) => f.type === 'photo')?.key ?? '']: _uri, ...fields } = values;
    try {
      const id = await addReport(pack.id, fields, photo);
      const canUseCloud = isOnline() && getSettings().aiMode !== 'offline';

      if (canUseCloud) {
        try {
          const assessment = await api.analyze({ packId: pack.id, locale, fields, imageBase64: photo });
          await setReportResult(id, assessment, 'cloud');
          setResult({ assessment, source: 'cloud' });
          return;
        } catch (e) {
          console.warn('[capture] analyze failed, using offline rules', e);
        }
      }

      const assessment = pack.offlineAssess?.(fields, locale) ?? { summary: t('history.noResult'), actions: [] };
      await setReportResult(id, assessment, 'offline');
      const payload: QueuedReport = { packId: pack.id, locale, fields };
      await enqueue('report', id, payload);
      await refreshPending();
      setResult({ assessment, source: 'offline' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <OfflineBanner />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={[styles.title, { color: theme.text }]}>{tr(form.title, locale)}</Text>
        {form.intro && <Text style={{ color: theme.textMuted, marginBottom: spacing.lg }}>{tr(form.intro, locale)}</Text>}

        {result ? (
          <>
            <AssessmentCard assessment={result.assessment} source={result.source} />
            {result.source !== 'cloud' && <Text style={{ color: theme.textMuted }}>{t('capture.queued')}</Text>}
            <Button
              label={t('capture.newReport')}
              variant="outline"
              onPress={() => {
                setValues({});
                setPhoto(undefined);
                setResult(null);
              }}
            />
          </>
        ) : (
          <>
            {form.fields
              .filter((f) => f.type !== 'photo' || pack.features.camera)
              .map((f) => (
                <FormFieldInput
                  key={f.key}
                  field={f}
                  value={values[f.key]}
                  onChange={(v) => setValues((prev) => ({ ...prev, [f.key]: v }))}
                  onPhoto={setPhoto}
                />
              ))}
            <Button label={tr(form.submitLabel, locale) || t('capture.submit')} loading={submitting} onPress={submit} />
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  title: { fontSize: 22, fontWeight: '800' },
});
