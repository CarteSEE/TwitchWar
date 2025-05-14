const fs = require('fs');
const path = require('path');
const turf = require('@turf/turf');

const geoPath = path.resolve(__dirname, 'ne_10m_admin_1_states_provinces', 'cleaned10m.geojson');
const outPath = path.resolve(__dirname, 'ne_10m_admin_1_states_provinces', 'merged10m.geojson');

const geo = JSON.parse(fs.readFileSync(geoPath));
const large = [];
const small = [];

geo.features.forEach(f => {
  const km2 = turf.area(f) / 1e6;
  if (km2 < 3000) small.push(f);
  else           large.push(f);
});

// 2) Pour chaque petit, trouver un grand voisin et fusionner
small.forEach(s => {
  // d’abord ceux qui touchent
  let neighbor = large.find(g => turf.booleanIntersects(s, g));
  // si aucun voisin direct, on choisit le plus proche
  if (!neighbor) {
    const sc = turf.centroid(s);
    let bestDist = Infinity;
    large.forEach(g => {
      const gc = turf.centroid(g);
      const d  = turf.distance(sc, gc);
      if (d < bestDist) { bestDist = d; neighbor = g; }
    });
  }
  // fusion
  if (neighbor) {
    const merged = turf.union(neighbor, s);
    if (merged) neighbor.geometry = merged.geometry;
  }
});

// 3) On écrit le résultat
const out = { type: 'FeatureCollection', features: large };
fs.writeFileSync('merged10m.geojson', JSON.stringify(out, null, 2));
console.log('✅ merged10m.geojson généré.');
