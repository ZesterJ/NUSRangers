"""Offline, fail-closed adapter for the preserved Kilifi ArcGIS layer-0 snapshot."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from uuid import UUID

from facility_router import SERVICES, coordinates, validate_catalogue

BASE = 'https://services3.arcgis.com/kUatCIwPzByJQvIx/ArcGIS/rest/services/Kilifi_Health_WFL1/FeatureServer'
ITEM = 'f5876f6990e141198c92847f2c780afe'
ROOT = Path(__file__).resolve().parents[1] / 'data/facilities'


def convert(layer, records, count, ids):
    """No type-code decoding, county boundary assertion or clinical enrichment."""
    for response in (layer, records, count, ids):
        if 'error' in response:
            raise ValueError('ArcGIS error response, not a dataset')
    if layer.get('id') != 0 or layer.get('serviceItemId') != ITEM:
        raise ValueError('Unexpected ArcGIS layer identity')
    if layer.get('name') != 'Kilfi_Health_Facilities' or records.get('geometryType') != 'esriGeometryPoint':
        raise ValueError('Unexpected layer or geometry type')
    if records.get('spatialReference', {}).get('wkid') != 4326:
        raise ValueError('Query must request outSR=4326')
    if records.get('exceededTransferLimit'):
        raise ValueError('Truncated query: retrieve a complete snapshot before ingestion')
    features = records['features']
    expected = ids['objectIds']
    actual = [f['attributes']['OBJECTID'] for f in features]
    if len(actual) != count['count'] or len(set(actual)) != len(actual) or len(set(expected)) != len(expected) or set(actual) != set(expected):
        raise ValueError('Record count/object-ID mismatch or duplicates')
    catalogue, supplemental = [], []
    seen = set()
    for feature in features:
        a = feature['attributes']
        # Source geographic scope only: legacy districts are not modern subcounties.
        if a.get('Province') != 'COAST' or a.get('District') not in ('KILIFI', 'MALINDI'):
            raise ValueError('Unexpected geographic scope; review before inclusion')
        gid = str(UUID(a['GlobalID']))
        if gid in seen:
            raise ValueError('Duplicate GlobalID')
        seen.add(gid)
        fid = f'arcgis:{ITEM}:0:{gid}'
        g = feature.get('geometry') or {}
        point = coordinates(g.get('y'), g.get('x'))
        if point is None:
            raise ValueError('Missing geometry; review source snapshot')
        original = coordinates(a.get('Latitude'), a.get('Longitude'))
        if original is None or max(abs(x-y) for x, y in zip(point, original)) > 1e-5:
            raise ValueError('Attribute/geometry coordinate discrepancy; review required')
        code = a.get('Facility_T')
        if code is not None and (type(code) not in (int, float) or int(code) != code):
            raise ValueError('Unexpected facility type code')
        row = dict(facilityId=fid, facilityName=a['F_NAME'].strip(), county='Kilifi',
                   countyId=None, subcounty=None, facilityLevel=None,
                   facilityType=f'Facility_T:{int(code)}' if code is not None else None,
                   latitude=point[0], longitude=point[1],
                   capabilities={s: 'unknown' for s in SERVICES},
                   dataSource=BASE + '/0', dataYear=None,
                   capabilityObservedAt=None, capabilityVerifiedAt=None)
        catalogue.append(row)
        supplemental.append({
            'facilityId': fid, 'objectId': a['OBJECTID'], 'globalId': gid,
            'sourceFacilityNumber': a.get('Facility_N'), 'sourceHMIS': a.get('HMIS'),
            'ownershipCode': a.get('Agency'), 'facilityTypeCode': code,
            'province': a.get('Province'), 'legacyDistrict': a.get('District'),
            'legacyDivision': a.get('Division'), 'location': a.get('LOCATION'),
            'subLocation': a.get('Sub_Locati'), 'coordinateSource': a.get('Spatial_Re'),
            'coordinatePrecisionWarning': 'proxy_location_source' if any(
                token in (a.get('Spatial_Re') or '') for token in ('ILRI', 'CENTROID')) else 'accuracy_unverified',
            'sourceBedCapacity': a.get('Bed_Capacity'), 'sourceDoctorCount': a.get('No_of_doctors'),
            'sourceNurseCount': a.get('No_of_nurses'),
            'sourceCreationTimestamp': a.get('CreationDate'), 'sourceEditTimestamp': a.get('EditDate'),
            'countyScopeBasis': 'user-selected Kilifi layer plus legacy KILIFI/MALINDI districts; no boundary verification',
            'availabilityStatus': 'unknown'})
    catalogue = sorted(validate_catalogue(catalogue), key=lambda r: r['facilityId'])
    supplemental.sort(key=lambda r: r['facilityId'])
    audit = {
        'sourceRecords': len(features), 'canonicalFacilities': len(catalogue),
        'completeness': 'count and complete object-ID set match; transfer limit not exceeded',
        'countyScope': 'dataset-scoped; not independently boundary-verified',
        'facilityTypeCodeCounts': dict(Counter(str(a['attributes'].get('Facility_T')) for a in features)),
        'ownershipCodeCounts': dict(Counter(a['attributes'].get('Agency') for a in features)),
        'legacyDistrictCounts': dict(Counter(a['attributes'].get('District') for a in features)),
        'canonicalNonNullCounts': {k: sum(r[k] is not None for r in catalogue) for k in catalogue[0]} if catalogue else {},
        'capabilities': {s: dict(Counter(r['capabilities'][s] for r in catalogue)) for s in SERVICES},
        'proxyCoordinateCount': sum(r['coordinatePrecisionWarning'] == 'proxy_location_source' for r in supplemental),
        'allCoordinates': 'WGS84 query geometry, range checked and agrees with attributes within 1e-5 degrees',
        'dataYear': None, 'licence': 'Not specified in item licenseInfo or layer copyrightText',
    }
    return catalogue, supplemental, audit


def load_snapshot(raw):
    manifest = json.loads((raw / 'manifest.json').read_text())
    for name in ('service.json', 'layer.json', 'item.json', 'count.json', 'ids.json', 'records.json'):
        if hashlib.sha256((raw/name).read_bytes()).hexdigest() != manifest['files'][name]['sha256']:
            raise ValueError(f'Snapshot hash mismatch: {name}')
    return convert(*(json.loads((raw/name).read_text()) for name in ('layer.json', 'records.json', 'count.json', 'ids.json')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=ROOT/'raw/arcgis')
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        catalogue, supplemental, audit = load_snapshot(args.raw)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, data in [('catalogue.json', catalogue), ('source_attributes.json', supplemental), ('arcgis_audit.json', audit)]:
            (args.output_dir/name).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f'ArcGIS ingestion failed: {exc}\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
