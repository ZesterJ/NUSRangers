/**
 * Intake record: the JSON contract between speech → extraction → triage → referral → QR handoff.
 * The backend /extract endpoint (jw's parser) must return `Extraction` in exactly this shape.
 * Keep docs/api.md in sync when this changes.
 */

export type PatientGroup = 'child_u5' | 'pregnant' | 'adult';

export const SYMPTOMS = [
  'fever',
  'cough',
  'difficulty_breathing',
  'diarrhoea',
  'vomiting',
  'headache',
  'abdominal_pain',
  'rash',
  'weakness',
] as const;
export type Symptom = (typeof SYMPTOMS)[number];

/** WHO community case management / maternal danger signs. Any one present → refer now. */
export const DANGER_SIGNS = [
  'unable_to_drink',
  'vomits_everything',
  'convulsions',
  'lethargic',
  'chest_indrawing',
  'vaginal_bleeding',
  'severe_headache_blurred_vision',
  'reduced_fetal_movement',
  'blood_in_stool',
] as const;
export type DangerSign = (typeof DANGER_SIGNS)[number];

/** `low` = the model or rules were unsure; the review screen highlights it for the patient to check. */
export type Confidence = 'high' | 'low';
export type Field<T> = { value: T; confidence: Confidence; evidence?: string };

export type Extraction = {
  patientGroup: Field<PatientGroup | null>;
  symptoms: Field<Symptom[]>;
  durationDays: Field<number | null>;
  dangerSigns: Field<DangerSign[]>;
  /** Free-text the extractor could not map to a field. Shown to the clinician, never used for triage. */
  unmapped: string[];
  source: 'rules' | 'model';
};

/** What the patient confirmed on the review screen. */
export type ConfirmedIntake = {
  patientGroup: PatientGroup | null;
  symptoms: Symptom[];
  durationDays: number | null;
  dangerSigns: DangerSign[];
  notes: string;
};

export type TriageLevel = 'refer_now' | 'refer_24h' | 'home_care' | 'unsure';
export type Triage = { level: TriageLevel; reasons: string[]; needs: Capability[] };

export type Capability = 'emergency' | 'maternity' | 'under5' | 'lab' | 'general';

export type Facility = {
  id: string;
  name: string;
  level: 'dispensary' | 'health_centre' | 'sub_county_hospital';
  capabilities: Capability[];
  /** Pre-computed travel time from the user's village (minutes, walking or boda). */
  travelMinutes: number;
  phone?: string;
  /** Last synced capacity snapshot. `null` = never synced. */
  capacity: { staffOnDuty: number; queue: 'short' | 'medium' | 'long'; updatedAt: string } | null;
  /** Typical probability staff are present (e.g. from Service Delivery Indicators absence rates). */
  typicalStaffPresence: number;
};

export type Recommendation = {
  facility: Facility;
  score: number;
  reasons: string[];
  /** True when capacity data is missing or older than the freshness limit → "call ahead". */
  stale: boolean;
};

export type IntakeRecord = {
  id: string;
  createdAt: number;
  locale: string;
  transcript: string[];
  intake: ConfirmedIntake;
  triage: Triage;
  facilityId: string | null;
  status: 'handed_off' | 'received';
};
