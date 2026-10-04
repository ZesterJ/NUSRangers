# Verified capability subset — 2026-10-04

## Result and meaning of verified

12 existing ArcGIS facilities investigated; **10 have at least one source-backed
claim**. 36 capability rows: 19 true, 17 unknown, zero false. Coverage: generalOutpatient
10, childHealth 3, maternal 6. The other 197 catalogue records were not enriched.
Across the full catalogue, 199 facilities therefore still have no confirmed claim
in this release (197 outside scope plus two unresolved matches).

“Verified” means the assistant checked a named public source for an explicit service
claim and documented the identity match. It does NOT mean current/on-site verification,
clinical review, current operating status, age eligibility or acceptance of referrals.
Human review is still pending. Six facilities rely on historical research observations;
four on undated indexed official/government/operator claims. This is enough for a
transparent source-snapshot hackathon demonstration, not an operational referral system.

The base `catalogue.json`, extractor, backend and frontend are unchanged. The learned
classifier remains an experiment; no training was run. New demo orchestration calls
`care_policy.rules_predict` by default and never loads the learned model.

## Service mapping policy

- generalOutpatient: explicit outpatient/curative clinic care, not facility type.
- childHealth: explicit paediatric assessment or observed care of sick children.
  Immunization or a child-welfare listing alone is insufficient for this assessment label.
- maternal: explicit antenatal, postnatal or maternity care. These are broad service
  categories, not confirmation of delivery, surgery or high-risk-pregnancy capacity.

Missing claims remain unknown. No negative values were fabricated. Level, name,
proximity and ownership were used only to help identify records, never to infer services.
No other capability was enabled, even where a source mentioned other services.

## Facility coverage

Names retain ArcGIS spelling. T = source-backed snapshot claim; ? = unknown.

| ArcGIS facility | Outpatient | Child assessment | Maternal | Evidence |
| --- | --- | --- | --- | --- |
| KILIFI DISTRICT HOSPITAL | T | T | T | Indexed production KMHFR #11474 |
| TAKAUNGU DISP | T | ? | T | Indexed production KMHFR #11836 |
| NGERENYA DISP | T | T | ? | Published 2016 outpatient / 2014–2018 child observations |
| MATSANGONI DISP | T | ? | T | Published 2016 outpatient / 2014 antenatal observations |
| JARIBUNI DISP | T | ? | ? | Published 2016 outpatient observations |
| CHASIMBA/MWELE DISP | T | ? | ? | Published 2016 outpatient observations |
| PINGILIKANI DISP | T | T | T | Published outpatient, child and antenatal observations |
| JUNJU DISP | T | ? | ? | Published 2016 outpatient observations |
| MALINDI DISTRICT HOSPITAL | T | ? | T | Council of Governors county-initiative report |
| TAWFIQ MUSLIM HOSPITAL | T | ? | T | Official operator service page |
| NEW WANANCHI NURS & MAT HOME | ? | ? | ? | Services found, identity mapping unresolved |
| MTWAPA DISP | ? | ? | ? | Hospital/dispensary match rejected |

Kilifi town and the surrounding public-clinic catchment dominate selection. Malindi
and Tawfiq are additional county candidates, not claimed to be near Kilifi town.

## Source coverage and limitations

All sources accessed 2026-10-04. Links and short evidence paraphrases, publication
year when known, observation period and retrieval form are retained in
[evidence/sources.json](../data/facilities/evidence/sources.json).
No full copyrighted web pages were copied; source-index content is not a full-page
archive. SourceDate is publication date/year when known, blank when unknown, and
is never substituted with access date or search-engine crawl date.

