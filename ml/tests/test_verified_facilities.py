import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from verified_facility_demo import ROOT, load_subset, examples, assess_and_route
from facility_router import route_facilities


def test_coverage_provenance_and_canonical_unchanged():
    before = hashlib.sha256((ROOT/'catalogue.json').read_bytes()).hexdigest()
    rows, evidence = load_subset()
    assert len(rows) == 12 and len(evidence) == 36
    assert sum(any(v is True for v in r['capabilities'].values()) for r in rows) == 10
    assert sum(r['value'] == 'true' for r in evidence) == 19
    assert not any(r['value'] == 'false' for r in evidence)
    for service, count in [('generalOutpatient',10),('childHealth',3),('maternal',6)]:
        assert sum(r['capabilities'][service] is True for r in rows) == count
    assert hashlib.sha256((ROOT/'catalogue.json').read_bytes()).hexdigest() == before
    assert all(v == 'unknown' for r in json.loads((ROOT/'catalogue.json').read_text()) for v in r['capabilities'].values())


def test_demo_reproducible_and_no_match():
    result = examples()
    assert result == json.loads((ROOT/'verified_routing_examples.json').read_text())
    for service in ('generalOutpatient','childHealth','maternal'):
        candidates = result[service]['candidates']
        assert len(candidates) == 3
        assert [c['distanceKm'] for c in candidates] == sorted(c['distanceKm'] for c in candidates)
        for candidate in candidates:
            assert candidate['capabilityEvidence']
            assert all(r['value'] == 'true' and r['source'].startswith('https://') for r in candidate['capabilityEvidence'])
            assert candidate['availabilityStatus'] == 'unknown'
            assert candidate['estimatedTravelMinutes'] is None
    missing = result['noConfirmedCompatibleFacility']
    assert missing['status'] == 'insufficient_data' and not missing['candidates']
    assert missing['excluded']['unknownCapability'] == 12
    assert len(result['unknownCapabilityExclusion']['candidates']) == 2


def test_rules_default_and_abstention():
    patient = {'patientType':'child', 'symptoms':['fever'], 'hydrationIssue':None,
               'subject':{'status':'resolved'}, 'abstentions':[], 'reportedSigns':[],
               'reportedSignStates':{s:{'state':'not_mentioned'} for s in ('cannot_drink','convulsions','bleeding')}}
    result = assess_and_route(patient)
    assert result['careAssessment']['generator'] == 'care-policy-v1-rules'
    assert result['careAssessment']['requiredServices'] == ['generalOutpatient','childHealth']
    patient['subject']['status'] = 'ambiguous'
    result = assess_and_route(patient)
    assert result['careAssessment']['status'] == 'unclear' and not result['routing']['candidates']


@pytest.mark.parametrize('change', ['unverified','id','name','source','false','duplicate','missing'])
def test_reject_corrupt_evidence(tmp_path, change):
    for filename in ('catalogue.json','verified_capabilities.csv'):
        shutil.copy(ROOT/filename,tmp_path/filename)
    shutil.copytree(ROOT/'evidence',tmp_path/'evidence')
    path = tmp_path/'verified_capabilities.csv'
    with path.open(newline='') as f: rows=list(csv.DictReader(f))
    if change=='unverified': rows[0]['verificationStatus']='guessed'
    if change=='id': rows[0]['facilityId']='made-up'
    if change=='name': rows[0]['facilityName']='other'
    if change=='source': rows[0]['source']='https://unverified.example'
    if change=='false': rows[0]['value']='false'
    if change=='duplicate': rows.append(rows[0])
    if change=='missing': rows.pop()
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    with pytest.raises(ValueError): load_subset(tmp_path)


def test_explicit_incompatible_branch_synthetic_only():
    rows,_ = load_subset()
    synthetic = dict(rows[0], facilityId='SYNTHETIC-NEGATIVE-UNIT-TEST',
                     facilityName='Synthetic negative fixture', dataSource='synthetic unit test only',
                     capabilities={s:False for s in rows[0]['capabilities']})
    result=route_facilities([synthetic],['maternal'])
    assert result['status']=='no_compatible_facility' and not result['candidates']
