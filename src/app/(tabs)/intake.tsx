import * as Crypto from 'expo-crypto';
import * as Speech from 'expo-speech';
import { useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Linking, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import { refreshPending } from '@/ai/sync';
import { IntakeSummary } from '@/components/IntakeSummary';
import { OfflineBanner } from '@/components/OfflineBanner';
import { Button, Card, Chip, SectionTitle } from '@/components/ui';
import { VoiceButton } from '@/components/VoiceButton';
import { enqueue, saveIntake } from '@/db';
import { SAMPLE_FACILITIES } from '@/intake/facilities';
import { encodeHandoff } from '@/intake/handoff';
import { QUESTIONS } from '@/intake/questions';
import { recommend } from '@/intake/recommend';
import { extract } from '@/intake/services';
import { triage } from '@/intake/triage';
import {
  DANGER_SIGNS,
  SYMPTOMS,
  type ConfirmedIntake,
  type Extraction,
  type IntakeRecord,
  type PatientGroup,
  type Recommendation,
  type Triage,
} from '@/intake/types';
import { tr } from '@/packs/types';
import { radius, spacing, usePackContext } from '@/theme';

type QuestionId = (typeof QUESTIONS)[number]['id'];
type Step = 'ask' | 'extracting' | 'review' | 'result';

const GROUPS: PatientGroup[] = ['child_u5', 'pregnant', 'adult'];

const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

export default function Intake() {
  const [run, setRun] = useState(0);
  // A new key resets every piece of state for the next patient.
  return <IntakeFlow key={run} onRestart={() => setRun((r) => r + 1)} />;
}

function IntakeFlow({ onRestart }: { onRestart: () => void }) {
  const { locale, theme } = usePackContext();
  const { t } = useTranslation();

  const [step, setStep] = useState<Step>('ask');
  const [qi, setQi] = useState(0);
  const [answers, setAnswers] = useState<Partial<Record<QuestionId, string>>>({});
  const [voiceMsg, setVoiceMsg] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [form, setForm] = useState<ConfirmedIntake | null>(null);
  const [result, setResult] = useState<{ triage: Triage; recs: Recommendation[] } | null>(null);
  const [chosen, setChosen] = useState<string | null>(null);
  const [qr, setQr] = useState<string | null>(null);

  const q = QUESTIONS[qi];
  const answer = answers[q.id] ?? '';
  const setAnswer = (v: string) => setAnswers((a) => ({ ...a, [q.id]: v }));

  // ---------- Step 3: extract, then pre-fill the form ----------
  const finishQuestions = async () => {
    setStep('extracting');
    const ex = await extract(answers, locale);
    setExtraction(ex);
    setForm({
      patientGroup: ex.patientGroup.value,
      symptoms: ex.symptoms.value,
      durationDays: ex.durationDays.value,
      dangerSigns: ex.dangerSigns.value,
      notes: ex.unmapped.join(' · '),
    });
    setStep('review');
  };

  // ---------- Steps 6–7: triage and clinic suggestions ----------
  const confirm = () => {
    if (!form) return;
    const tri = triage(form, extraction ?? undefined);
    const recs = recommend(SAMPLE_FACILITIES, tri);
    setResult({ triage: tri, recs });
    setChosen(recs[0]?.facility.id ?? null);
    setStep('result');
  };

  // ---------- Steps 8 & 10: save locally, queue sync, show QR ----------
  const handoff = async () => {
    if (!form || !result) return;
    const rec: IntakeRecord = {
      id: Crypto.randomUUID().slice(0, 8),
      createdAt: Date.now(),
      locale,
      transcript: QUESTIONS.map((qq) => answers[qq.id] ?? '').filter(Boolean),
      intake: form,
      triage: result.triage,
      facilityId: chosen,
      status: 'handed_off',
    };
    await saveIntake(rec);
    await enqueue('intake', 0, rec);
    await refreshPending();
    setQr(await encodeHandoff(rec));
  };

  return (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <OfflineBanner />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {step === 'ask' && (
          <>
            <Text style={[styles.step, { color: theme.textMuted }]}>
              {t('intake.step', { n: qi + 1, total: QUESTIONS.length })}
            </Text>
            <View style={styles.progress}>
              {QUESTIONS.map((qq, i) => (
                <View key={qq.id} style={[styles.dot, { backgroundColor: i <= qi ? theme.primary : theme.border }]} />
              ))}
            </View>

            <Pressable onPress={() => Speech.speak(tr(q.prompt, locale), { language: locale })}>
              <Text style={[styles.question, { color: theme.text }]}>🔊 {tr(q.prompt, locale)}</Text>
            </Pressable>
            <Text style={{ color: theme.textMuted }}>{tr(q.hint, locale)}</Text>

            <VoiceButton
              onText={(text) => {
                if (text) {
                  setAnswer(text);
                  setVoiceMsg(null);
                } else setVoiceMsg(t('intake.voiceUnavailable'));
              }}
            />
            {voiceMsg && <Text style={{ color: theme.warning }}>{voiceMsg}</Text>}

            <TextInput
              style={[styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.card }]}
              value={answer}
              onChangeText={setAnswer}
              placeholder={t('intake.typeHere')}
              placeholderTextColor={theme.textMuted}
              multiline
            />

            <SectionTitle>{t('intake.samples')}</SectionTitle>
            <View style={styles.chips}>
              {q.samples.map((s) => (
                <Chip key={s.sw} label={locale === 'sw' ? s.sw : `${s.sw} (${s.en})`} onPress={() => setAnswer(s.sw)} />
              ))}
            </View>

            <View style={styles.nav}>
              {qi > 0 && <Button label={t('intake.back')} variant="outline" onPress={() => setQi(qi - 1)} />}
              {qi < QUESTIONS.length - 1 ? (
                <Button label={t('intake.next')} disabled={!answer.trim()} onPress={() => setQi(qi + 1)} style={{ flex: 1 }} />
              ) : (
                <Button label={t('intake.finish')} disabled={!answer.trim()} onPress={finishQuestions} style={{ flex: 1 }} />
              )}
            </View>
          </>
        )}

        {step === 'extracting' && <Text style={[styles.question, { color: theme.text }]}>{t('intake.extracting')}</Text>}

        {step === 'review' && form && extraction && (
          <ReviewForm extraction={extraction} form={form} setForm={setForm} onConfirm={confirm} />
        )}

        {step === 'result' && form && result && (
          <>
            <Text style={[styles.question, { color: theme.text }]}>{t('intake.resultTitle')}</Text>
            <IntakeSummary intake={form} triage={result.triage} />

            {result.triage.level !== 'home_care' && (
              <>
                <SectionTitle>
                  {t('intake.clinics')} · {t('intake.sampleData')}
                </SectionTitle>
                {result.recs.length === 0 && <Text style={{ color: theme.warning }}>{t('intake.noClinic')}</Text>}
                {result.recs.map((r) => {
                  const selected = chosen === r.facility.id;
                  return (
                    <Pressable key={r.facility.id} onPress={() => setChosen(r.facility.id)}>
                      <Card style={selected ? { borderColor: theme.primary, borderWidth: 2 } : undefined}>
                        <View style={styles.clinicHead}>
                          <Text style={[styles.clinicName, { color: theme.text }]}>{r.facility.name}</Text>
                          <Text style={{ color: theme.primary, fontWeight: '700' }}>
                            {selected ? `✓ ${t('intake.chosen')}` : t('intake.choose')}
                          </Text>
                        </View>
                        {r.reasons.map((x) => (
                          <Text key={x} style={{ color: theme.textMuted }}>
                            • {x}
                          </Text>
                        ))}
                        {r.stale && r.facility.phone && (
                          <Pressable onPress={() => Linking.openURL(`tel:${r.facility.phone}`)}>
                            <Text style={{ color: theme.warning, fontWeight: '700' }}>
                              📞 {t('intake.callAhead')} {r.facility.phone}
                            </Text>
                          </Pressable>
                        )}
                      </Card>
                    </Pressable>
                  );
                })}
              </>
            )}

            {!qr ? (
              <Button label={`▦ ${t('intake.handoff')}`} onPress={handoff} />
            ) : (
              <Card style={{ alignItems: 'center' }}>
                <Text style={[styles.clinicName, { color: theme.text }]}>{t('intake.qrTitle')}</Text>
                {/* White quiet zone so the code scans in dark mode too. */}
                <View style={styles.qrBox}>
                  <QRCode value={qr} size={240} ecl="M" />
                </View>
                <Text style={{ color: theme.textMuted, textAlign: 'center' }}>{t('intake.qrHint')}</Text>
                <Text style={{ color: theme.success, textAlign: 'center' }}>✓ {t('intake.saved')}</Text>
              </Card>
            )}
            <Button label={t('intake.newIntake')} variant="outline" onPress={onRestart} />
          </>
        )}
      </ScrollView>
    </View>
  );
}

