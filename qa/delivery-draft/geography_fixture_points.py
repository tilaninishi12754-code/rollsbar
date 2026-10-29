"""Independent GEOS point selection for PHP ray-casting regression fixtures."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'qa/.runtime/map-packages'))
from shapely.geometry import shape,box
data=json.loads((ROOT/'wordpress/wp-content/plugins/rollsbar-core/data/delivery-geography.json').read_text(encoding='utf8'))
objects=[(f['properties'],shape(f['geometry'])) for f in data['features']]
points={tier:[] for tier in [1200,1500,2000,2500,3000,3500,4000]}
for props,g in objects:
 parts=[g] if g.geom_type=='Polygon' else list(g.geoms)
 for part in parts:
  x0,y0,x1,y1=part.bounds
  for section in [part,part.intersection(box(x0,y0,(x0+x1)/2,y1)),part.intersection(box((x0+x1)/2,y0,x1,y1))]:
   if section.is_empty:continue
   p=section.representative_point();matches=[pr for pr,geo in objects if geo.contains(p)]
   local=[pr for pr in matches if pr['kind']=='locality'];matches=local or matches
   amounts={pr['minimum'] for pr in matches}
   if len(amounts)!=1:continue
   tier=amounts.pop();point=[round(p.x,6),round(p.y,6)]
   if point not in points[tier] and len(points[tier])<2:points[tier].append(point)
assert all(len(v)==2 for v in points.values())
(ROOT/'qa/checkout/geography-points.json').write_text(json.dumps(points,indent=2),encoding='utf8')
print('Independent GEOS fixtures:',sum(map(len,points.values())),'points / 7 tiers')
