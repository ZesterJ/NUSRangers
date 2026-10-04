import data from './kilifiFacilities.json';
import type { CareRouting, ConfirmedIntake } from './types';

/**
 * On-phone care assessment and facility routing: works with no signal.
 * A TypeScript port of the team's rules in ml/src (care_policy.py "care-policy-v1", facility_router.py)
 * and of backend/app/care.py, over the verified Kilifi facilities exported by scripts/export-facilities.py.
 * Keep the three in step when the policy changes.
 *
 * It proposes services and facilities for a person to confirm. It does not diagnose, and facility
 * services come from a historical public-source snapshot: "unknown" is never treated as available.
 */

export type Service = 'generalOutpatient' | 'childHealth' | 'maternal';
export type Coordinates = { latitude: number; longitude: number };

/** Symptoms the policy treats as outside its scope, so it abstains. */
const OUTSIDE_SYMPTOMS = ['difficulty_breathing'];

function groupService(intake: ConfirmedIntake): Service[] {
  if (intake.patientGroup === 'child_u5' || intake.patientGroup === 'child_5plus') return ['childHealth'];
  if (intake.patientGroup === 'pregnant') return ['maternal'];
  return [];
}

/** Which services the visit note calls for, and whether the policy was able to say so itself. */
export function assessServices(intake: ConfirmedIntake): Pick<CareRouting, 'requiredServices' | 'assessmentStatus'> {
  const abstains =
    // The policy abstains on every danger sign: the ones it models, and the ones it has no word for.
    intake.dangerSigns.length > 0 ||
    intake.symptoms.some((s) => OUTSIDE_SYMPTOMS.includes(s));
  if (!abstains && intake.symptoms.length === 0) return { requiredServices: [], assessmentStatus: 'unclear' };
  // When the policy abstains the patient is still told to go to a clinic, so facilities are listed
  // by patient group and the assessment is marked unclear.
  return {
    requiredServices: ['generalOutpatient', ...groupService(intake)],
    assessmentStatus: abstains ? 'unclear' : 'proposed',
  };
}

/** Haversine distance, same radius as ml/src/facility_router.py. */
function distanceKm(a: Coordinates, b: Coordinates) {
  const rad = (d: number) => (d * Math.PI) / 180;
  const h =
    Math.sin(rad(b.latitude - a.latitude) / 2) ** 2 +
    Math.cos(rad(a.latitude)) * Math.cos(rad(b.latitude)) * Math.sin(rad(b.longitude - a.longitude) / 2) ** 2;
  return 6371.0088 * 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, h))));
}

function origin(coordinates?: Coordinates): { point: Coordinates; type: CareRouting['origin'] } {
  const b = data.bounds;
  if (
    coordinates &&
    coordinates.latitude >= b.south &&
    coordinates.latitude <= b.north &&
    coordinates.longitude >= b.west &&
    coordinates.longitude <= b.east
  )
    return { point: coordinates, type: 'patient' };
  // No location, or a phone outside the area the catalogue covers: measure from the demo anchor.
  return { point: data.anchor, type: 'demo_anchor' };
}

export function assessCareOnPhone(intake: ConfirmedIntake, coordinates?: Coordinates): CareRouting {
  const { requiredServices, assessmentStatus } = assessServices(intake);
  const from = origin(coordinates);
  const capabilities = (f: (typeof data.facilities)[number]) => f.capabilities as Record<string, boolean | string>;
  const candidates = requiredServices.length
    ? data.facilities
        // Every required service must be documented; "unknown" excludes the facility.
        .filter((f) => requiredServices.every((s) => capabilities(f)[s] === true))
        .map((f) => ({ f, km: distanceKm(from.point, f) }))
        .sort((a, b) => a.km - b.km || a.f.id.localeCompare(b.f.id))
        .slice(0, 3)
        .map(({ f, km }, i) => ({
          facilityId: f.id,
          facilityName: f.name,
          rank: i + 1,
          distanceKm: Math.round(km * 1000) / 1000,
          matchedServices: [...requiredServices].sort(),
        }))
    : [];
  return {
    requiredServices,
    assessmentStatus,
    routingStatus: candidates.length ? 'candidates_found' : 'insufficient_data',
    candidates,
    origin: from.type,
    limitations: [],
  };
}
