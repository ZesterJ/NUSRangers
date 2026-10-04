import bundled from './guidanceRegistry.json';
import type { ConfirmedIntake, DangerSign, PatientGroup, Symptom } from './types';

/**
 * Guidance registry: reminders from current WHO guidance, shown to the clinician who receives a patient.
 * Entries are matched to the visit note by fixed rules (patient group, symptoms, danger signs, duration);
 * nothing is generated, so the app cannot invent guidance. A copy ships in the app and works offline;
 * when the backend has a newer version it is downloaded and kept on the phone (guidanceStore.ts).
 */
export type GuidanceSource = { title: string; publisher: string; year: number; url: string };
export type GuidanceEntry = {
  id: string;
  /** The condition the entry belongs to, e.g. "Malaria and fever"; groups the Guidance tab. */
  topic?: string;
  title: string;
  sourceId: string;
  /** Patient groups the entry applies to; omitted = all. */
  groups?: PatientGroup[];
  /** Applies when any listed symptom or danger sign is present; omitted = the group alone is enough. */
  any?: { symptoms?: Symptom[]; dangerSigns?: DangerSign[] };
  minDurationDays?: number;
  points: string[];
};
export type GuidanceRegistry = {
  version: number;
  updated: string;
  reviewStatus: string;
  sources: Record<string, GuidanceSource>;
  entries: GuidanceEntry[];
};

export const BUNDLED_REGISTRY = bundled as GuidanceRegistry;

export function guidanceFor(intake: ConfirmedIntake, registry: GuidanceRegistry = BUNDLED_REGISTRY): GuidanceEntry[] {
  return registry.entries.filter((e) => {
    if (e.groups && (!intake.patientGroup || !e.groups.includes(intake.patientGroup))) return false;
    if (e.minDurationDays !== undefined && (intake.durationDays ?? 0) < e.minDurationDays) return false;
    if (!e.any) return true;
    return (
      (e.any.symptoms ?? []).some((s) => intake.symptoms.includes(s)) ||
      (e.any.dangerSigns ?? []).some((d) => intake.dangerSigns.includes(d))
    );
  });
}

/** The whole registry grouped by condition, for browsing. Entries keep their registry order. */
export function guidanceByTopic(registry: GuidanceRegistry = BUNDLED_REGISTRY): { topic: string; entries: GuidanceEntry[] }[] {
  const groups: { topic: string; entries: GuidanceEntry[] }[] = [];
  for (const entry of registry.entries) {
    const topic = entry.topic ?? 'Other';
    const group = groups.find((g) => g.topic === topic);
    if (group) group.entries.push(entry);
    else groups.push({ topic, entries: [entry] });
  }
  return groups.sort((a, b) => a.topic.localeCompare(b.topic));
}
