"""Compile the owner's 2026-10-29 staging authorization without changing the review source."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];PLUGIN=ROOT/'wordpress/wp-content/plugins/rollsbar-core'
SOURCE=ROOT/'wordpress/docs/delivery-draft-2026-10-29/review-data.json'
source=json.loads(SOURCE.read_text(encoding='utf8'))
features=[]
for f in source['layers']['proposals']['features']:
 p=f['properties']
 features.append({'type':'Feature','geometry':f['geometry'],'properties':{'id':p['id'],'minimum':p['minimum'],'kind':'locality' if p['layer']=='locality-footprint' else 'city'}})
data={'type':'FeatureCollection','authorization':'Owner instruction 2026-10-29: staging map and advisory geography; callback remains phone + explicit consent.','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'features':features}
serialized=json.dumps(data,ensure_ascii=False,separators=(',',':'))
(PLUGIN/'data/delivery-geography.json').write_text(serialized,encoding='utf8')
template=(ROOT/'qa/delivery-draft/checkout-map-template.html').read_text(encoding='utf8')
for marker,value in [('<!--LEAFLET_LICENSE-->','<!--\n'+(ROOT/'qa/delivery-draft/vendor/LICENSE').read_text(encoding='utf8')+'\n-->'),('/*LEAFLET_CSS*/',(ROOT/'qa/delivery-draft/vendor/leaflet.css').read_text(encoding='utf8')),('/*LEAFLET_JS*/',(ROOT/'qa/delivery-draft/vendor/leaflet.js').read_text(encoding='utf8')),('/*ZONE_DATA*/',serialized),('/*ROAD_DATA*/',json.dumps(source['layers']['roads'],ensure_ascii=False,separators=(',',':')))]:
 template=template.replace(marker,value)
(PLUGIN/'assets/delivery-map.html').write_text(template,encoding='utf8')
print('Checkout map compiled:',len(features),'polygons; no live mutation')
