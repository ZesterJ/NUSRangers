import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import { VITAL_KEYS, vitalFlags, type ClinicVisit, type NurseTriage } from '@/intake/clinic';
import { encodeTriageReport } from '@/intake/handoff';
import { radius, spacing, usePackContext } from '@/theme';

import { Button, Card } from '../ui';

/** What the doctor reads first: the nurse's priority, vital signs with highlights, and notes. */
export function TriageReport({ visit, triage }: { visit: ClinicVisit; triage: NurseTriage }) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const [qr, setQr] = useState<string | null>(null);

  const color = triage.priority === 'emergency' ? theme.danger : triage.priority === 'priority' ? theme.warning : theme.success;
  const flags = vitalFlags(visit.note, triage.vitals);
  const recorded = VITAL_KEYS.filter((k) => triage.vitals[k] !== undefined);

  return (
    <Card style={{ borderColor: color, borderWidth: 2 }}>
      <Text style={[styles.heading, { color: theme.text }]}>{t('clinic.reportTitle')}</Text>
      <Text style={[styles.priority, { color }]}>{t(`clinic.priorityOpt.${triage.priority}`)}</Text>
      <Text style={{ color: theme.textMuted }}>
        {t('clinic.triagedAt', { time: new Date(triage.triagedAt).toLocaleTimeString() })}
      </Text>

      <View style={styles.block}>
        {recorded.length === 0 && <Text style={{ color: theme.textMuted }}>{t('clinic.noVitals')}</Text>}
        {recorded.map((k) => (
          <View key={k} style={styles.row}>
            <Text style={[styles.label, { color: theme.textMuted }]}>{t(`clinic.v.${k}`)}</Text>
            <Text style={[styles.value, { color: theme.text }]}>{triage.vitals[k]}</Text>
          </View>
        ))}
        {flags.map((f) => (
          <Text key={f} style={{ color: theme.danger, fontWeight: '700' }}>
            ⚠ {t(`clinic.flag.${f}`)}
          </Text>
        ))}
      </View>

      {!!triage.notes && (
        <View style={styles.block}>
          <Text style={[styles.label, { color: theme.textMuted }]}>{t('clinic.nurseNotes')}</Text>
          <Text style={{ color: theme.text }}>{triage.notes}</Text>
        </View>
      )}
      <Text style={{ color: theme.success, fontWeight: '700', marginTop: spacing.md }}>
        ✓ {t(triage.noteEdited ? 'clinic.editedNote' : 'clinic.confirmedNote')}
      </Text>
      <Text style={[styles.note, { color: theme.textMuted }]}>{t('clinic.flagsNote')}</Text>

      {qr ? (
        <View style={{ alignItems: 'center' }}>
          {/* White quiet zone so the code scans in dark mode too. */}
          <View style={styles.qrBox}>
            <QRCode value={qr} size={260} ecl="M" />
          </View>
          <Text style={{ color: theme.textMuted, textAlign: 'center' }}>{t('clinic.qrHint')}</Text>
        </View>
      ) : (
        <Button
          label={`▦ ${t('clinic.showQr')}`}
          variant="outline"
          onPress={async () => setQr(await encodeTriageReport(visit))}
        />
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  heading: { fontSize: 14, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  priority: { fontSize: 24, fontWeight: '800' },
  block: { marginTop: spacing.md, gap: spacing.xs },
  row: { flexDirection: 'row', gap: spacing.md },
  label: { flex: 1, fontSize: 14 },
  value: { fontSize: 15, fontWeight: '700' },
  note: { fontSize: 13, fontStyle: 'italic', marginVertical: spacing.md },
  qrBox: { backgroundColor: '#FFFFFF', padding: 16, borderRadius: radius.md, marginVertical: spacing.sm },
});
