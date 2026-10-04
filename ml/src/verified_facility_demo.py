"""Rules-first, source-backed routing DEMO; historical evidence is not live readiness.

No learned model is loaded. The original 209-record catalogue is never modified.
"""
import argparse
import copy
import csv
import json
from pathlib import Path

from care_policy import rules_predict
from facility_router import route_facilities, validate_catalogue

ROOT = Path(__file__).resolve().parents[1] / 'data/facilities'
ACCEPTED = {'source_verified_historical', 'source_verified_indexed'}
CAPABILITIES = {'generalOutpatient', 'childHealth', 'maternal'}


def load_subset(root=ROOT):
    original = validate_catalogue(json.loads((root/'catalogue.json').read_text()))
    catalogue = {r['facilityId']: copy.deepcopy(r) for r in original}
    for row in catalogue.values():
        row['capabilities'] = {cap: 'unknown' for cap in row['capabilities']}
    sources = json.loads((root/'evidence/sources.json').read_text())
    crosswalk = {r['facilityId']: r for r in json.loads((root/'evidence/crosswalk.json').read_text())}
    with (root/'verified_capabilities.csv').open(newline='') as stream:
        evidence = list(csv.DictReader(stream))
    seen = set()
    for row in evidence:
        fid, capability, value = row['facilityId'], row['capability'], row['value']
        if fid not in catalogue or fid not in crosswalk or catalogue[fid]['facilityName'] != row['facilityName']:
            raise ValueError('Evidence must reference an exact catalogue ID and name')
        if capability not in CAPABILITIES or value not in ('true', 'false', 'unknown'):
            raise ValueError('Invalid capability or tri-state value')
        if (fid, capability) in seen:
            raise ValueError('Duplicate capability evidence requires adjudication')
        seen.add((fid, capability))
        if row['sourceId'] not in sources or sources[row['sourceId']]['url'] != row['source']:
            raise ValueError('Unregistered evidence source')
        if not row['evidence'].strip() or row['matchStatus'] != crosswalk[fid]['matchStatus']:
            raise ValueError('Missing evidence or inconsistent crosswalk')
        if value != 'unknown':
            if row['verificationStatus'] not in ACCEPTED or row['matchStatus'] == 'unresolved':
                raise ValueError('Unverified or unresolved claims cannot be used')
            # This evidence release contains no documented negatives. Fail rather than
            # allowing a future CSV edit to silently fabricate false values.
            if value == 'false':
                raise ValueError('Explicit negatives require a separately reviewed evidence release')
            catalogue[fid]['capabilities'][capability] = True
        elif row['verificationStatus'] != 'unknown':
            raise ValueError('Unknown values must be labelled unknown')
    selected = {fid for fid, _ in seen}
    if seen != {(fid, cap) for fid in selected for cap in CAPABILITIES}:
        raise ValueError('Every selected facility needs all three capability rows')
    for fid in selected:
        # Row-level dates cannot describe heterogeneous historical observations.
        # Per-capability evidence is attached to every returned candidate below.
        catalogue[fid]['dataSource'] = 'verified_capabilities.csv; see candidate capabilityEvidence for public URLs'
        catalogue[fid]['capabilityObservedAt'] = None
        catalogue[fid]['capabilityVerifiedAt'] = None
    return [catalogue[fid] for fid in sorted(selected)], evidence


def route_verified(required_services, coordinates=None, root=ROOT):
    subset, evidence = load_subset(root)
    result = route_facilities(subset, required_services, patient_coordinates=coordinates)
    result['evidenceMode'] = 'documented_source_snapshot_demo_including_historical_observations'
    result['limitations'] = ['Not current capability verification or clinical suitability',
                            'No live opening, beds, staffing, waiting time or referral acceptance data',
                            'Matches and service mappings require human confirmation']
    for candidate in result['candidates']:
        candidate['capabilityEvidence'] = [r for r in evidence if r['facilityId'] == candidate['facilityId'] and r['capability'] in required_services]
    return result


def assess_and_route(patient, coordinates=None, root=ROOT):
    """Default generator is explicit care policy; learned classifier stays experimental."""
    services = rules_predict(patient)
    return {'careAssessment': {'requiredServices': services, 'generator': 'care-policy-v1-rules',
                              'status': 'proposed' if services else 'unclear', 'requiresVerification': True},
            'routing': route_verified(services, coordinates, root)}


def examples(root=ROOT):
    original = json.loads((root/'catalogue.json').read_text())
    # Source anchor is a demonstration reference, not fabricated patient geography.
    anchor = next(r for r in original if r['facilityName'] == 'KILIFI DISTRICT HOSPITAL')
    coordinates = {key: anchor[key] for key in ('latitude', 'longitude')}
    return {'reference': {'name': anchor['facilityName'], 'coordinates': coordinates,
                          'purpose': 'source-coordinate demo anchor, not a patient'},
            'generalOutpatient': route_verified(['generalOutpatient'], coordinates, root),
            'childHealth': route_verified(['childHealth'], coordinates, root),
            'maternal': route_verified(['maternal'], coordinates, root),
            'noConfirmedCompatibleFacility': route_verified(['imaging'], coordinates, root),
            'unknownCapabilityExclusion': route_verified(['generalOutpatient', 'childHealth', 'maternal'], coordinates, root)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patient', type=Path, help='Full structured care-policy patient projection; uses rules only')
    args = parser.parse_args()
    output = assess_and_route(json.loads(args.patient.read_text())) if args.patient else examples()
    print(json.dumps(output, indent=2, allow_nan=False))
