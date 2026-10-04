"""Offline tests against preserved source bytes; no APIs or clinical inferences."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ingest_arcgis_facilities import ROOT, convert, load_snapshot
from facility_router import SERVICES, route_facilities
from demo_facility_routing import demonstrate


@pytest.fixture
def snapshot():
    return [json.loads((ROOT/'raw/arcgis'/name).read_text())
            for name in ('layer.json', 'records.json', 'count.json', 'ids.json')]


def test_real_snapshot_reproducible_and_no_inference():
    rows, extra, audit = load_snapshot(ROOT/'raw/arcgis')
    assert len(rows) == len(extra) == 209
    assert rows == json.loads((ROOT/'catalogue.json').read_text())
    assert extra == json.loads((ROOT/'source_attributes.json').read_text())
    assert audit == json.loads((ROOT/'arcgis_audit.json').read_text())
    assert len({r['facilityId'] for r in rows}) == 209
    for row in rows:
        assert all(row['capabilities'][s] == 'unknown' for s in SERVICES)
        assert row['dataYear'] is row['facilityLevel'] is row['countyId'] is row['subcounty'] is None
        assert row['capabilityObservedAt'] is row['capabilityVerifiedAt'] is None
        assert row['facilityType'].startswith('Facility_T:')
        assert row['latitude'] < 0 and row['longitude'] > 0
    assert audit['proxyCoordinateCount'] == 10
    for service in SERVICES:
        result = route_facilities(rows, [service])
        assert result['status'] == 'insufficient_data'
        assert result['excluded']['unknownCapability'] == 209
        assert result['candidates'] == []


@pytest.mark.parametrize('case', ['truncated', 'count', 'ids', 'sr', 'geometry', 'scope', 'duplicate', 'error'])
def test_fail_closed(snapshot, case):
    layer, records, count, ids = snapshot
    if case == 'truncated': records['exceededTransferLimit'] = True
    if case == 'count': count['count'] += 1
    if case == 'ids': ids['objectIds'][0] = 999999
    if case == 'sr': records['spatialReference']['wkid'] = 3857
    if case == 'geometry': records['features'][0]['geometry']['x'] += 1
    if case == 'scope': records['features'][0]['attributes']['District'] = 'OTHER'
    if case == 'duplicate': records['features'][1]['attributes']['GlobalID'] = records['features'][0]['attributes']['GlobalID']
    if case == 'error': records['error'] = {'code': 400}
    with pytest.raises(ValueError):
        convert(layer, records, count, ids)


def test_no_capabilities_from_type_name_beds_or_staff(snapshot):
    snapshot[1]['features'][0]['attributes'].update(F_NAME='Hospital with laboratory', Facility_T=1,
                                                   Bed_Capacity=100, No_of_doctors=40)
    rows, _, _ = convert(*snapshot)
    assert all(v == 'unknown' for r in rows for v in r['capabilities'].values())


def test_hash_tampering_rejected(tmp_path):
    raw = ROOT/'raw/arcgis'
    for path in raw.iterdir():
        if path.is_file(): (tmp_path/path.name).write_bytes(path.read_bytes())
    with (tmp_path/'records.json').open('a') as f: f.write(' ')
    with pytest.raises(ValueError, match='hash mismatch'):
        load_snapshot(tmp_path)


def test_geographic_demo_is_not_service_recommendation():
    rows, extra, _ = load_snapshot(ROOT/'raw/arcgis')
    result = demonstrate(rows, extra)
    assert result == demonstrate(list(reversed(rows)), list(reversed(extra)))
    assert not result['serviceRouting']['candidates']
    entries = result['geographicDirectory']['entries']
    assert len(entries) == 3
    assert [e['distanceKm'] for e in entries] == sorted(e['distanceKm'] for e in entries)
    assert all(e['estimatedTravelMinutes'] is None and e['serviceCompatibility'] == 'unknown' for e in entries)
    assert result == json.loads((ROOT/'routing_demo.json').read_text())
