"""Local capability matching only: no clinical inference or availability claims."""
import argparse
from datetime import date
import json
import math
from pathlib import Path

SERVICES = ('generalOutpatient', 'childHealth', 'maternal', 'laboratory', 'imaging', 'emergency')
FIELDS = ('facilityId', 'facilityName', 'county', 'countyId', 'subcounty',
          'facilityLevel', 'facilityType', 'latitude', 'longitude', 'capabilities',
          'dataSource', 'dataYear', 'capabilityObservedAt', 'capabilityVerifiedAt')


def coordinates(lat, lon):
    if lat is None and lon is None:
        return None
    if (type(lat) not in (int, float) or type(lon) not in (int, float)
            or not math.isfinite(lat) or not math.isfinite(lon)
            or not -90 <= lat <= 90 or not -180 <= lon <= 180):
        raise ValueError('Coordinates must be a complete, finite latitude/longitude pair')
    return lat, lon


def validate_facility(row):
    if set(row) != set(FIELDS):
        raise ValueError('Facility fields must match the canonical schema')
    for key in ('facilityId', 'facilityName', 'county', 'dataSource'):
        if not isinstance(row[key], str) or not row[key].strip() or row[key] != row[key].strip():
            raise ValueError(f'{key} must be a nonblank, trimmed string')
    for key in ('countyId', 'subcounty', 'facilityLevel', 'facilityType'):
        if row[key] is not None and (not isinstance(row[key], str) or not row[key].strip()):
            raise ValueError(f'{key} must be a nonblank string or null')
    if row['county'] != 'Kilifi':
        raise ValueError('Only explicitly scoped Kilifi records are supported')
    coordinates(row['latitude'], row['longitude'])
    caps = row['capabilities']
    if not isinstance(caps, dict) or set(caps) != set(SERVICES):
        raise ValueError('All six capabilities must be supplied')
    if any(type(v) is not bool and v != 'unknown' for v in caps.values()):
        raise ValueError('Capabilities must be true, false, or "unknown"')
    year = row['dataYear']
    if year is not None and (type(year) is not int or not 1900 <= year <= date.today().year):
        raise ValueError('Invalid dataYear')
    for key in ('capabilityObservedAt', 'capabilityVerifiedAt'):
        value = row[key]
        if value is not None:
            if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                raise ValueError(f'{key} must be an ISO date or null')
            if date.fromisoformat(value) > date.today():
                raise ValueError(f'{key} cannot be in the future')
    return row


def validate_catalogue(rows):
    if not isinstance(rows, list):
        raise ValueError('Catalogue must be a JSON array')
    unique = {}
    for row in rows:
        validate_facility(row)
        key = row['facilityId']
        if key in unique and unique[key] != row:
            raise ValueError(f'Conflicting duplicate facility ID: {key}')
        unique[key] = row
    return list(unique.values())


def distance_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def service_list(values):
    if not isinstance(values, list) or any(not isinstance(v, str) or v not in SERVICES for v in values):
        raise ValueError('Services must be an array of canonical capability names')
    return set(values)


def route_facilities(facilities, required_services, patient_context=None,
                     patient_coordinates=None, optional_services=None):
    """Requirements are caller-selected; patient context never generates clinical labels.

    Context may carry subjectStatus. Ambiguous subjects block routing. No age,
    pregnancy, urgency, opening-hours, or referral eligibility is inferred.
    """
    rows = validate_catalogue(facilities)
    required = service_list(required_services)
    optional = service_list([] if optional_services is None else optional_services) - required
    context = {} if patient_context is None else patient_context
    if not isinstance(context, dict):
        raise ValueError('patientContext must be an object')
    origin = None
    if patient_coordinates is not None:
        if not isinstance(patient_coordinates, dict) or set(patient_coordinates) != {'latitude', 'longitude'}:
            raise ValueError('patientCoordinates requires latitude and longitude')
        origin = coordinates(**{'lat': patient_coordinates['latitude'], 'lon': patient_coordinates['longitude']})
    result = {'status': 'insufficient_data', 'candidates': [], 'requiresVerification': True,
              'rankingMethod': None, 'availabilityStatus': 'unknown',
              'reasonCodes': [], 'excluded': {'incompatible': 0, 'unknownCapability': 0}}
    if not required or context.get('subjectStatus') == 'ambiguous':
        result['reasonCodes'] = ['requirements_missing' if not required else 'ambiguous_subject']
        return result
    if not rows:
        result['reasonCodes'] = ['no_facility_data']
        return result
    compatible = []
    for row in rows:
        caps = row['capabilities']
        if any(caps[s] is False for s in required):
            result['excluded']['incompatible'] += 1
        elif any(caps[s] == 'unknown' for s in required):
            result['excluded']['unknownCapability'] += 1
        else:
            point = coordinates(row['latitude'], row['longitude'])
            distance = distance_km(origin, point) if origin is not None and point is not None else None
            compatible.append((row, sorted(s for s in optional if caps[s] is True), distance))
    if not compatible:
        result['status'] = 'insufficient_data' if result['excluded']['unknownCapability'] else 'no_compatible_facility'
        result['reasonCodes'] = ['mandatory_capabilities_not_confirmed']
        return result
    # Compare distances only when every compatible candidate has a distance.
    # Missing geography must not silently disadvantage a facility.
    use_distance = all(item[2] is not None for item in compatible)
    compatible.sort(key=lambda item: (-len(item[1]), item[2] if use_distance else 0, item[0]['facilityId']))
    result['status'] = 'candidates_found'
    result['rankingMethod'] = 'optional_matches_then_' + ('straight_line_distance_then_id' if use_distance else 'id')
    if not use_distance:
        result['reasonCodes'].append('incomplete_coordinates_distance_not_used_for_ranking')
    for rank, (row, matches, distance) in enumerate(compatible[:3], 1):
        reasons = [f'Required {s} capability explicitly documented in source' for s in sorted(required)]
        reasons.append(f'{len(matches)} optional capabilities explicitly documented')
        reasons.append('Ordered by straight-line distance within optional-match tier' if use_distance
                       else 'Distance ranking unavailable; facility ID breaks optional-match ties')
        reasons.append('Current opening, staff, equipment and referral availability are unknown')
        result['candidates'].append({
            'facilityId': row['facilityId'], 'facilityName': row['facilityName'], 'rank': rank,
            'matchedServices': sorted(required), 'matchedOptionalServices': matches,
            'distanceKm': round(distance, 3) if distance is not None else None,
            'distanceType': 'straight_line' if distance is not None else None,
            'estimatedTravelMinutes': None, 'availabilityStatus': 'unknown',
            'dataSource': row['dataSource'], 'dataYear': row['dataYear'],
            'capabilityObservedAt': row['capabilityObservedAt'],
            'capabilityVerifiedAt': row['capabilityVerifiedAt'], 'reasons': reasons})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path, help='JSON with requiredServices and optional patientContext, patientCoordinates, optionalServices')
    parser.add_argument('--catalogue', type=Path, default=Path(__file__).resolve().parents[1] / 'data/facilities/catalogue.json')
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text())
        output = route_facilities(json.loads(args.catalogue.read_text()), request['requiredServices'],
                                  request.get('patientContext'), request.get('patientCoordinates'), request.get('optionalServices'))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f'Routing failed: {exc}\n')
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
