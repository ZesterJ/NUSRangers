"""Reproducible, standard-library-only audit. Does not alter data or train models.

Run from any directory: python3 /path/to/ml/src/analyze_data.py
Sentence-bag groups are leakage diagnostics, not verified generator template IDs.
"""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical_labels(row):
    return json.dumps({k: sorted(v) if isinstance(v, list) else v
                       for k, v in row['labels'].items()}, sort_keys=True)


def sentences(text):
    return [s.strip().lower() for s in re.split(r'[.!?]+', text) if s.strip()]


def audit():
    raw = ROOT / 'data/raw'
    manifest = json.loads((raw / 'manifest.json').read_text())
    for item in manifest['files']:
        path = raw / Path(item['path']).name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
    rows = [json.loads(line) for line in (raw / 'health_triage_ie_synthetic_v1.jsonl').read_text().splitlines()]
    with (raw / 'health_triage_ie_synthetic_v1.csv').open(newline='') as handle:
        csv_rows = list(csv.DictReader(handle))
    converted = []
    for row in csv_rows:
        converted.append({k: row[k] for k in ('id', 'language', 'text', 'split', 'data_source')} | {
            'labels': {'patient_type': row['patient_type'], 'symptoms': json.loads(row['symptoms']),
                       'duration_days': int(row['duration_days']) if row['duration_days'] else None,
                       'hydration_issue': json.loads(row['hydration_issue']),
                       'danger_signs': json.loads(row['danger_signs']), 'notes': row['notes'] or None}})
    assert converted == rows, 'CSV and JSONL differ'
    fields = tuple(rows[0]['labels'])
    def distribution(subset):
        return {field: dict(sorted(Counter(
            json.dumps(value, ensure_ascii=False) for row in subset
            for value in (row['labels'][field] if isinstance(row['labels'][field], list)
                          else [row['labels'][field]])).items())) for field in fields}
    def groups(key):
        result = defaultdict(list)
        for row in rows:
            result[key(row)].append(row)
        return result
    text_groups = groups(lambda r: r['text'])
    bag_groups = groups(lambda r: tuple(sorted(sentences(r['text']))))
    overlap = {}
    for name, grouped in [('exact_text', text_groups), ('sentence_bag', bag_groups)]:
        cross = [g for g in grouped.values() if len({r['split'] for r in g}) > 1]
        train_keys = {key for key, group in grouped.items() if any(r['split'] == 'train' for r in group)}
        overlap[name] = {
            'unique_groups': len(grouped), 'duplicate_excess_rows': len(rows) - len(grouped),
            'cross_split_groups': len(cross), 'rows_in_cross_split_groups': sum(map(len, cross)),
            'heldout_rows_also_in_train': {split: sum(r['split'] == split for key in train_keys
                                                     for r in grouped[key]) for split in ('validation', 'test')},
            'conflicting_label_groups': sum(len({canonical_labels(r) for r in g}) > 1 for g in grouped.values()),
            'cross_split_examples': [[{'id': r['id'], 'split': r['split'], 'text': r['text']} for r in g]
                                     for g in cross[:3]],
        }
    train_sentences = {s for r in rows if r['split'] == 'train' for s in sentences(r['text'])}
    result = {
        'rows': len(rows), 'csv_rows': len(csv_rows), 'exports_equal': True,
        'jsonl_keys': list(rows[0]), 'csv_columns': list(csv_rows[0]),
        'duplicate_ids': len(rows) - len({r['id'] for r in rows}),
        'languages': dict(Counter(r['language'] for r in rows)),
        'sources': dict(Counter(r['data_source'] for r in rows)),
        'splits': dict(Counter(r['split'] for r in rows)),
        'split_language_counts': {s: dict(Counter(r['language'] for r in rows if r['split'] == s))
                                  for s in ('train', 'validation', 'test')},
        'label_distributions': distribution(rows),
        'labels_by_split': {s: distribution([r for r in rows if r['split'] == s])
                           for s in ('train', 'validation', 'test')},
        'labels_by_language': {s: distribution([r for r in rows if r['language'] == s]) for s in ('en', 'sw')},
        'missing_top_level': {k: sum(r.get(k) is None or r.get(k) == '' for r in rows) for k in rows[0]},
        'null_labels': {k: sum(r['labels'].get(k) is None for r in rows) for k in fields},
        'empty_label_arrays': {k: sum(r['labels'][k] == [] for r in rows) for k in ('symptoms', 'danger_signs')},
        'overlap': overlap,
        'unique_sentence_fragments': len({s for r in rows for s in sentences(r['text'])}),
        'heldout_all_sentences_seen_in_train': {
            split: sum(all(s in train_sentences for s in sentences(r['text'])) for r in rows if r['split'] == split)
            for split in ('validation', 'test')},
        'symptom_combinations': dict(Counter('|'.join(sorted(r['labels']['symptoms'])) for r in rows)),
        'sw_rows_with_english_note_verbatim': sum(r['language'] == 'sw' and r['labels']['notes'] is not None
            and r['labels']['notes'] in r['text'] for r in rows),
        'yesterday_mentions_by_duration_label': dict(Counter(str(r['labels']['duration_days']) for r in rows
            if 'since yesterday' in r['text'] or 'tangu jana' in r['text'])),
        'text_length_characters': {'min': min(len(r['text']) for r in rows),
                                   'max': max(len(r['text']) for r in rows),
                                   'mean': round(sum(len(r['text']) for r in rows) / len(rows), 2)},
    }
    return result


if __name__ == '__main__':
    result = audit()
    target = ROOT / 'reports/data_audit.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(f'Audited {result["rows"]} examples; equivalent CSV/JSONL; hashes verified. Report: {target}')
