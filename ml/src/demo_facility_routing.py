"""Demonstrate strict service routing and a separate geographic directory lookup.

The reference point is a source facility, NOT a real patient or town-centre estimate.
Geographic neighbours are NOT compatible-care candidates.
"""
import json
from pathlib import Path

from facility_router import distance_km, route_facilities, validate_catalogue

ROOT = Path(__file__).resolve().parents[1] / 'data/facilities'
REFERENCE_ID = 'arcgis:f5876f6990e141198c92847f2c780afe:0:c7c3c0ed-1708-4201-a8aa-cfd0a125111a'


def demonstrate(catalogue, source_attributes):
    catalogue = validate_catalogue(catalogue)
    reference = next(r for r in catalogue if r['facilityId'] == REFERENCE_ID)
    origin = {'latitude': reference['latitude'], 'longitude': reference['longitude']}
    routing = route_facilities(catalogue, ['childHealth'], patient_coordinates=origin)
    attributes = {r['facilityId']: r for r in source_attributes}
    nearby = []
    for row in catalogue:
        if row['facilityId'] == REFERENCE_ID or row['latitude'] is None or row['longitude'] is None:
            continue
        distance = distance_km((origin['latitude'], origin['longitude']), (row['latitude'], row['longitude']))
        nearby.append((distance, row))
    nearby.sort(key=lambda item: (item[0], item[1]['facilityId']))
    return {
        'reference': {'facilityId': REFERENCE_ID, 'facilityName': reference['facilityName'],
                      'coordinates': origin, 'purpose': 'geographic demo anchor; not patient coordinates'},
        'serviceRouting': routing,
        'geographicDirectory': {
            'purpose': 'Nearby source records only; no confirmed service compatibility or referral recommendation',
            'referenceFacilityExcluded': True, 'requiresVerification': True,
            'entries': [{'facilityId': row['facilityId'], 'facilityName': row['facilityName'],
                         'distanceKm': round(distance, 3), 'distanceType': 'straight_line',
                         'estimatedTravelMinutes': None, 'availabilityStatus': 'unknown',
                         'serviceCompatibility': 'unknown',
                         'coordinateSource': attributes[row['facilityId']]['coordinateSource'],
                         'coordinatePrecisionWarning': attributes[row['facilityId']]['coordinatePrecisionWarning']}
                        for distance, row in nearby[:3]]}}


if __name__ == '__main__':
    print(json.dumps(demonstrate(json.loads((ROOT/'catalogue.json').read_text()),
                                json.loads((ROOT/'source_attributes.json').read_text())), indent=2))
