"""Export simplified Kenya county outlines for the app's offline map (Clinics tab).

    python3 scripts/export-map.py

Reads ml/data/boundaries (see its README for source and licence) and the facility directory, and writes
src/intake/kenyaMap.json: the country at low detail for the locator inset, the counties around Kilifi at
higher detail for the main map, and town labels taken from hospital records in the facility data.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTY = "Kilifi"


def simplify(points, tolerance):
    """Douglas-Peucker on a ring of [lon, lat]."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = points[a], points[b]
        dx, dy = x2 - x1, y2 - y1
        norm = (dx * dx + dy * dy) ** 0.5
        worst, index = 0.0, None
        for i in range(a + 1, b):
            x, y = points[i]
            d = abs(dy * (x - x1) - dx * (y - y1)) / norm if norm else ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
            if d > worst:
                worst, index = d, i
        if index is not None and worst > tolerance:
            keep[index] = True
            stack += [(a, index), (index, b)]
    return [p for p, k in zip(points, keep) if k]


def rings(geometry, tolerance, min_points=4):
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    out = []
    for polygon in polygons:
        ring = simplify([[round(x, 4), round(y, 4)] for x, y in polygon[0]], tolerance)  # outer ring only
        if len(ring) >= min_points:
            out.append(ring)
    return out


def bbox(all_rings):
    xs = [x for ring in all_rings for x, _ in ring]
    ys = [y for ring in all_rings for _, y in ring]
    return min(xs), min(ys), max(xs), max(ys)


features = json.loads((ROOT / "ml/data/boundaries/geoBoundaries-KEN-ADM1_simplified.geojson").read_text())["features"]
directory = json.loads((ROOT / "src/intake/kilifiDirectory.json").read_text())["facilities"]

county = next(f for f in features if f["properties"]["shapeName"] == COUNTY)
west, south, east, north = bbox(rings(county["geometry"], 0))
pad = 0.12
view = {"west": round(west - pad, 4), "south": round(south - pad, 4), "east": round(east + pad, 4), "north": round(north + pad, 4)}

detail = []
for f in features:
    shape = rings(f["geometry"], 0.004)
    if not shape:
        continue
    w, s, e, n = bbox(shape)
    if e < view["west"] or w > view["east"] or n < view["south"] or s > view["north"]:
        continue
    detail.append({"name": f["properties"]["shapeName"], "rings": shape})

country = [{"name": f["properties"]["shapeName"], "rings": rings(f["geometry"], 0.03, min_points=5)} for f in features]
cw, cs, ce, cn = bbox([r for c in country for r in c["rings"]])

# Town labels: the hospitals in the facility records mark the main towns.
towns = []
for f in directory:
    name = f["name"]
    if "HOSPITAL" in name and ("DISTRICT" in name or "SUB" in name):
        town = name.split(" DISTRICT")[0].split(" SUB")[0].title()
        if town not in [t["name"] for t in towns]:
            towns.append({"name": town, "latitude": f["latitude"], "longitude": f["longitude"]})

# A few more towns, placed at the first facility record that carries the town's name.
for town in ("MTWAPA", "MARIAKANI", "KALOLENI", "WATAMU"):
    record = next((f for f in directory if f["name"].startswith(town)), None)
    if record:
        towns.append({"name": town.title(), "latitude": record["latitude"], "longitude": record["longitude"]})

out = {
    "source": "geoBoundaries gbOpen KEN ADM1 (RCMRD GeoPortal, Africa GeoPortal), 2020, Public Domain; simplified by scripts/export-map.py",
    "county": COUNTY,
    "view": view,
    "detail": detail,
    "countryView": {"west": round(cw - 0.3, 3), "south": round(cs - 0.3, 3), "east": round(ce + 0.3, 3), "north": round(cn + 0.3, 3)},
    "country": [c for c in country if c["rings"]],
    "towns": towns,
}
path = ROOT / "src/intake/kenyaMap.json"
path.write_text(json.dumps(out, separators=(",", ":")) + "\n")
points = lambda group: sum(len(r) for c in group for r in c["rings"])
print(f"Wrote {path.relative_to(ROOT)}: {path.stat().st_size // 1024} KB; detail {len(detail)} counties / {points(detail)} points; country {points(out['country'])} points; towns {[t['name'] for t in towns]}")

# Sanity check: how many facilities fall inside the county outline used for the map.
def inside(x, y, ring):
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit

shape = next(c for c in detail if c["name"] == COUNTY)["rings"]
within = sum(any(inside(f["longitude"], f["latitude"], r) for r in shape) for f in directory)
print(f"{within} of {len(directory)} facilities fall inside the {COUNTY} outline; view {view}")
