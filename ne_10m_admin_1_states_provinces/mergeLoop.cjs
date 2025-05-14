/* mergeLoop.cjs
 * Boucle de fusion des polygones < THRESH_KM2
 * Usage : node mergeLoop.cjs input.geojson output.geojson
 */

const fs = require('fs');
const path = require('path');
const turf = require('@turf/turf');
const pc   = require('polygon-clipping');
// récupère la fonction quel que soit le format d'export
const rbushMod = require('rbush');
const RBush    = rbushMod.default || rbushMod;

const THRESH_KM2 = 3000;

// ---------- outils ---------- //
function areaKm2(f) { return turf.area(f) / 1e6; }
function featureBBox(f) {
  const [minX,minY,maxX,maxY] = turf.bbox(f);
  return {minX, minY, maxX, maxY, id: f.id};
}

// ---------- lecture ---------- //
const inPath  = process.argv[2] || 'cleaned10m.geojson';
const outPath = process.argv[3] || 'merged10m.geojson';
let fc = JSON.parse(fs.readFileSync(inPath));

// assure un id unique simple
fc.features.forEach((f,i)=>{ f.id = i; f.properties._merged = false; });

// ---------- index spatial ---------- //
let tree = new RBush();
tree.load(fc.features.map(featureBBox));

// ---------- boucle principale ---------- //
let changed = true;
while (changed) {
  // chercher le plus petit polygone < seuil
  const small = fc.features
      .filter(f => !f.properties._merged && areaKm2(f) < THRESH_KM2)
      .sort((a,b) => areaKm2(a) - areaKm2(b));

  if (small.length === 0) { changed = false; break; }

  const tiny = small[0];                              // le plus petit
  const bbox = featureBBox(tiny);
  const candidates = tree.search(bbox)                // voisins bbox
      .map(b => fc.features.find(f => f.id === b.id))
      .filter(f => f.id !== tiny.id && turf.booleanIntersects(tiny, f));

  if (candidates.length === 0) {
    console.warn(`❗ Aucun voisin pour id ${tiny.id} – ignoré`);
    tiny.properties._merged = true;
    continue;
  }

  // voisin le plus petit
  const neighbor = candidates
      .sort((a,b) => areaKm2(a) - areaKm2(b))[0];

  // ---------- union géométrique ---------- //
  let mergedGeom;
  try {
    mergedGeom = { type: 'MultiPolygon',
      coordinates: pc.union(tiny.geometry.coordinates, neighbor.geometry.coordinates)
    };
  } catch (e) {
    console.warn(`⚠️  Union échouée (id ${tiny.id}/${neighbor.id}) – tentative Turf`);
    const turfUnion = turf.union(tiny, neighbor);
    if (!turfUnion) { console.error('Échec définitif, on saute'); tiny.properties._merged = true; continue; }
    mergedGeom = turfUnion.geometry;
  }

  // ---------- nouveau feature ---------- //
  const mergedFeat = {
    type: 'Feature',
    geometry: mergedGeom,
    properties: {...neighbor.properties}, // hérite des props du voisin
    id: fc.features.length                // nouvel id
  };

  // MAJ des données
  tiny.properties._merged = true;
  neighbor.properties._merged = true;

  // retirer les deux anciennes BBox du rtree puis ajouter la nouvelle
  tree.remove(featureBBox(tiny), (a,b)=>a.id===b.id);
  tree.remove(featureBBox(neighbor), (a,b)=>a.id===b.id);
  tree.insert(featureBBox(mergedFeat));

  // enlever les deux features, ajouter le nouveau
  fc.features = fc.features.filter(f => !f.properties._merged);
  fc.features.push(mergedFeat);
}

// ---------- écriture ---------- //
fs.writeFileSync(outPath, JSON.stringify(fc));
console.log(`✅  ${outPath} écrit – ${fc.features.length} régions, seuil ${THRESH_KM2} km² atteint.`);
