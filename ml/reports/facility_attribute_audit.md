# Kilifi facility attribute audit

Inspected the preserved 209-record ArcGIS layer-0 response and its field metadata.
No capability inference or canonical-data changes. Counts describe this snapshot,
not the current complete Kilifi facility network.

## Names and types

`F_NAME`: **209 populated records, 209 distinct exact names, each occurring once**.
The complete unique-value/count/type inventory is in
[facility_name_type_inventory.csv](facility_name_type_inventory.csv).
Names include historical labels and abbreviations; they are not verified service lists.

`Facility_T`: **209 populated records, seven distinct numeric codes**:

| Raw code | Count | Example source names |
| --- | ---: | --- |
| 1 | 5 | GALANA HOSPITAL; KILIFI DISTRICT HOSPITAL |
| 3 | 12 | JILORE HEALTH CENTRE; MBOGO HC |
| 4 | 56 | ADU DISP; MALANGA SDA DISPENSARY |
| 5 | 3 | NEW MWENA MED HOSP; NEW SAVANNA HOSP; STAR HOSPITAL |
| 6 | 123 | KAREMA MED CLINIC; JAMBO CLINIC & LABORATORY |
| 7 | 7 | BAHARI MUSLIM NURSING HOME; NEW WANANCHI NURS & MAT HOME |
| 9 | 3 | KILIFI PLANTATION DISP; MARIAKANI BARRACKS HOSPITAL; GK PRISON DISP(MALINDI) |

**No codebook is present in the preserved metadata or ingestion workspace.** All
22 field domains are null, layer `types` is empty, and item description/documentation
provide no decoding. Facility_T's alias is “Facility Type”, not facility level.
Examples above must not be used to assign a meaning to an entire code. In particular,
code 9 includes both DISP and HOSPITAL names; MTWAPA FAMILY HEALTH CENTRE has code 6.
Canonical types remain explicitly undecoded `Facility_T:<code>` values.

## Literal name patterns

Case-insensitive whole-word matching, counted once per record per pattern. These
are overlapping textual observations, not inferred types or capabilities.

| Name token/pattern | Records | Example |
| --- | ---: | --- |
| HOSPITAL or HOSP | 9 | NEW SAVANNA HOSP |
| DISPENSARY or DISP | 58 | ADU DISP |
| HEALTH CENTRE or HC | 12 | MBOGO HC |
| H C (separate abbreviation) | 1 | KIZINGO H C |
| CLINIC | 102 | KAREMA MED CLINIC |
| MEDICAL or MED | 80 | SEASIDE MED CENTRE |
| MATERNITY | 3 | PWANI MATERNITY AND NURSING HOME |
| MAT (separate abbreviation) | 1 | NEW WANANCHI NURS & MAT HOME |
| NURSING | 6 | MTWAPA NURSING HOME |
| NURS (separate abbreviation) | 1 | NEW WANANCHI NURS & MAT HOME |
| LABORATORY or LAB | 1 | JAMBO CLINIC & LABORATORY |
| IMAGING, RADIOLOGY, X-RAY/XRAY/X RAY, ULTRASOUND | 0 | — |
| OUTPATIENT / OUT PATIENT / OUT-PATIENT | 0 | — |
| EMERGENCY | 0 | — |

The other two literal MATERNITY names are MSENANGU NURSING  & MATERNITY HOME LTD
and WATAMU MATERNITY & NURSING HOME. A missing name token does not establish absence
of a service. Spelling variants such as CINIC and DIAGONSTIC are preserved, not
silently repaired or counted as clinical evidence.

## All potentially relevant attributes

| Attribute(s) | Actual content | Potential use and limit |
| --- | --- | --- |
| F_NAME | 209 unique names | Leads for manual record verification; not service evidence |
| Facility_T | Seven numeric codes | Candidate type signal if an authoritative codebook is obtained; not KEPH level |
| Agency | Six codes, all records populated | Ownership context / supplementary-source matching; not service evidence |
| Bed_Capacity | 209 nulls | Could describe documented capacity if populated; currently unusable, never available beds |
| No_of_doctors | 209 nulls | Could describe dated staffing if populated; currently unusable |
| No_of_nurses | 209 nulls | Same; cannot establish staff currently on duty |
| GlobalID, OBJECTID | Each unique across 209 | Identify source records for evidence links; not national facility codes |
| Facility_N | 132 distinct values; 17 zeros | Possible legacy crosswalk lead, not a unique key |
| HMIS | 92 distinct values; 118 zeros | Possible legacy crosswalk lead; not assumed to be current MFL code |
| Province, District, Division, LOCATION, Sub_Locati | Geographic/legacy administrative labels | Disambiguate facility identity for enrichment; no level or services |
| Latitude, Longitude and point geometry | All populated | Spatial cross-checks and proximity; not capability evidence |
| Spatial_Re | 11 coordinate-source labels | Trace provenance/accuracy; not a service field |
| CreationDate, EditDate | Same 2025-11-07 timestamp across records | ArcGIS management dates; not capability observation/verification dates |
| Creator, Editor | Publisher account on all records | Data-management provenance; not clinical verification |

Agency values/counts: PRIV 142; MOH 46; MISS 18; LA 1; AF 1; OTHER MIN 1.
No ownership codebook supplied; expansions are not asserted.

Spatial_Re values/counts: AMKENI 102; DANIDA 42; DHMT 26; KEMRI-KILIFI PROJECT 23;
DSA/DFH(MOH)-UNFPA REPORT 5; ILRI MKT CENTRE 3; ILRI VILLAGES 3;
SUBLOC CENTROID 2; ILRI MKT CENTRES 1; ILRI TOWNS 1; PSI 1.
These are source labels, not evidence that those organizations verified services.

## Requested field search

| Topic | Dedicated source field? | Finding |
| --- | --- | --- |
| Services | No | Some facility names contain SERVICES; no individual service listing |
| Facility level / KEPH | No | No level field, domain or verified mapping |
| Facility type | Yes | Facility_T, coded and undecoded |
| Maternity | No | Three literal name mentions plus one MAT abbreviation |
| Laboratory | No | One literal name mention |
| Imaging | No | No matching name tokens either |
| Outpatient | No | No matching name tokens either |
| Emergency | No | No matching name tokens either |
| Beds | Yes | Bed_Capacity, entirely null |
| Staffing | Yes | No_of_doctors and No_of_nurses, entirely null |
| Operating status / opening | No | No facility-operational or opening-hours fields |

ArcGIS metadata `capabilities` (Query/Create/etc.), `defaultVisibility`, and
`hasStaticData` describe the GIS service, not health services or facility operation.
Canonical capability fields were created by our schema and remain unknown; they
are not additional evidence in the source.

## Conclusion and sources

The strongest next leads are a verified Facility_T codebook and an authoritative
facility-ID crosswalk. Names, ownership and coordinates can assist manual matching;
none currently justify setting a capability or KEPH level. Beds/staff columns add
no information in this snapshot. Canonical data remains unchanged.

Sources inspected: [raw records](../data/facilities/raw/arcgis/records.json),
[layer schema](../data/facilities/raw/arcgis/layer.json),
[item metadata](../data/facilities/raw/arcgis/item.json), and
[retrieval manifest](../data/facilities/raw/arcgis/manifest.json).
