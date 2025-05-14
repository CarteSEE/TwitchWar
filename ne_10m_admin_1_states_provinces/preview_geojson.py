#!/usr/bin/env python3
# preview_with_geojsonpopup.py

import json
import folium

# 1. Crée la carte (ajuste le centre et le zoom si besoin)
m = folium.Map(location=[20, 0], zoom_start=2)

# 2. Charge ton GeoJSON en UTF-8
with open('merged10m.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 3. Ajoute la couche GeoJSON avec GeoJsonPopup
folium.GeoJson(
    data,
    name='Régions',
    style_function=lambda feat: {
        'fillColor': '#ececec',
        'color': '#444444',
        'weight': 1,
        'fillOpacity': 0.7
    },
    popup=folium.GeoJsonPopup(
        fields=['name'],         # change en 'name_en' si besoin
        aliases=['Région :'],    # label avant la valeur
        localize=True
    )
).add_to(m)

# 4. Contrôle des calques
folium.LayerControl().add_to(m)

# 5. Sauvegarde en HTML
m.save('preview_with_geojsonpopup.html')
print("🗺️ Ouvrez preview_with_geojsonpopup.html — cliquez sur une région pour voir son nom.")  
