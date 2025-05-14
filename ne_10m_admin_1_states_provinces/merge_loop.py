# merge_loop_strtree.py
#!/usr/bin/env python3
"""
Fusionne en boucle toutes les régions < THRESH_KM2 (km²) avec une STRtree pour accélérer
la recherche des voisins. Le script affiche la progression et gère la sortie GeoJSON.

Usage:
    python merge_loop_strtree.py cleaned10m.geojson merged10m.geojson
"""
import sys
import json
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
import pyproj
import numpy as np

# Seuil d'aire en km² (fusionne toute région < THRESH_KM2)
THRESH_KM2 = 50000

# Vérification des arguments
if len(sys.argv) < 3:
    print("Usage: python merge_loop_strtree.py input.geojson output.geojson")
    sys.exit(1)

infile, outfile = sys.argv[1], sys.argv[2]

# Projection WGS84 → WebMercator (mètres)
proj_to_m = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform

# Lecture du GeoJSON (UTF-8)
with open(infile, encoding='utf-8') as f:
    fc = json.load(f)

# Construction des features avec cache des géométries projetées et des aires
features = []
for feat in fc['features']:
    geom_wgs = shape(feat['geometry'])
    geom_m   = transform(proj_to_m, geom_wgs)
    area_km2 = geom_m.area / 1e6
    features.append({
        'geom': geom_wgs,
        '_geom_m': geom_m,
        'props': feat['properties'],
        'area_km': area_km2
    })

# Initialisation de l'index spatial
geoms_m = [f['_geom_m'] for f in features]
tree = STRtree(geoms_m)
merge_count = 0

# Fonction utilitaire calcul aire (avec cache)
def get_area(f):
    return f['area_km']

# Boucle de fusion
while True:
    # lister les petites régions
    smalls = [(i, get_area(f)) for i, f in enumerate(features) if get_area(f) < THRESH_KM2]
    if not smalls:
        break

    # sélectionner la plus petite
    idx_tiny, area_tiny = min(smalls, key=lambda x: x[1])
    tiny = features[idx_tiny]

    # retrouver rapidement les voisins via STRtree
    hits = tree.query(tiny['_geom_m'])
    neighbors = []
    for hit in hits:
        # hit peut être un index numpy ou une géométrie
        if isinstance(hit, (int, np.integer)):
            j = int(hit)
        else:
            # geoms_m contiennent les géométries, on retrouve l'index
            try:
                j = geoms_m.index(hit)
            except ValueError:
                continue
        if j == idx_tiny:
            continue
        # test d'intersection géométrique
        if tiny['geom'].intersects(features[j]['geom']):
            neighbors.append((j, features[j]))

    # si aucun voisin direct, fallback par distance centroïde
    if not neighbors:
        tiny_cent = tiny['geom'].centroid
        neighbors = sorted(
            [(j, f) for j, f in enumerate(features) if j != idx_tiny],
            key=lambda pair: tiny_cent.distance(pair[1]['geom'].centroid)
        )

    # choisir le voisin de plus petite aire
    idx_nb, neighbor = min(neighbors, key=lambda pair: pair[1]['area_km'])
    area_nb = neighbor['area_km']

    # récupérer noms pour affichage
    name_tiny = tiny['props'].get('name') or tiny['props'].get('name_en') or str(idx_tiny)
    name_nb   = neighbor['props'].get('name') or neighbor['props'].get('name_en') or str(idx_nb)
    print(f"Fusion {merge_count+1}: '{name_tiny}' ({area_tiny:.1f} km²) → '{name_nb}' ({area_nb:.1f} km²)")

    # fusion géométrique en WGS84
    merged_geom = unary_union([tiny['geom'], neighbor['geom']])
    # reprojection et recalcul d'aire unique
    merged_geom_m = transform(proj_to_m, merged_geom)
    merged_area   = merged_geom_m.area / 1e6

    # propriétés héritées du voisin
    merged_props = neighbor['props'].copy()

    # nouvelle feature
    newfeat = {
        'geom': merged_geom,
        '_geom_m': merged_geom_m,
        'props': merged_props,
        'area_km': merged_area
    }

    # mise à jour des données
    features = [f for i, f in enumerate(features) if i not in (idx_tiny, idx_nb)]
    features.append(newfeat)

    # reconstruire l'index spatial et liste geoms_m
    geoms_m = [f['_geom_m'] for f in features]
    tree    = STRtree(geoms_m)

    merge_count += 1

# Préparer la sortie GeoJSON
out_fc = {'type': 'FeatureCollection', 'features': []}
for f in features:
    out_fc['features'].append({
        'type': 'Feature',
        'geometry': mapping(f['geom']),
        'properties': f['props']
    })

# écrire le fichier final
with open(outfile, 'w', encoding='utf-8') as f:
    json.dump(out_fc, f, ensure_ascii=False)

print(f"\n✅ Terminé : {merge_count} fusions, {len(features)} régions finales. Sortie → {outfile}")