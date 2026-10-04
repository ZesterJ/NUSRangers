# Kilifi facility ingestion workspace

## Current real source

The catalogue now contains **209 real source records** from the user-provided
[ArcGIS FeatureServer](https://services3.arcgis.com/kUatCIwPzByJQvIx/ArcGIS/rest/services/Kilifi_Health_WFL1/FeatureServer),
layer 0 `Kilfi_Health_Facilities`. Accessed 2026-10-04. Public ArcGIS item
`f5876f6990e141198c92847f2c780afe`, owner `lamukohe_esrieaproducts`.
This is not established as an official/current Ministry of Health registry.

The item description, attribution and licence fields are empty. Public REST access
worked without authentication; redistribution permission is not established. Raw
responses are retained as requested for provenance; verify terms with the publisher
before redistribution. Source observation year is unknown. ArcGIS upload/edit times
are 2025-11-07 and must not be substituted for observation or verification dates.

Files:

- `raw/arcgis/`: unchanged response bytes for service, layer, item, count, object IDs
  and full records. `manifest.json` records exact request URLs, access date, hashes
  and sizes. Records were requested with `outFields=*`, `outSR=4326`, sorted OBJECTID.
- `catalogue.json`: canonical output, with all six capabilities unknown.
- `source_attributes.json`: ownership codes, legacy administrative fields, source
  IDs, coordinate provenance and nullable bed/staff fields keyed by canonical ID.
- `arcgis_audit.json`: reproducible field counts and limitations.
- `routing_demo.json`: strict routing abstention plus a separate geographic lookup.
- `template.csv`: header-only template for manually reviewed future enrichment.

## Reproduce the ArcGIS ingestion (offline)

```bash
python3 ml/src/ingest_arcgis_facilities.py
python3 ml/src/facility_router.py ml/data/facilities/example_request.json
python3 ml/src/demo_facility_routing.py
```

The adapter verifies raw hashes, expected layer identity, complete count/object-ID
agreement, no transfer truncation, unique GlobalIDs, geography metadata, coordinate
ranges and agreement between coordinate attributes and WGS84 geometry. It rejects
unexpected data rather than silently truncating or guessing. It does not make network
calls. To refresh, retrieve the manifest's read-only URLs into a NEW snapshot folder,
review changes and record new hashes/access dates. If the service exceeds 2,000 rows,
retrieve all pages/object-ID batches before adapting; the current adapter fails on
truncated or count-mismatched responses rather than importing a partial catalogue.
Use `--raw PATH --output-dir PATH` to inspect a separate snapshot without replacing
this one. Check that the source did not change between count, ID and record requests.

## Mapping and geographic limitations

- `GlobalID` → namespaced facilityId including item ID and layer ID. `Facility_N`
  repeats and HMIS has 118 zeros; neither is treated as a current MFL identifier.
- `F_NAME` → facilityName, preserving original naming (including historical names).
- WGS84 query geometry y/x → latitude/longitude. The source storage CRS is Web
  Mercator (102100/3857), so stored x/y must not be interpreted as degrees.
- `Facility_T` → `Facility_T:<code>`; no codebook/domain is supplied. It is NOT KEPH
  level. `Agency` codes remain undecoded in source_attributes.
- County is dataset-scoped Kilifi, supported by legacy KILIFI/MALINDI districts.
  No authoritative county ID or boundary is supplied. Modern subcounty is null;
  District/Division/Sub_Locati are retained without relabelling them as subcounty.
- The metadata contains no service-level or detailed service-capability field.
  All capabilities are unknown; names, type codes and beds never imply services.
- Ten coordinate sources contain ILRI locality references or SUBLOC CENTROID;
  these are flagged as potential proxy locations. All remaining positional accuracy
  is also unverified. There is no road/travel-time or live availability feed.

## Supplementary official record investigation

The production KMHFR page for Kilifi County Hospital #11474 is:
https://kmhfr.health.go.ke/public/facilities/09d5776f-81a0-4bf0-bbbb-77d607803976

Both web retrieval and a direct curl request timed out (40-second curl limit).
A search result for the official **test-host** page
https://kmhfltest.health.go.ke/public/facilities/09d5776f-81a0-4bf0-bbbb-77d607803976
shows a promising record, but it is not promoted to verified production evidence.
No automated scraping or capability enrichment was performed. The search preview
suggests a match to ArcGIS `KILIFI DISTRICT HOSPITAL` at the same coordinate values,
but an explicit reviewed crosswalk is required: ArcGIS HMIS 565 and Facility_N 16
are not MFL code 11474. Keep ArcGIS and MFL IDs in separate namespaces.

A future enrichment must preserve the official record/export, retrieval date,
source service names and statuses, reviewed mapping to canonical capabilities,
per-capability provenance and crosswalk evidence. Listed services establish only a
registry assertion, never current equipment/staff readiness. Operational/opening/bed
fields must remain dated source claims, not live capacity. Missing services are unknown,
not false. See the audit for the current decision not to merge this record.

The earlier World Bank source remains supplementary only:
https://microdata.worldbank.org/catalog/3872/study-description — Kenya SDI Health
2018, harmonized anonymized public-use survey under licence/citation conditions.
No survey data downloaded and no named-facility join established. It is historical,
not live availability. No evidence from it is used in this catalogue.

## Canonical record

All keys are required; nullable fields preserve missingness:

| Key | Type / meaning |
| --- | --- |
| facilityId | Nonblank stable source ID; namespace IDs when mixing registries |
| facilityName | Nonblank source name, never the deduplication key |
| county | `Kilifi`; ArcGIS scope comes from the selected layer and legacy district metadata, not a boundary check |
| countyId | Source-specific authoritative county ID, or null |
| subcounty | String or null |
| facilityLevel | Source level string or null; never a capability proxy |
| facilityType | Source type string or null; ArcGIS codes are explicitly prefixed `Facility_T:` and not decoded |
| latitude, longitude | Finite numeric pair or both null; WGS84 decimal degrees |
| capabilities | All six keys below, each JSON true, false or string `unknown` |
| dataSource | Nonblank source URL/reference identifying the reviewed export |
| dataYear | Source observation year or null, not download year |
| capabilityObservedAt | ISO date YYYY-MM-DD or null |
| capabilityVerifiedAt | Actual review date YYYY-MM-DD or null |

Capability keys: `generalOutpatient`, `childHealth`, `maternal`, `laboratory`,
`imaging`, `emergency`. These are routing vocabulary, not established clinical
service definitions. A reviewer must document the exact registry-service mapping
and scope before entering true/false. Blank means unknown. Omission of a service
from a partial registry list does not justify false. No level-based inference.

Dates at record level describe the whole capability snapshot. If observations have
different dates, leave the shared date null and retain per-service source evidence
in the reviewed export documentation; do not imply a common verification date.

## Ingestion

Copy `template.csv`, map an authorized export into its columns, and retain the
original export plus a source note (URL, dataset/version, access date, licence,
year, geography, field mappings and evidence for every non-unknown capability).
Avoid committing restricted data. The script is a reviewed-CSV adapter, not an
unverified automatic adapter for the live registry.

```bash
python3 ml/src/ingest_facilities.py /path/to/reviewed.csv \
  --county-id SOURCE_SPECIFIC_KILIFI_ID \
  --output /tmp/kilifi_catalogue.json
```

Use the actual source code; the placeholder is not a county identifier. Without
`--county-id`, explicit county-name metadata is used and the audit records this
weaker selection. No facility-name matching. Exact duplicate IDs/records collapse;
conflicting duplicate IDs fail for human reconciliation. Coordinates are checked
for complete pairs, finite values and global ranges only. No county boundary exists
locally: range-valid coordinates are NOT verified Kilifi points. Review outliers
against an authoritative boundary before publishing. No Kilifi-town centre or
catchment radius is invented; all verified county records remain in scope.

The adapter outputs canonical JSON and a sibling `.audit.json` with input SHA256,
counts, duplicate handling and scope method. Missing observations stay null/unknown.

## Router

```bash
python3 ml/src/facility_router.py ml/data/facilities/example_request.json
# Later, use --catalogue /tmp/kilifi_catalogue.json
```

The current real catalogue has 209 records, all with unknown capabilities. Thus the
example returns `insufficient_data` with 209 unknown-capability exclusions.

Request: `requiredServices` array, optional `optionalServices`, `patientContext`
object and `patientCoordinates` object (`latitude`, `longitude`) or null.
Requirements are human-selected. Context is carried as input but only an explicit
`subjectStatus: ambiguous` blocks routing; other clinical context is not interpreted.
This does not implement age eligibility, diagnosis, triage or referral policy.

Every mandatory capability must be true in one facility. False excludes; unknown
never qualifies. No requirements, ambiguous subject, no catalogue or potentially
matching unknown capabilities return `insufficient_data`. If all records are
explicitly incompatible, return `no_compatible_facility`. Up to three candidates.

Ordering: optional true-count descending, then straight-line distance ascending,
then stable ID. No travel-time source exists, so travel-time estimation is not
implemented and always returns null. Distance is used for ranking only if all
compatible facilities and the patient have coordinates; otherwise optional match
and ID determine order, with an explicit explanation. Any calculable distance is
still displayed. No facility level preference. Ranking uses unrounded distances.

Capability is a dated source assertion, not proof of present readiness. The router
always returns availability unknown and requiresVerification true. No live data
adapter or simulated availability exists. Before use, a person must confirm service
scope, opening, staff/equipment availability and suitability. Historical SDI input
must not be mapped to current capability without a separate documented review.

## Source-backed demonstration subset

`verified_capabilities.csv` is a separate 12-facility evidence overlay; the original
209-record catalogue remains unchanged. Ten selected facilities have at least one
source-backed claim; two unresolved matches remain unknown. Historical and indexed
source evidence is explicitly distinguished from current verification.
See `../../reports/verified_capability_audit.md`, `evidence/sources.json` and
`evidence/crosswalk.json` for scope, dates, matching decisions and rejected claims.

```bash
python3 ml/src/verified_facility_demo.py
python3 ml/src/verified_facility_demo.py --patient /path/to/structured-patient.json
```

The patient path uses explicit care-policy rules by default. The learned classifier
remains experimental and is not loaded. Every candidate includes per-capability
provenance. The loader rejects unresolved matches, unknown verification statuses,
duplicate claims and invented negatives. The demonstration uses historical evidence
as historical evidence; it is not an operational referral recommendation.
