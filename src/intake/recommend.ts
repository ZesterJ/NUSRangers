import type { Facility, Recommendation, Triage } from './types';

/** Capacity data older than this is treated as unknown → "call ahead". */
export const FRESH_HOURS = 24;

/** Longest acceptable journey for each urgency level, in minutes. */
const MAX_TRAVEL: Record<Triage['level'], number> = { refer_now: 180, refer_24h: 150, unsure: 120, home_care: 90 };

/**
 * Offline clinic recommendation. Scores every facility that can meet the patient's needs on:
 *   - likelihood it can see her today (fresh capacity snapshot, else typical staff presence)
 *   - travel time (weighted more heavily when urgent)
 *   - queue length
 * Returns the best two. The health worker or patient chooses; the app never books on its own.
 */
export function recommend(facilities: Facility[], t: Triage, now = Date.now()): Recommendation[] {
  const required = t.needs.filter((n) => n !== 'general');

  const scored = facilities
    .filter((f) => required.every((n) => f.capabilities.includes(n)))
    .filter((f) => f.travelMinutes <= MAX_TRAVEL[t.level])
    .map((f): Recommendation => {
      const reasons: string[] = [];
      const ageH = f.capacity ? (now - Date.parse(f.capacity.updatedAt)) / 3600_000 : Infinity;
      const stale = ageH > FRESH_HOURS;

      const available = stale
        ? f.typicalStaffPresence
        : f.capacity!.staffOnDuty > 0
          ? 0.95
          : 0.05;
      const queuePenalty = stale ? 0 : { short: 0, medium: 0.1, long: 0.2 }[f.capacity!.queue];
      const travelWeight = t.level === 'refer_now' ? 1.6 : 1;
      const travelScore = 1 - Math.min(f.travelMinutes / MAX_TRAVEL[t.level], 1);

      const score = available * 0.55 + travelScore * 0.35 * travelWeight - queuePenalty;

      reasons.push(`${f.travelMinutes} min away`);
      if (required.length) reasons.push(`Offers ${required.join(', ')}`);
      if (stale) reasons.push(`Staffing unknown, usually present ${Math.round(f.typicalStaffPresence * 100)}% of days`);
      else reasons.push(`${f.capacity!.staffOnDuty} staff on duty, ${f.capacity!.queue} queue (${Math.round(ageH)}h ago)`);

      return { facility: f, score: Math.round(score * 100) / 100, reasons, stale };
    })
    .sort((a, b) => b.score - a.score);

  return scored.slice(0, 2);
}