/** A review field. `low` confidence = the extractor guessed, so the patient is asked to check it. */
function Section({ label, low, children }: { label: string; low: boolean; children: ReactNode }) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  return (
    <View style={[styles.section, low && { borderColor: theme.warning, backgroundColor: theme.card }]}>
      <View style={styles.sectionHead}>
        <Text style={[styles.sectionLabel, { color: theme.text }]}>{label}</Text>
        {low && <Text style={[styles.check, { color: theme.warning }]}>⚠ {t('intake.pleaseCheck')}</Text>}
      </View>
      {children}
    </View>
  );
}

// ---------- Steps 4–5: pre-filled form the patient confirms or corrects ----------
function ReviewForm({
  extraction,
  form,
  setForm,
  onConfirm,
}: {
  extraction: Extraction;
  form: ConfirmedIntake;
  setForm: (f: ConfirmedIntake) => void;
  onConfirm: () => void;
}) {
  const { theme } = usePackContext();
  const { t } = useTranslation();

  return (
    <>
      <Text style={[styles.question, { color: theme.text }]}>{t('intake.reviewTitle')}</Text>
      <Text style={{ color: theme.textMuted }}>{t('intake.reviewHint')}</Text>
      <Text style={{ color: theme.textMuted, fontSize: 12 }}>
        {extraction.source === 'model' ? '☁️' : '📱'} {t(`intake.source.${extraction.source}`)}
      </Text>

      <Section label={t('intake.who')} low={extraction.patientGroup.confidence === 'low'}>
        <View style={styles.chips}>
          {GROUPS.map((g) => (
            <Chip
              key={g}
              label={t(`intake.group.${g}`)}
              selected={form.patientGroup === g}
              onPress={() => setForm({ ...form, patientGroup: g })}
            />
          ))}
        </View>
      </Section>

      <Section label={t('intake.symptoms')} low={extraction.symptoms.confidence === 'low'}>
        <View style={styles.chips}>
          {SYMPTOMS.map((s) => (
            <Chip
              key={s}
              label={t(`intake.sym.${s}`)}
              selected={form.symptoms.includes(s)}
              onPress={() => setForm({ ...form, symptoms: toggle(form.symptoms, s) })}
            />
          ))}
        </View>
      </Section>

      <Section label={t('intake.duration')} low={extraction.durationDays.confidence === 'low'}>
        <TextInput
          style={[styles.input, styles.short, { color: theme.text, borderColor: theme.border, backgroundColor: theme.card }]}
          keyboardType="numeric"
          value={form.durationDays === null ? '' : String(form.durationDays)}
          onChangeText={(v) => setForm({ ...form, durationDays: v === '' ? null : Number(v.replace(/\D/g, '')) })}
        />
      </Section>

      <Section label={t('intake.danger')} low={extraction.dangerSigns.confidence === 'low'}>
        <View style={styles.chips}>
          {DANGER_SIGNS.map((d) => (
            <Chip
              key={d}
              label={t(`intake.ds.${d}`)}
              selected={form.dangerSigns.includes(d)}
              onPress={() => setForm({ ...form, dangerSigns: toggle(form.dangerSigns, d) })}
            />
          ))}
        </View>
      </Section>

      <Section label={t('intake.notes')} low={false}>
        <TextInput
          style={[styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.card }]}
          value={form.notes}
          onChangeText={(v) => setForm({ ...form, notes: v })}
          multiline
        />
      </Section>

      <Button label={`✓ ${t('intake.confirm')}`} onPress={onConfirm} />
    </>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  step: { fontSize: 13, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  progress: { flexDirection: 'row', gap: spacing.xs },
  dot: { flex: 1, height: 4, borderRadius: 2 },
  question: { fontSize: 22, fontWeight: '800', lineHeight: 28 },
  input: { borderWidth: 1, borderRadius: radius.md, padding: spacing.md, minHeight: 56, fontSize: 16 },
  short: { minHeight: 44, width: 120 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  nav: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md },
  section: { gap: spacing.sm, padding: spacing.md, borderRadius: radius.md, borderWidth: 1.5, borderColor: 'transparent' },
  sectionHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  sectionLabel: { fontSize: 16, fontWeight: '700' },
  check: { fontSize: 13, fontWeight: '700' },
  clinicHead: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.sm },
  clinicName: { fontSize: 17, fontWeight: '700', flexShrink: 1 },
  qrBox: { backgroundColor: '#FFFFFF', padding: 16, borderRadius: radius.md, marginVertical: spacing.sm },
});
