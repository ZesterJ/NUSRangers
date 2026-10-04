import { CameraView, useCameraPermissions } from 'expo-camera';
import { router, useFocusEffect, useIsFocused, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { NoteRows } from '@/components/clinic/NoteRows';
import { TriageForm } from '@/components/clinic/TriageForm';
import { TriageReport } from '@/components/clinic/TriageReport';
import { GuidanceCard } from '@/components/GuidanceCard';
import { IntakeSummary } from '@/components/IntakeSummary';
import { Button, Card, KeyboardScrollView, SectionTitle } from '@/components/ui';
import { listClinicVisits, markIntakeReceived, saveClinicVisit } from '@/db';
import { sortQueue, type ClinicVisit } from '@/intake/clinic';
import { decodeClinicCode, visitFromHandoff, type DecodedClinicCode } from '@/intake/handoff';
import { radius, spacing, usePackContext } from '@/theme';

type View_ = { kind: 'queue'; reportsOnly?: boolean } | { kind: 'scan' } | { kind: 'visit'; id: string; editing?: boolean };

/**
 * Clinic tab. Reception scans the patient's visit note into the queue (step 9), the nurse adds vital
 * signs and a priority to make the triage report, and the doctor opens that report: on this phone, or
 * on their own by scanning the report's code.
 */
export default function Clinic() {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const focused = useIsFocused();
  const [permission, requestPermission] = useCameraPermissions();
  const [view, setView] = useState<View_>({ kind: 'queue' });
  const [visits, setVisits] = useState<ClinicVisit[]>([]);
  const [scanned, setScanned] = useState<DecodedClinicCode | null>(null);
  const busy = useRef(false);

  const reload = useCallback(() => {
    listClinicVisits()
      .then(setVisits)
      .catch((e) => console.warn('[clinic] could not load the queue', e));
  }, []);
  useFocusEffect(reload);

  const save = async (visit: ClinicVisit) => {
    await saveClinicVisit(visit);
    setVisits((all) => [...all.filter((v) => v.id !== visit.id), visit]);
  };

  const onScan = async ({ data }: { data: string }) => {
    if (busy.current || scanned) return;
    busy.current = true;
    const result = await decodeClinicCode(data);
    if (result.ok && result.kind === 'report') {
      // A nurse's triage report from another phone: store it here and open it for the doctor.
      await save(result.visit);
      setView({ kind: 'visit', id: result.visit.id });
    } else setScanned(result);
    busy.current = false;
  };

  const openScanner = () => {
    setScanned(null);
    setView({ kind: 'scan' });
  };

  // A Home card can ask for the scanner or the triage reports directly. The request is applied once
  // during render, then cleared from the route so that tapping the tab later shows the queue again.
  const { mode } = useLocalSearchParams<{ mode?: 'scan' | 'reports' }>();
  const [appliedMode, setAppliedMode] = useState<string | undefined>(undefined);
  if (mode !== appliedMode) {
    setAppliedMode(mode);
    if (mode) {
      setScanned(null);
      setView(mode === 'scan' ? { kind: 'scan' } : { kind: 'queue', reportsOnly: true });
    }
  }
  useEffect(() => {
    if (mode) router.setParams({ mode: undefined });
  }, [mode]);

  // ---------- A patient: nurse triage, then the triage report ----------
  const visit = view.kind === 'visit' ? visits.find((v) => v.id === view.id) : undefined;
  if (view.kind === 'visit' && visit) {
    const showForm = !visit.triage || view.editing;
    return (
      <KeyboardScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={styles.content}>
        <Text style={[styles.title, { color: theme.text }]}>{visit.note.patientName || `#${visit.id}`}</Text>
        <Text style={{ color: theme.textMuted }}>
          #{visit.id} · {t(`clinic.status.${visit.status}`)}
        </Text>

        {visit.triage && !view.editing && <TriageReport visit={visit} triage={visit.triage} />}
        {showForm && (
          <TriageForm
            visit={visit}
            onSave={async (triage, note) => {
              // Keep the patient's own answers when the nurse corrected them.
              const patientNote = triage.noteEdited ? (visit.patientNote ?? visit.note) : undefined;
              await save({ ...visit, note, patientNote, triage, status: 'triaged' });
              setView({ kind: 'visit', id: visit.id });
            }}
          />
        )}

        {showForm ? (
          <>
            <SectionTitle>{t('clinic.patientReported')}</SectionTitle>
            <IntakeSummary
              intake={visit.patientNote ?? visit.note}
              triage={{ ...visit.selfTriage, needs: [] }}
              services={visit.services}
            />
          </>
        ) : (
          <>
            <SectionTitle>{t('clinic.confirmedTitle')}</SectionTitle>
            <Card>
              <NoteRows note={visit.note} />
            </Card>
            {visit.patientNote && (
              <>
                <SectionTitle>{t('clinic.originalTitle')}</SectionTitle>
                <Card>
                  <NoteRows note={visit.patientNote} />
                </Card>
              </>
            )}
          </>
        )}
        <GuidanceCard intake={visit.note} />

        {visit.status === 'triaged' && !view.editing && (
          <>
            <Button label={`✓ ${t('clinic.markSeen')}`} onPress={() => save({ ...visit, status: 'seen' })} />
            <Button label={t('clinic.editTriage')} variant="outline" onPress={() => setView({ ...view, editing: true })} />
          </>
        )}
        <Button label={t('clinic.back')} variant="outline" onPress={() => setView({ kind: 'queue' })} />
      </KeyboardScrollView>
    );
  }

  // ---------- Reception: scan a code ----------
  if (view.kind === 'scan') {
    if (!permission) return <View style={{ flex: 1, backgroundColor: theme.background }} />;
    if (!permission.granted) {
      return (
        <View style={[styles.center, { backgroundColor: theme.background }]}>
          <Text style={{ color: theme.text, textAlign: 'center' }}>{t('scan.permission')}</Text>
          <Button label={t('scan.grant')} onPress={requestPermission} />
          <Button label={t('clinic.back')} variant="outline" onPress={() => setView({ kind: 'queue' })} />
        </View>
      );
    }

    if (scanned?.ok && scanned.kind === 'visit') {
      const p = scanned.payload;
      const received = visitFromHandoff(p);
      return (
        <KeyboardScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={styles.content}>
          <Text style={[styles.title, { color: theme.success }]}>✓ {t('scan.verified')}</Text>
          <Text style={{ color: theme.textMuted }}>
            #{p.id} · {new Date(p.t * 1000).toLocaleString()}
            {p.fn ? ` · ${p.fn}` : ''}
          </Text>
          <IntakeSummary intake={received.note} triage={{ ...received.selfTriage, needs: [] }} services={p.sv} />
          <Text style={{ color: theme.warning }}>{t('scan.checkInPerson')}</Text>
          <Button
            label={t('clinic.addToQueue')}
            onPress={async () => {
              // Keeps an existing triage if the same code is scanned twice.
              const existing = visits.find((v) => v.id === received.id);
              if (!existing) await save(received);
              // Updates the patient's own record when the same phone made it.
              await markIntakeReceived(p.id);
              setView({ kind: 'visit', id: received.id });
            }}
          />
          <Button label={t('scan.scanAgain')} variant="outline" onPress={openScanner} />
        </KeyboardScrollView>
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
              onBarcodeScanned={scanned ? undefined : onScan}
            />
          )}
          <View style={styles.frame} pointerEvents="none" />
        </View>
        <View style={styles.content}>
          <Text style={{ color: theme.textMuted }}>{t('scan.hint')}</Text>
          {scanned && !scanned.ok && (
            <Card style={{ borderColor: theme.danger, borderWidth: 2 }}>
              <Text style={{ color: theme.danger, fontWeight: '700' }}>{t(`scan.${scanned.error}`)}</Text>
              <Button label={t('scan.scanAgain')} variant="outline" onPress={openScanner} />
            </Card>
          )}
          <Button label={t('clinic.back')} variant="outline" onPress={() => setView({ kind: 'queue' })} />
        </View>
      </View>
    );
  }

  // ---------- The queue ----------
  const reportsOnly = view.kind === 'queue' && view.reportsOnly;
  const shown = sortQueue(visits).filter((v) => !reportsOnly || v.triage);
  return (
    <KeyboardScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={styles.content}>
      <Text style={[styles.title, { color: theme.text }]}>{t(reportsOnly ? 'clinic.reportsTitle' : 'clinic.queueTitle')}</Text>
      {reportsOnly ? (
        <Button label={t('clinic.showAll')} variant="outline" onPress={() => setView({ kind: 'queue' })} />
      ) : (
        <Button label={`📷 ${t('clinic.scanButton')}`} onPress={openScanner} />
      )}
      {shown.length === 0 && <Text style={{ color: theme.textMuted }}>{t(reportsOnly ? 'clinic.noReports' : 'clinic.empty')}</Text>}
      {shown.map((v) => {
        const color =
          v.status !== 'triaged' || !v.triage
            ? theme.textMuted
            : v.triage.priority === 'emergency'
              ? theme.danger
              : v.triage.priority === 'priority'
                ? theme.warning
                : theme.success;
        return (
          <Pressable key={v.id} onPress={() => setView({ kind: 'visit', id: v.id })}>
            <Card style={{ borderLeftColor: color, borderLeftWidth: 6 }}>
              <Text style={[styles.name, { color: theme.text }]}>{v.note.patientName || `#${v.id}`}</Text>
              <Text style={{ color: theme.textMuted }}>
                {v.note.patientGroup ? t(`intake.group.${v.note.patientGroup}`) : '—'} · {new Date(v.receivedAt).toLocaleTimeString()}
              </Text>
              <Text style={{ color, fontWeight: '700' }}>
                {t(`clinic.status.${v.status}`)}
                {v.status === 'triaged' && v.triage ? ` · ${t(`clinic.priorityOpt.${v.triage.priority}`)}` : ''}
              </Text>
            </Card>
          </Pressable>
        );
      })}
    </KeyboardScrollView>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.lg },
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  title: { fontSize: 20, fontWeight: '800' },
  name: { fontSize: 17, fontWeight: '700' },
  cameraBox: { height: 340, backgroundColor: '#000', alignItems: 'center', justifyContent: 'center' },
  frame: { width: 220, height: 220, borderWidth: 3, borderColor: '#FFFFFF', borderRadius: radius.lg },
});
