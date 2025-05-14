#!/usr/bin/env python3
import sys, json
from shapely.geometry import shape
from shapely.strtree import STRtree

if len(sys.argv) != 3:
    print("Usage: python generate_neighbors.py input.geojson output.json")
    sys.exit(1)

infile, outfile = sys.argv[1], sys.argv[2]
with open(infile, 'r', encoding='utf-8') as f:
    data = json.load(f)
features = data['features']
geoms = [shape(f['geometry']) for f in features]
names = [f['properties'].get('name') or f['properties'].get('name_en') or str(i)
         for i, f in enumerate(features)]
tree = STRtree(geoms)
neighbors = {}
for idx, geom in enumerate(geoms):
        # retrieve candidate indices via STRtree
    if hasattr(tree, 'query_items'):
        hits = tree.query_items(geom)
    else:
        # fallback for shapely <2.0: use envelope intersection
        hits = [i for i, g in enumerate(geoms) if g.envelope.intersects(geom.envelope)]
    nbrs = []
    for j in hits:
        if j == idx: continue
        if geom.intersects(geoms[j]):
            nbrs.append(names[j])
    neighbors[names[idx]] = nbrs
    print(f"'{names[idx]}' has {len(nbrs)} neighbors")
with open(outfile, 'w', encoding='utf-8') as f:
    json.dump(neighbors, f, ensure_ascii=False, indent=2)
print(f"Done: wrote {outfile}")
