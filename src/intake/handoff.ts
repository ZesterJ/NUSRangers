import * as Crypto from 'expo-crypto';

import { topGroups } from './classification';
import type { IntakeRecord } from './types';

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
  dg?: string[]; // diagnosis groups suggested by the classification model
  f: string | null; // facility id
  c: string; // checksum
};

const PREFIX = 'NURX1:';

async function checksum(body: Omit<Payload, 'c'>) {
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
    ...(topGroups(rec.classification).length ? { dg: topGroups(rec.classification) } : {}),
    f: rec.facilityId,
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
