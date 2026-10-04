# Kenya county boundaries

`geoBoundaries-KEN-ADM1_simplified.geojson`: the 47 county boundaries (ADM1), simplified geometry, from
[geoBoundaries](https://www.geoboundaries.org) gbOpen, release `9469f09`. Boundary source: RCMRD GeoPortal,
Africa GeoPortal. Represents 2020. Licence: Public Domain. Downloaded 2026-10-04 from
<https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/KEN/ADM1/geoBoundaries-KEN-ADM1_simplified.geojson>.

Used only to draw the offline map in the app's Clinics tab. `scripts/export-map.py` simplifies it further and
writes `src/intake/kenyaMap.json`. Boundaries are for orientation, not for legal or administrative use.
