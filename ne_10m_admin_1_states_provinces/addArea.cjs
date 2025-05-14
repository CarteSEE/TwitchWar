const fs   = require('fs');
const path = require('path');
const turf = require('@turf/turf');

// __dirname = dossier où se trouve ce script
const src = path.join(__dirname, 'cleaned10m.geojson');
const dst = path.join(__dirname, 'cleaned10m_area.geojson');

const geo = JSON.parse(fs.readFileSync(src));

geo.features.forEach(f => {
  f.properties.area_km = turf.area(f) / 1e6;
});

fs.writeFileSync(dst, JSON.stringify(geo));
console.log('✅  area_km ajouté →', path.basename(dst));
