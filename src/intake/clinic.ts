import type { ConfirmedIntake, TriageLevel } from './types';

/**
 * Clinic side of the flow: reception scans the visit note into the queue, the nurse adds vital signs
 * and a triage priority to make a triage report, and the doctor reads that report.
 * The app highlights and suggests; the nurse and the doctor decide.
 */
export const VITAL_KEYS = ['temperatureC', 'pulse', 'respiratoryRate', 'systolic', 'diastolic', 'spo2', 'weightKg'] as const;
export type VitalKey = (typeof VITAL_KEYS)[number];
export type Vitals = Partial<Record<VitalKey, number>>;

export const PRIORITIES = ['emergency', 'priority', 'routine'] as const;
export type NursePriority = (typeof PRIORITIES)[number];

export type NurseTriage = { vitals: Vitals; priority: NursePriority; notes: string; triagedAt: number };

export type ClinicVisit = {
  /** Same id as the patient's visit note. */
  id: string;
  receivedAt: number;
  note: ConfirmedIntake;
  /** What the patient's phone suggested before arrival. */
  selfTriage: { level: TriageLevel; reasons: string[] };
  services?: string[];
  status: 'waiting' | 'triaged' | 'seen';
  triage?: NurseTriage;
};

export type VitalFlag = 'fever' | 'low_spo2' | 'fast_breathing_child' | 'raised_bp_pregnancy' | 'severe_bp_pregnancy';

/**
 * Automatic highlights on the vital signs, for the nurse to check. Draft thresholds, not yet clinically
 * reviewed: fever 38.0 °C; oxygen saturation under 90%; fast breathing in a child under 5 (40 per minute,
 * the IMCI threshold from 12 months; it is 50 under 12 months, and the app does not know the age in months);
 * blood pressure in pregnancy 140/90, severe from 160/110.
 */
export function vitalFlags(note: ConfirmedIntake, v: Vitals): VitalFlag[] {
  const flags: VitalFlag[] = [];
  if (v.temperatureC !== undefined && v.temperatureC >= 38) flags.push('fever');
  if (v.spo2 !== undefined && v.spo2 < 90) flags.push('low_spo2');
  if (note.patientGroup === 'child_u5' && v.respiratoryRate !== undefined && v.respiratoryRate >= 40)
    flags.push('fast_breathing_child');
  if (note.patientGroup === 'pregnant') {
    const sys = v.systolic ?? 0;
    const dia = v.diastolic ?? 0;
    if (sys >= 160 || dia >= 110) flags.push('severe_bp_pregnancy');
    else if (sys >= 140 || dia >= 90) flags.push('raised_bp_pregnancy');
  }
  return flags;
}

/** A starting point for the nurse, who makes the decision. It never suggests lower than the evidence allows. */
export function suggestedPriority(visit: Pick<ClinicVisit, 'note' | 'selfTriage'>, vitals: Vitals): NursePriority {
  const flags = vitalFlags(visit.note, vitals);
  if (
    visit.note.dangerSigns.length > 0 ||
    visit.selfTriage.level === 'refer_now' ||
    flags.includes('low_spo2') ||
    flags.includes('severe_bp_pregnancy')
  )
    return 'emergency';
  if (flags.length > 0 || visit.selfTriage.level === 'refer_24h' || visit.selfTriage.level === 'unsure') return 'priority';
  return 'routine';
}

const STATUS_ORDER = { triaged: 0, waiting: 1, seen: 2 };
const PRIORITY_ORDER = { emergency: 0, priority: 1, routine: 2 };

/** Doctor's order of work: triaged patients by priority, then those waiting for the nurse, then those already seen. */
export function sortQueue(visits: ClinicVisit[]): ClinicVisit[] {
  return [...visits].sort(
    (a, b) =>
      STATUS_ORDER[a.status] - STATUS_ORDER[b.status] ||
      (a.triage && b.triage ? PRIORITY_ORDER[a.triage.priority] - PRIORITY_ORDER[b.triage.priority] : 0) ||
      a.receivedAt - b.receivedAt,
  );
}
