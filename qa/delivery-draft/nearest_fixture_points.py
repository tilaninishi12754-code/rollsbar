"""Independent Shapely oracle for owner-approved nearest-area coverage."""
import json,math,hashlib
from pathlib import Path
from shapely.geometry import shape,Point
from shapely.affinity import scale
root=Path(__file__).resolve().parents[2]
raw=(root/'wordpress/wp-content/plugins/rollsbar-core/data/delivery-geography.json').read_bytes()
features=[(shape(f['geometry']),f['properties']) for f in json.loads(raw)['features']]
def classify(x,y):
 p=Point(x,y);inside=[props for g,props in features if g.covers(p)]
 if inside:
  local=[r for r in inside if r['kind']=='locality'];inside=local or inside
  return {'minimum':max(r['minimum'] for r in inside),'distance_m':0,'basis':'owner_geographic_advisory'}
 sx=6371000*math.pi/180*math.cos(math.radians(y));sy=6371000*math.pi/180
 distances=[(scale(g,xfact=sx,yfact=sy,origin=(x,y)).distance(p),props) for g,props in features]
 distance=min(d for d,_ in distances);nearest=[props for d,props in distances if abs(d-distance)<=.000001]
 return {'minimum':max(r['minimum'] for r in nearest),'distance_m':round(distance),'basis':'owner_nearest_zone'}
groups={k:[] for k in ['NE','NW','SE','SW']}
for i in range(45):
 for j in range(45):
  x=33.9+i*.012;y=44.77+j*.012;answer=classify(x,y)
  if answer['basis']!='owner_nearest_zone' or answer['distance_m']>10000:continue
  quadrant=('N' if y>=44.953 else 'S')+('E' if x>=34.115 else 'W')
  if len(groups[quadrant])<8:groups[quadrant].append({'point':[x,y],**answer})
assert all(len(v)==8 for v in groups.values())
doc={'geography_sha256':hashlib.sha256(raw).hexdigest(),'oracle':'Shapely metric distance to polygon area, not centroid/store radius','cases':[dict(quadrant=k,**r) for k,values in groups.items() for r in values]}
(root/'qa/checkout/nearest-points.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
# Existing real provider identities whose previous split-street exclusion is now superseded.
existing=root/'qa/visual-results/map-live-41031129897/delivery-rules/address-evidence.json'
if existing.exists():
 for row in json.loads(existing.read_text(encoding='utf8'))['cases']:
  if row['query'] in ['Симферополь Кечкеметская 79','Симферополь Беспалова 53']:
   d=row['identity'];print(row['query'],d.get('qc_geo'),classify(float(d['geo_lon']),float(d['geo_lat'])))
print('32 independent nearest-zone cases saved, all four quadrants')
