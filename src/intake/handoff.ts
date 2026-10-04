import * as Crypto from 'expo-crypto';

import type { ClinicVisit } from './clinic';
import type { DangerSign, IntakeRecord, Symptom } from './types';

/**
 * QR handoff payload. Short keys keep the QR small enough to scan from a cheap phone screen.
 * The checksum detects a corrupted or edited record; it is NOT a signature. Anyone with the app
 * format can create a valid QR, so the clinic still verifies the patient in person.
 */
type Payload = {
  v: 1;
  id: string;
  t: number; // created at (epoch seconds)
  nm?: string; // patient name
  sx?: IntakeRecord['intake']['sex'];
  g: IntakeRecord['intake']['patientGroup'];
  s: string[]; // symptoms
  d: number | null; // duration days
  ds: string[]; // danger signs
  n: string; // notes
  tl: IntakeRecord['triage']['level'];
  r: string[]; // triage reasons
  sv?: string[]; // care services proposed by the backend
  f: string | null; // facility id
  fn?: string; // facility name, for facilities the scanning phone has no list of
  c: string; // checksum
};

const PREFIX = 'NURX1:';

async function checksum(body: unknown) {
  const hex = await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, JSON.stringify(body));
  return hex.slice(0, 12);
}

export async function encodeHandoff(rec: IntakeRecord): Promise<string> {
  const body: Omit<Payload, 'c'> = {
    v: 1,
    id: rec.id,
    t: Math.floor(rec.createdAt / 1000),
    ...(rec.intake.patientName ? { nm: rec.intake.patientName.slice(0, 40) } : {}),
    ...(rec.intake.sex ? { sx: rec.intake.sex } : {}),
    g: rec.intake.patientGroup,
    s: rec.intake.symptoms,
    d: rec.intake.durationDays,
    ds: rec.intake.dangerSigns,
    n: rec.intake.notes.slice(0, 200),
    tl: rec.triage.level,
    r: rec.triage.reasons,
    ...(rec.services?.length ? { sv: rec.services } : {}),
    f: rec.facilityId,
    ...(rec.facilityName ? { fn: rec.facilityName.slice(0, 40) } : {}),
  };
  return PREFIX + JSON.stringify({ ...body, c: await checksum(body) });
}

export type DecodedHandoff = { ok: true; payload: Payload } | { ok: false; error: 'not_ours' | 'unreadable' | 'tampered' };

export async function decodeHandoff(text: string): Promise<DecodedHandoff> {
  if (!text.startsWith(PREFIX)) return { ok: false, error: 'not_ours' };
  let payload: Payload;
  try {
    payload = JSON.parse(text.slice(PREFIX.length));
  } catch {
    return { ok: false, error: 'unreadable' };
  }
  const { c, ...body } = payload;
  if ((await checksum(body)) !== c) return { ok: false, error: 'tampered' };
  return { ok: true, payload };
}

/** The visit note as the clinic stores it once reception has scanned the handoff. */
export function visitFromHandoff(p: Payload): ClinicVisit {
  return {
    id: p.id,
    receivedAt: Date.now(),
    note: {
      patientName: p.nm,
      sex: p.sx,
      patientGroup: p.g,
      symptoms: p.s as Symptom[],
      durationDays: p.d,
      dangerSigns: p.ds as DangerSign[],
      notes: p.n,
    },
    selfTriage: { level: p.tl, reasons: p.r },
    services: p.sv,
    status: 'waiting',
  };
}

// ---------- Triage report: nurse → doctor's phone ----------

const REPORT_PREFIX = 'NURT1:';

/** Same integrity check as the handoff: detects damage or edits, does not authenticate the sender. */
export async function encodeTriageReport(visit: ClinicVisit): Promise<string> {
  const body = { v: 1 as const, visit };
  return REPORT_PREFIX + JSON.stringify({ ...body, c: await checksum(body) });
}

export type DecodedClinicCode =
  | { ok: true; kind: 'visit'; payload: Payload }
  | { ok: true; kind: 'report'; visit: ClinicVisit }
  | { ok: false; error: 'not_ours' | 'unreadable' | 'tampered' };

/** Reads either code the Clinic tab can receive: a patient's visit note, or a nurse's triage report. */
export async function decodeClinicCode(text: string): Promise<DecodedClinicCode> {
  if (!text.startsWith(REPORT_PREFIX)) {
    const handoff = await decodeHandoff(text);
    return handoff.ok ? { ok: true, kind: 'visit', payload: handoff.payload } : handoff;
  }
  let parsed: { v: 1; visit: ClinicVisit; c: string };
  try {
    parsed = JSON.parse(text.slice(REPORT_PREFIX.length));
  } catch {
    return { ok: false, error: 'unreadable' };
  }
  const { c, ...body } = parsed;
  if ((await checksum(body)) !== c) return { ok: false, error: 'tampered' };
  return { ok: true, kind: 'report', visit: parsed.visit };
}