1. [Production KMHFR Kilifi #11474](https://kmhfr.health.go.ke/public/facilities/09d5776f-81a0-4bf0-bbbb-77d607803976):
   indexed service list explicitly includes general outpatient, paediatric outpatient,
   and focused antenatal services. Registry level 4, primary-care-hospital type and
   operational status are recorded as undated source claims only.
2. [Production KMHFR Takaungu #11836](https://kmhfr.health.go.ke/public/facilities/505bfafc-1eb3-4daf-8a68-30418b76b9ba):
   indexed outpatient and antenatal services support two labels. Child immunization
   does not establish child assessment. Source lists level 2, dispensary and operational;
   these remain dated-as-unknown registry metadata, not live opening information.
3. [Nyiro et al., outpatient surveillance](https://pmc.ncbi.nlm.nih.gov/articles/PMC6081997/):
   2018 publication, observations in 2016, identifies public clinics and routine outpatient
   care. Six uniquely matched sites used; Mavueni, Mtondia and Sokoke were not forced
   onto similarly named private ArcGIS records. Methods were available in indexed text;
   direct PMC page retrieval presented a browser challenge.
4. [Nyamwaya et al., child cohort](https://pmc.ncbi.nlm.nih.gov/articles/PMC7889702/):
   2021 publication documents care of febrile children below sixteen at Ngerenya and
   Pingilikani in 2014–2018. It does not establish today's scope or all-age eligibility.
5. [Nyundo et al., clinic linkage study](https://pmc.ncbi.nlm.nih.gov/articles/PMC7059845/):
   2020 article version, 2014 observations; facility-specific antenatal visits at
   Matsangoni and Pingilikani. Historical service evidence only.
6. [Council of Governors / Malindi](https://www.maarifa.cog.go.ke/county-initiatives/kilifi-county-strengthens-maternal-and-referral-care-modern-maternity-wing):
   indexed article reports completed maternity commissioning and outpatient upgrades.
   Exact publication/observation dates were not established. Future planned works were
   not treated as operating services. No child-assessment claim was extracted.
7. [Tawfiq's official operator](https://tawfiqmy.org/the-hospital/):
   indexed listing explicitly states outpatient and maternal services. Child-welfare
   scope is not sufficient to confirm the child-assessment label. Listing is undated.
8. [Wananchi official services](https://wananchihospital.org/services/):
   relevant services are explicit but transfer to either of the two old Wananchi
   ArcGIS identities is unresolved; all claims remain unknown for the selected record.
9. [Mtwapa test-host registry](https://kmhfltest.health.go.ke/public/facilities/55585f1c-6f0d-4bd0-a357-824e392def89):
   used only to document rejection, not capability evidence. Hospital coordinates differ
   from the ArcGIS dispensary by roughly 3.3 km. Test-host status adds uncertainty.

No direct registry scraping, live capacity feed or clinician review was performed.
Indexed production records are accepted only as source snapshots, explicitly permitted
by the task; earlier investigations had not obtained their full service lists.

## Crosswalk

[Crosswalk JSON](../data/facilities/evidence/crosswalk.json) preserves every canonical
ArcGIS ID, external ID where established, match rationale, coordinates, ownership
and locality. All rows record humanReviewed=false.

- Kilifi #11474: exact coordinate agreement to source rounding plus hospital identity
  and ownership. ArcGIS HMIS 565 is not substituted for MFL 11474.
- Takaungu #11836: matching name, ownership and locality with approximately 215 m
  coordinate discrepancy; not assumed exact. No competing public Takaungu record.
- Six rural clinics: manually documented unique public-name/locality matches within
  the research geography. ArcGIS MOH ownership excludes private namesakes. These are
  historical matches, not national-ID joins or confirmation that no relocation occurred.
- Malindi/Tawfiq: documented distinctive identity and locality matches, no national-ID
  join. Tawfiq is the operator's Malindi hospital; the locality is also stated in
  [its institutional history](https://tawfiqmy.org/our-main-aim/).
- Wananchi and Mtwapa: unresolved; excluded from confirmed-compatible candidates.

## Routing demonstration

Run `python3 ml/src/verified_facility_demo.py`. An in-memory overlay applies ONLY
accepted positive claims to the selected records; canonical source data is never
rewritten. Every returned candidate includes capability-level evidence with public
URLs, source date/period, access date and verification/match status. Original router
filtering/ranking is reused unchanged. Historical evidence is explicitly marked in
output; live availability always remains unknown.

Reference: the source Kilifi hospital coordinate, **not a real patient**. Its 0 km
result follows that deliberate anchor choice, not a facility preference. Ranking is
straight-line distance then stable ID; no travel times or level bonuses.

| Request | Up to three returned candidates (km) | Unknown exclusions |
| --- | --- | ---: |
| generalOutpatient | Kilifi hospital 0; Takaungu 5.645; Jaribuni 12.705 | 2 |
| childHealth | Kilifi hospital 0; Ngerenya 13.191; Pingilikani 18.360 | 9 |
| maternal | Kilifi hospital 0; Takaungu 5.645; Pingilikani 18.360 | 6 |
| All three required | Kilifi hospital 0; Pingilikani 18.360 | 10 |
| imaging (manual no-match probe) | None: insufficient_data | 12 |

No-match uses an unsupported manual request to demonstrate exclusion, not a service
inferred by the care policy. With no documented false values, the correct no-match
status is insufficient_data, not evidence that services do not exist. The router's
explicit no_compatible_facility branch is separately tested using a clearly synthetic
false-capability fixture, never added to the real CSV or catalogue.

Complete reproducible output: [verified_routing_examples.json](../data/facilities/verified_routing_examples.json).
For a structured patient projection: `python3 ml/src/verified_facility_demo.py --patient FILE.json`.
This uses only explicit care rules and abstains if they produce no services. No learned
model is loaded, and no request to the backend is made.

## Readiness

Enough for a source-labelled historical/registry-snapshot routing demo. Not enough
for current clinical referral recommendations. Before that, obtain human confirmation
of identity, age/service scope, dated current capabilities and approved clinical
policy; separately confirm opening and referral acceptance. Do not portray old study
observations or indexed registry claims as fresh facility inspections.
