"""Derived scenario-family split. Original records/splits remain unchanged.

Family proxy: patient_type + sorted symptoms + sorted danger_signs + hydration_issue
+ notes. Excludes duration and language to group cross-language paraphrases and onset
variants. This deliberately coarse proxy uses annotation metadata ONLY for grouping,
never as input features. It is not a recovered generator ID. Shared phrases can remain.
"""
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 42
LABELS = ('abdominal_pain', 'bleeding', 'blurred_vision', 'breathing_difficulty', 'cough',
          'diarrhoea', 'fatigue', 'fever', 'fluid_loss', 'headache', 'reduced_fetal_movement',
          'vomiting', 'weakness')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def family_key(row):
    labels = row['labels']
    return digest({k: sorted(labels[k]) if isinstance(labels[k], list) else labels[k]
                   for k in ('patient_type', 'symptoms', 'danger_signs', 'hydration_issue', 'notes')})[:16]


def prepare():
    manifest = json.loads((ROOT / 'data/raw/manifest.json').read_text())
    for item in manifest['files']:
        path = ROOT / 'data/raw' / Path(item['path']).name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
    rows = sorted([json.loads(s) for s in (ROOT / 'data/raw/health_triage_ie_synthetic_v1.jsonl').read_text().splitlines()], key=lambda r: r['id'])
    groups = defaultdict(list)
    for row in rows:
        groups[family_key(row)].append(row)
    # Annotation vocabulary predeclared from the prior audit, not fitted to held-out text.
    keys = sorted(groups)
    random.Random(SEED).shuffle(keys)
    n = len(keys)
    split = {g: ('train' if i < int(.6*n) else 'validation' if i < int(.8*n) else 'test')
             for i, g in enumerate(keys)}
    # Coverage constraint specified before model fitting: all 13 labels must be learnable.
    # Move complete families, never individual rows. No metric-driven seed search.
    moves = []
    for label in LABELS:
        if not any(label in r['labels']['symptoms'] for g in keys if split[g] == 'train' for r in groups[g]):
            g = next(g for g in keys if label in groups[g][0]['labels']['symptoms'])
            moves.append({'family': g, 'from': split[g], 'to': 'train', 'reason': f'training coverage for {label}'})
            split[g] = 'train'
    records = [{'id': r['id'], 'originalSplit': r['split'], 'derivedSplit': split[family_key(r)],
                'family': family_key(r)} for r in rows]
    by_id = {r['id']: r for r in rows}
    for key_function in (lambda r: r['text'], lambda r: tuple(sorted(s.strip().lower() for s in r['text'].split('.') if s.strip()))):
        seen = defaultdict(set)
        for record in records:
            seen[key_function(by_id[record['id']])].add(record['derivedSplit'])
        assert all(len(v) == 1 for v in seen.values()), 'Duplicate leakage across derived splits'
    parts = {s: [by_id[r['id']] for r in records if r['derivedSplit'] == s] for s in ('train', 'validation', 'test')}
    assert all(parts.values())
    info = {'seed': SEED, 'method': __doc__, 'family_count': n, 'coverage_moves': moves,
            'rows_per_split': {s: len(rs) for s, rs in parts.items()},
            'families_per_split': dict(Counter(split.values())),
            'language_counts': {s: dict(Counter(r['language'] for r in rs)) for s, rs in parts.items()},
            'label_support': {s: {label: sum(label in r['labels']['symptoms'] for r in rs) for label in LABELS} for s, rs in parts.items()},
            'original_split_counts_by_derived': {s: dict(Counter(r['split'] for r in rs)) for s, rs in parts.items()},
            'record_manifest_sha256': digest(records), 'exact_and_sentence_bag_overlap': 0,
            'family_overlap': 0}
    # Report residual sentence reuse, rather than claiming complete template independence.
    def fragments(rs):
        return {s.strip().lower() for r in rs for s in r['text'].split('.') if s.strip()}
    train_fragments = fragments(parts['train'])
    info['heldout_sentence_fragment_overlap_fraction'] = {
        s: len(fragments(parts[s]) & train_fragments) / len(fragments(parts[s])) for s in ('validation', 'test')}
    target = ROOT / 'data/processed'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'baseline_split_manifest.json').write_text(json.dumps({'summary': info, 'records': records}, indent=2) + '\n')
    return parts, info


if __name__ == '__main__':
    _, info = prepare()
    print(json.dumps(info, indent=2))
