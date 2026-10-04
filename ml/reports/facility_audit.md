# Kilifi ArcGIS ingestion audit — 2026-10-04

## Outcome

**209 facility records ingested**, replacing the empty catalogue. The real ArcGIS
snapshot supports identity and geographic directory lookup. It does **not** establish
mandatory care-service compatibility; all six capabilities remain unknown for every
record. The existing strict router therefore correctly returns insufficient data.

No classifier training, care labels, extraction changes, frontend changes, speech
changes or backend `/predict` changes were made. The original router's mandatory
filtering is unchanged. A separate geographic demonstration does not weaken it.

## Source and acquisition

Dataset: `Kilifi Health_WFL1`, layer 0 `Kilfi_Health_Facilities`.

- [Service metadata](https://services3.arcgis.com/kUatCIwPzByJQvIx/ArcGIS/rest/services/Kilifi_Health_WFL1/FeatureServer?f=pjson)
- [Layer schema](https://services3.arcgis.com/kUatCIwPzByJQvIx/ArcGIS/rest/services/Kilifi_Health_WFL1/FeatureServer/0?f=pjson)
- [Item metadata](https://www.arcgis.com/sharing/rest/content/items/f5876f6990e141198c92847f2c780afe?f=pjson)

Access date: 2026-10-04. Public read-only requests, no token required. Publisher account:
`lamukohe_esrieaproducts`. Official Ministry provenance is not established. Empty
item licenseInfo/accessInformation/description and layer copyrightText: no explicit
licence or original collection-year documentation. Do not equate public access with
permission to redistribute. Retained original bytes per user request; establish terms
before publishing the source snapshot.

The network sandbox initially failed DNS. Approved direct curl access succeeded for
ArcGIS. Six original JSON responses, exact URLs, byte counts and SHA256 hashes are
preserved in [raw/arcgis](../data/facilities/raw/arcgis/manifest.json). The query returned
209 records; count=209 and the complete returned object-ID set agree. No transfer-limit
flag was raised; layer limit is 2,000. Offline ingestion verifies hashes and completeness.

ArcGIS record creation/edit timestamp is 2025-11-07, apparently an upload/edit batch.
It is NOT the health-facility observation year. `dataYear`, capabilityObservedAt and
capabilityVerifiedAt remain null. Current operation or completeness of the county's
facility network is not established.

## Fields and actual coverage

| Source field | Findings / canonical use |
| --- | --- |
| OBJECTID | 209 unique feature IDs, retained in sidecar |
| GlobalID | 209 unique IDs; canonical ID uses item/layer/GlobalID namespace |
| F_NAME | 209 nonempty, distinct source names |
| Facility_N | Only 132 distinct values, 17 zeros; not a unique facility identifier |
| HMIS | 118 zeros; not assumed to be current MFL code |
| Facility_T | Numeric type codes, no coded-value domain; preserved as `Facility_T:<code>` |
| Agency | Ownership/agency codes preserved verbatim; no supplied decoding guide |
| Province | COAST for all 209 |
| District | KILIFI 120, MALINDI 89; legacy district, not modern subcounty |
| Division, LOCATION, Sub_Locati | Legacy locality fields retained in sidecar |
| Spatial_Re | Coordinate source labels; useful for accuracy warnings |
| Latitude, Longitude | Present in all 209; consistent with WGS84 query geometry |
| Bed_Capacity | Null in all 209 |
| No_of_doctors, No_of_nurses | Null in all 209 |
| CreationDate, EditDate, Creator, Editor | ArcGIS management metadata, not clinical verification |

Full facility names and records: [catalogue.json](../data/facilities/catalogue.json).
All source fields: [original query](../data/facilities/raw/arcgis/records.json).
Additional attributes: [source_attributes.json](../data/facilities/source_attributes.json).

Examples of names: ADC GALANA RANCH DISP, ADU DISP, KILIFI DISTRICT HOSPITAL,
KILIFI MEDICAL SERVICES (DR PESHU), KILIFI PLANTATION DISP. Names are not interpreted
as evidence of services, current type, or current operation.

Type code distribution: 1=5, 3=12, 4=56, 5=3, 6=123, 7=7, 9=3.
These codes are not facility levels; no KEPH/service-level field is present.
Agency distribution: PRIV=142, MOH=46, MISS=18, LA=1, AF=1, OTHER MIN=1.
No ownership category expansion is asserted without a codebook.

Canonical ID/name/county/type-code/latitude/longitude/source are populated for 209.
Canonical countyId, modern subcounty, facilityLevel, dataYear and both capability dates
are null for all 209. All 1,254 capability values (209 × six) are `unknown`:
generalOutpatient, childHealth, maternal, laboratory, imaging and emergency.
No false values are invented from missing data. No true values are inferred from type.

## Geographic validation and scope

The selected dataset supplies Kilifi scope. Legacy district records include both
KILIFI and MALINDI; filtering only District=KILIFI would wrongly discard 89 source
records. No authoritative current county ID/boundary is available. County attribution
is dataset-based, not an independently verified point-in-polygon claim.

Geometry was requested in EPSG:4326 from storage CRS 102100/3857. All coordinates
pass global range checks and match latitude/longitude attributes within 4.46e-10
degrees. Extent: latitude -3.962407 to -2.685982, longitude 39.330267 to 40.180000.
This is a consistency check, not ground-truth location validation.

Ten records have possible proxy coordinate sources: two SUBLOC CENTROID and eight
ILRI village/market/town references. Sidecar records flag these; other coordinates
remain accuracy-unverified. Two latitude values and two longitude values repeat;
coordinate similarity is not used to merge distinct GlobalIDs. No road access,
travel time, opening hours or live availability is supplied.

## KMHFR supplementary evidence

Investigated [production record #11474](https://kmhfr.health.go.ke/public/facilities/09d5776f-81a0-4bf0-bbbb-77d607803976).
Web and direct curl timed out. A search-index preview for the corresponding
[Ministry test host](https://kmhfltest.health.go.ke/public/facilities/09d5776f-81a0-4bf0-bbbb-77d607803976)
shows level, services and status information, but no retrievable production snapshot
was obtained. No preview text is used as canonical capability evidence.

ArcGIS KILIFI DISTRICT HOSPITAL has coordinates -3.63205, 39.85722, consistent with
the indexed record. It remains a proposed crosswalk, not an automatic ID match:
its HMIS is 565 and Facility_N is 16, not MFL 11474. A reviewer must establish identity
using the official ID plus location/name history, preserve the official evidence,
and approve each service mapping before enrichment. Opening and operational claims
would remain dated registry observations, not proof of live readiness.

## Routing demonstration

Command: `python3 ml/src/demo_facility_routing.py`

The anchor is the ArcGIS KILIFI DISTRICT HOSPITAL coordinate, not a real patient and
not an invented Kilifi town centre. A required `childHealth` request returns:

```json
{
  "status": "insufficient_data",
  "candidates": [],
  "requiresVerification": true,
  "rankingMethod": null,
  "availabilityStatus": "unknown",
  "reasonCodes": ["mandatory_capabilities_not_confirmed"],
  "excluded": {"incompatible": 0, "unknownCapability": 209}
}
```

Separately, the directory demo uses only source coordinates to list nearby records,
excluding the anchor itself:

| Source name | Straight-line distance |
| --- | ---: |
| SEASIDE MED CENTRE | 0.455 km |
| MSENANGU NURSING  & MATERNITY HOME LTD | 0.559 km |
| MISSION UNION MED CLINIC | 0.656 km |

These are geographic neighbours, **not confirmed care candidates**. Their service
compatibility and availability remain unknown; travel minutes remain null. Distance
is a calculation on source points, not a statement about actual access or position
accuracy. Complete output: [routing_demo.json](../data/facilities/routing_demo.json).

## Next data needed

Obtain the type/ownership codebook, collection date, licence, authoritative county
boundary, current MFL crosswalk and dated per-service evidence. Confirm individual
locations and facility operation before operational use. After service definitions
and capability coverage are reviewed, create independently reviewed patient-to-service
labels and grouped evaluation splits. No such labels or classifier were created.
