"""All facilities here are synthetic unit fixtures, never a real catalogue."""
import csv
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from facility_router import SERVICES, route_facilities, validate_catalogue
from ingest_facilities import COLUMNS, ingest


def facility(fid='TEST-A', **updates):
    row = dict(facilityId=fid, facilityName='Synthetic test fixture', county='Kilifi',
               countyId=None, subcounty=None, facilityLevel=None, facilityType=None,
               latitude=None, longitude=None, capabilities={s: 'unknown' for s in SERVICES},
               dataSource='synthetic_unit_test_only', dataYear=None,
               capabilityObservedAt=None, capabilityVerifiedAt=None)
    row.update(updates)
    return row


def capable(fid='TEST-A', **updates):
    return facility(fid, capabilities={s: s == 'childHealth' for s in SERVICES}, **updates)


def test_compatible_no_fabrication():
    result = route_facilities([capable()], ['childHealth'])
    assert result['status'] == 'candidates_found'
    item = result['candidates'][0]
    assert item['distanceKm'] is item['estimatedTravelMinutes'] is item['dataYear'] is None
    assert item['availabilityStatus'] == 'unknown'
    assert item['reasons'] and result['requiresVerification']


@pytest.mark.parametrize('value,status', [(False, 'no_compatible_facility'), ('unknown', 'insufficient_data')])
def test_exclusions(value, status):
    row = facility()
    row['capabilities']['childHealth'] = value
    assert route_facilities([row], ['childHealth'])['status'] == status


def test_no_combining_or_relaxing_requirements():
    first, second = capable(), capable('TEST-B')
    second['capabilities'].update(childHealth=False, maternal=True)
    assert not route_facilities([first, second], ['childHealth', 'maternal'])['candidates']


def test_limit_dedup_and_determinism():
    rows = [capable(f'TEST-{i}') for i in reversed(range(5))]
    a = route_facilities(rows + [rows[0]], ['childHealth'])
    assert a == route_facilities(list(reversed(rows)), ['childHealth'])
    assert [r['facilityId'] for r in a['candidates']] == ['TEST-0', 'TEST-1', 'TEST-2']
    assert [r['rank'] for r in a['candidates']] == [1, 2, 3]
    with pytest.raises(ValueError, match='Conflicting duplicate'):
        validate_catalogue([capable(), capable(facilityName='Conflicting fixture')])


def test_distance_and_optional_priority():
    near = capable('TEST-Z', latitude=-3.6, longitude=39.8)
    far = capable('TEST-A', latitude=-3.8, longitude=39.8)
    origin = {'latitude': -3.6, 'longitude': 39.8}
    result = route_facilities([far, near], ['childHealth'], patient_coordinates=origin)
    assert result['candidates'][0]['facilityId'] == 'TEST-Z'
    assert result['candidates'][0]['distanceKm'] == 0
    assert 22 < result['candidates'][1]['distanceKm'] < 23
    far['capabilities']['laboratory'] = True
    result = route_facilities([near, far], ['childHealth'], patient_coordinates=origin, optional_services=['laboratory'])
    assert result['candidates'][0]['facilityId'] == 'TEST-A'


def test_partial_coordinates_do_not_bias_ranking():
    rows = [capable('TEST-Z', latitude=-3.6, longitude=39.8), capable('TEST-A')]
    result = route_facilities(rows, ['childHealth'], patient_coordinates={'latitude': -3.6, 'longitude': 39.8})
    assert result['rankingMethod'] == 'optional_matches_then_id'
    assert result['candidates'][0]['facilityId'] == 'TEST-A'


@pytest.mark.parametrize('updates', [dict(latitude=0), dict(latitude=91, longitude=0),
    dict(latitude=float('nan'), longitude=0), dict(county='Other'), dict(dataYear=True),
    dict(capabilityVerifiedAt='2099-01-01'), dict(capabilities={s: 1 for s in SERVICES})])
def test_invalid_records(updates):
    with pytest.raises(ValueError):
        validate_catalogue([facility(**updates)])


def test_empty_unknown_service_and_subject():
    assert route_facilities([], ['childHealth'])['reasonCodes'] == ['no_facility_data']
    assert not route_facilities([capable()], [])['candidates']
    assert not route_facilities([capable()], ['childHealth'], {'subjectStatus': 'ambiguous'})['candidates']
    with pytest.raises(ValueError):
        route_facilities([capable()], ['invented'])


def write_csv(tmp_path, rows):
    path = tmp_path / 'reviewed.csv'
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def csv_row(**updates):
    row = {k: '' for k in COLUMNS}
    row.update(facilityId='TEST-A', facilityName='Synthetic only', county='Kilifi', dataSource='unit_test')
    row.update(updates)
    return row


def test_ingestion_unknowns_scope_duplicates(tmp_path):
    path = write_csv(tmp_path, [csv_row(), csv_row(), csv_row(facilityId='TEST-B', county='Other')])
    rows, audit = ingest(path)
    assert len(rows) == 1
    assert all(v == 'unknown' for v in rows[0]['capabilities'].values())
    assert rows[0]['latitude'] is rows[0]['capabilityVerifiedAt'] is None
    assert audit['identicalDuplicatesRemoved'] == audit['excludedOutsideScope'] == 1


def test_authoritative_scope_and_conflict(tmp_path):
    path = write_csv(tmp_path, [csv_row(countyId='source-specific-kilifi')])
    assert len(ingest(path, 'source-specific-kilifi')[0]) == 1
    assert not ingest(path, 'different-id')[0]
    path = write_csv(tmp_path, [csv_row(countyId='source-specific-kilifi', county='Other')])
    with pytest.raises(ValueError, match='conflict'):
        ingest(path, 'source-specific-kilifi')


@pytest.mark.parametrize('updates', [dict(childHealth='yes'), dict(latitude='abc'), dict(dataSource='')])
def test_ingestion_rejects_bad_values(tmp_path, updates):
    with pytest.raises(ValueError):
        ingest(write_csv(tmp_path, [csv_row(**updates)]))


def test_empty_catalogue_cli(tmp_path):
    root = Path(__file__).resolve().parents[2]
    empty = tmp_path / 'empty.json'
    empty.write_text('[]')
    proc = subprocess.run([sys.executable, str(root/'ml/src/facility_router.py'),
                           str(root/'ml/data/facilities/example_request.json'),
                           '--catalogue', str(empty)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)['reasonCodes'] == ['no_facility_data']
