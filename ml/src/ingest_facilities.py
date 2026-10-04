"""Ingest a manually mapped, source-reviewed CSV. No guessed source service mappings."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from facility_router import FIELDS, SERVICES, validate_catalogue

COLUMNS = [key for key in FIELDS if key != 'capabilities'] + list(SERVICES)


def ingest(path, county_id=None):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or set(reader.fieldnames) != set(COLUMNS) or len(reader.fieldnames) != len(COLUMNS):
            raise ValueError('CSV header must match template.csv exactly (order may differ)')
        rows, excluded = [], 0
        for line, raw in enumerate(reader, 2):
            if None in raw or any(v is None for v in raw.values()):
                raise ValueError(f'Malformed CSV row {line}')
            raw = {key: value.strip() for key, value in raw.items()}
            # An authoritative ID takes priority when its source-specific value is supplied.
            # Name fallback is explicit county metadata, never a facility-name heuristic.
            if county_id is not None:
                if raw['countyId'] != county_id:
                    excluded += 1
                    continue
                if raw['county'].casefold() != 'kilifi':
                    raise ValueError(f'County ID/name conflict at row {line}')
            elif raw['county'].casefold() != 'kilifi':
                excluded += 1
                continue
            row = {key: raw[key] or None for key in FIELDS if key != 'capabilities'}
            row['county'] = 'Kilifi'
            row['capabilities'] = {}
            for service in SERVICES:
                value = raw[service].lower()
                if value not in ('', 'unknown', 'true', 'false'):
                    raise ValueError(f'Invalid {service} at row {line}: use true/false/unknown')
                row['capabilities'][service] = {'true': True, 'false': False}.get(value, 'unknown')
            for key in ('latitude', 'longitude'):
                row[key] = float(row[key]) if row[key] is not None else None
            row['dataYear'] = int(row['dataYear']) if row['dataYear'] is not None else None
            rows.append(row)
    catalogue = sorted(validate_catalogue(rows), key=lambda row: row['facilityId'])
    return catalogue, {'inputSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                       'kilifiFacilities': len(catalogue), 'excludedOutsideScope': excluded,
                       'identicalDuplicatesRemoved': len(rows) - len(catalogue),
                       'countySelection': 'authoritative_id_and_name' if county_id is not None else 'explicit_county_name',
                       'coordinateValidation': 'global ranges and complete pairs only; no county boundary available'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--county-id', help='Exact authoritative Kilifi ID from the source; do not guess its code system')
    args = parser.parse_args()
    try:
        rows, audit = ingest(args.csv, args.county_id)
        args.output.write_text(json.dumps(rows, indent=2, allow_nan=False) + '\n')
        args.output.with_suffix('.audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Ingestion failed: {exc}\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
