import { CameraView, useCameraPermissions } from 'expo-camera';
import { useIsFocused } from 'expo-router';
import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { IntakeSummary } from '@/components/IntakeSummary';
import { Button, Card } from '@/components/ui';
import { markIntakeReceived } from '@/db';
import { decodeHandoff, type DecodedHandoff } from '@/intake/handoff';
import type { DangerSign, Symptom } from '@/intake/types';
import { radius, spacing, usePackContext } from '@/theme';

/** Step 9: the clinic scans the patient's handoff QR and verifies it was not changed. */
export default function Scan() {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const focused = useIsFocused();
  const [permission, requestPermission] = useCameraPermissions();
  const [result, setResult] = useState<DecodedHandoff | null>(null);
  const [received, setReceived] = useState(false);
  const busy = useRef(false);

  const onScan = async ({ data }: { data: string }) => {
    if (busy.current || result) return;
    busy.current = true;
    setResult(await decodeHandoff(data));
    busy.current = false;
  };

  const reset = () => {
    setResult(null);
    setReceived(false);
  };

  if (!permission) return <View style={{ flex: 1, backgroundColor: theme.background }} />;

  if (!permission.granted) {
    return (
      <View style={[styles.center, { backgroundColor: theme.background }]}>
        <Text style={{ color: theme.text, textAlign: 'center' }}>{t('scan.permission')}</Text>
        <Button label={t('scan.grant')} onPress={requestPermission} />
      </View>
    );
  }

  if (result?.ok) {
    const p = result.payload;
    const facilityName = p.fn;
    return (
      <ScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={styles.content}>
        <Text style={[styles.title, { color: theme.success }]}>✓ {t('scan.verified')}</Text>
        <Text style={{ color: theme.textMuted }}>
          #{p.id} · {new Date(p.t * 1000).toLocaleString()}
          {facilityName ? ` · ${facilityName}` : ''}
        </Text>
        <IntakeSummary
          intake={{
            patientName: p.nm,
            sex: p.sx,
            patientGroup: p.g,
            symptoms: p.s as Symptom[],
            durationDays: p.d,
            dangerSigns: p.ds as DangerSign[],
            notes: p.n,
          }}
          triage={{ level: p.tl, reasons: p.r, needs: [] }}
          services={p.sv}
        />
        <Text style={{ color: theme.warning }}>{t('scan.checkInPerson')}</Text>
        {received ? (
          <Text style={[styles.title, { color: theme.success }]}>✓ {t('scan.received')}</Text>
        ) : (
          <Button
            label={t('scan.markReceived')}
            onPress={async () => {
              // Updates the local record when the same phone made it; on another phone this is the clinic's own receipt.
              await markIntakeReceived(p.id);
              setReceived(true);
            }}
          />
        )}
        <Button label={t('scan.scanAgain')} variant="outline" onPress={reset} />
      </ScrollView>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <View style={styles.cameraBox}>
        {focused && (
          <CameraView
            style={StyleSheet.absoluteFill}
            facing="back"
            barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
            onBarcodeScanned={result ? undefined : onScan}
          />
        )}
        <View style={styles.frame} pointerEvents="none" />
      </View>
      <View style={styles.content}>
        <Text style={[styles.title, { color: theme.text }]}>{t('scan.title')}</Text>
        <Text style={{ color: theme.textMuted }}>{t('scan.hint')}</Text>
        {result && !result.ok && (
          <Card style={{ borderColor: theme.danger, borderWidth: 2 }}>
            <Text style={{ color: theme.danger, fontWeight: '700' }}>{t(`scan.${result.error}`)}</Text>
            <Button label={t('scan.scanAgain')} variant="outline" onPress={reset} />
          </Card>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.lg },
  content: { padding: spacing.lg, gap: spacing.md },
  title: { fontSize: 20, fontWeight: '800' },
  cameraBox: { height: 340, backgroundColor: '#000', alignItems: 'center', justifyContent: 'center' },
  frame: { width: 220, height: 220, borderWidth: 3, borderColor: '#FFFFFF', borderRadius: radius.lg },
});
