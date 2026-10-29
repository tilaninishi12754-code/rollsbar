"""Build review-only geographic hypotheses. No live delivery configuration writes."""
import sys,json,gzip,re,math,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'qa/.runtime/map-packages'))
import shapely
from shapely.geometry import Point,LineString,Polygon,MultiPoint,mapping,shape
from shapely.ops import unary_union,transform
OUT=ROOT/'wordpress/docs/delivery-draft-2026-10-29'
REG=json.loads((ROOT/'wordpress/wp-content/plugins/rollsbar-core/data/delivery-minimum.json').read_text(encoding='utf8'))
RAW=json.loads(gzip.decompress((OUT/'osm-extract.json.gz').read_bytes()))
ELS=RAW['elements'];BYID={(e['type'],e['id']):e for e in ELS}
ORIGIN=[34.099398,44.973541]
def project(x,y,z=None):return ((x-34.1)*78700,(y-44.95)*111195)
def unproject(x,y,z=None):return (round(x/78700+34.1,6),round(y/111195+44.95,6))
def norm(s):
 s=re.sub(r'\b(улица|ул|проспект|переулок|площадь)\b','',s.lower().replace('ё','е'))
 return re.sub(r'\s+',' ',re.sub(r'[^а-яa-z0-9]+',' ',s)).strip()
def names(e):return {norm(e.get('tags',{}).get(k,'')) for k in ['name','name:ru','alt_name','old_name']}-{''}
def coords(e):
 if e['type']=='node':return Point(e['lon'],e['lat'])
 if e.get('geometry'):return LineString([(p['lon'],p['lat']) for p in e['geometry']])
 parts=[[(p['lon'],p['lat']) for p in m['geometry']] for m in e.get('members',[]) if m.get('geometry') and m.get('role') in ['outer','']]
 rings=[]
 while parts:
  ring=parts.pop(0);changed=True
  while ring[0]!=ring[-1] and changed:
   changed=False
   for i,part in enumerate(parts):
    if ring[-1]==part[0]:ring+=part[1:]
    elif ring[-1]==part[-1]:ring+=part[-2::-1]
    elif ring[0]==part[-1]:ring=part[:-1]+ring
    elif ring[0]==part[0]:ring=part[::-1][:-1]+ring
    else:continue
    parts.pop(i);changed=True;break
  if len(ring)>3 and ring[0]==ring[-1]:rings.append(shapely.make_valid(Polygon(ring)))
 return unary_union(rings) if rings else None
def geom(e):
 g=coords(e)
 if g is None or g.is_empty:return None
 if e['type']=='way' and e.get('tags',{}).get('place') and len(g.coords)>3 and g.coords[0]==g.coords[-1]:g=shapely.make_valid(Polygon(g))
 return transform(project,g)
CITY=geom(BYID['relation',3030295]).simplify(15,preserve_topology=True)
ORIG=transform(project,Point(ORIGIN))
ROADS=[e for e in ELS if e.get('tags',{}).get('highway') and e.get('geometry')]
PLACES=[e for e in ELS if e.get('tags',{}).get('place')]
GEO={}
def geometry(e):
 key=(e['type'],e['id'])
 if key not in GEO:GEO[key]=geom(e)
 return GEO[key]
def ref(e):return f"https://www.openstreetmap.org/{e['type']}/{e['id']}"
POI={'B3':('node',11385490043),'B22':('way',92403678),'B25':('node',3693422903),'C15':('way',173565687),'D18':('way',95974262),'E5':('way',404353015),'E9':('way',693994772)}
SPELLING={'E7':'Строгоновка','H8':'Родниково'}
objects={};rows=[];features=[];urban=[];locality_polygons=[];interpretations=[]
def feature(g,props):return {'type':'Feature','properties':props,'geometry':mapping(transform(unproject,g))}
def add_object(r,label,g,elements,status,note='',alternatives=None):
 key=f"{r['minimum']}|{r['type']}|{label}"
 if key in objects:objects[key]['cells'].append(r['cell']);return objects[key]['id']
 oid='ref-'+str(len(objects)+1)
 pt=g if g.geom_type=='Point' else g.interpolate(g.length/2) if g.geom_type in ['LineString','MultiLineString'] else g.representative_point()
 row={'id':oid,'label':label,'minimum':r['minimum'],'kind':r['type'],'cells':[r['cell']],'match':status,'note':note,'position':list(unproject(pt.x,pt.y)),'osm':[ref(e) for e in elements],'alternatives':alternatives or []}
 objects[key]=row
 features.append(feature(g.simplify(8,preserve_topology=True),{**row,'layer':'reference'}))
 if CITY.buffer(100).intersects(g) and g.geom_type in ['LineString','MultiLineString','Point']:
  urban.append((r['minimum'],g,oid))
 elif CITY.buffer(100).intersects(pt):urban.append((r['minimum'],pt,oid))
 if r['type'] in ['locality','area'] and g.geom_type in ['Polygon','MultiPolygon']:
  locality_polygons.append(feature(g.simplify(25,preserve_topology=True),{'id':'footprint-'+oid,'label':label,'minimum':r['minimum'],'cells':row['cells'],'layer':'locality-footprint','status':'geographic_footprint_not_approved_delivery_boundary','note':'Географический контур OSM. Покрытие доставки целиком требует подтверждения.'}))
 return oid
for r in REG['rules']:
 row={**r,'references':[]}
 if r['type']=='unresolved':row['map_status']='boundary_question';rows.append(row);continue
 labels=r['aliases'] if r['cell']=='E8' else [r['aliases'][0]]
 for label in labels:
  if r['cell'] in POI:
   e=BYID[POI[r['cell']]];g=geometry(e)
   oid=add_object(r,label,g,[e],'landmark' if r['cell']!='B3' else 'interpreted_name','Ориентир, а не граница района.' if r['cell']!='B3' else 'Москольцо сопоставлено с подписью OSM «Московское кольцо»; проверить.')
  elif r['type']=='street':
   wanted={norm(a) for a in r['aliases']};candidates=[e for e in ROADS if names(e)&wanted]
   inside=[e for e in candidates if geometry(e).intersects(CITY)]
   chosen=inside or candidates
   if not chosen:continue
   g=unary_union([geometry(e) for e in chosen]);oid=add_object(r,label,g,chosen,'street_geometry','Показана найденная улица. Территория рядом с ней — отдельная гипотеза.')
  else:
   wanted={norm(label)}
   if r['cell'] in SPELLING:wanted={norm(SPELLING[r['cell']])}
   candidates=[e for e in PLACES if names(e)&wanted and geometry(e) is not None]
   if not candidates:continue
   # Prefer a village/town when the source explicitly calls it a settlement.
   priority={'village':0,'town':0,'suburb':1,'neighbourhood':2,'hamlet':2,'locality':3}
   candidates.sort(key=lambda e:(priority.get(e.get('tags',{}).get('place'),4) if r['type']=='locality' else 0, geometry(e).distance(ORIG)))
   # Local district names must not jump to a distant namesake village.
   preferred={'C6':('node',11385575704),'F5':('node',11385475310),'F10':('node',11385475310)}
   chosen=BYID[preferred[r['cell']]] if r['cell'] in preferred else candidates[0];centre=geometry(chosen).representative_point()
   nearby=[e for e in candidates if geometry(e).distance(centre)<1800]
   polygons=[e for e in nearby if geometry(e).geom_type in ['Polygon','MultiPolygon']]
   actual=max(polygons,key=lambda e:geometry(e).area) if polygons else chosen
   g=geometry(actual);far=[e for e in candidates if geometry(e).distance(centre)>=1800]
   status='candidate_spelling' if r['cell'] in SPELLING else 'candidate_namesake' if far else 'place_geometry' if polygons else 'place_point'
   note='Есть одноимённые места: предложен ближайший подходящий населённый пункт; проверить.' if far else 'Подпись населённого пункта; контура в извлечении нет.' if not polygons else 'Географический контур, не утверждённая зона доставки.'
   if r['cell'] in SPELLING:note=f"В таблице «{label}», в OSM «{SPELLING[r['cell']]}». Предполагаемое соответствие, проверить."
   alternatives=[{'name':e.get('tags',{}).get('name'),'position':list(unproject(geometry(e).representative_point().x,geometry(e).representative_point().y)),'osm':ref(e)} for e in far if e['type']=='node']
   oid=add_object(r,label,g,[actual],status,note,alternatives)
   if status.startswith('candidate'):interpretations.append({'cell':r['cell'],'source':r['source'],'candidate':actual.get('tags',{}).get('name'),'osm':ref(actual),'note':note})
  row['references'].append(oid)
 row['map_status']='located' if row['references'] else 'needs_location';rows.append(row)

# Proposed urban background: closest sampled reference; explicit street rules remain exceptions.
samples={}
for tier,g,oid in urban:
 gs=list(g.geoms) if g.geom_type.startswith('Multi') else [g]
 for part in gs:
  points=[part] if part.geom_type=='Point' else [part.interpolate(min(i*150,part.length)) for i in range(max(1,int(part.length/150))+1)]
  for p in points:
   key=(round(p.x,2),round(p.y,2))
   if key not in samples:samples[key]=(tier,oid,p)
collection=MultiPoint([v[2] for v in samples.values()])
cells=shapely.voronoi_polygons(collection,extend_to=CITY.envelope,ordered=True)
groups={};support=unary_union([g for _,g,_ in urban]).buffer(500)
for cell,(tier,oid,_) in zip(cells.geoms,samples.values()):
 clipped=cell.intersection(CITY)
 if not clipped.is_empty:groups.setdefault(tier,[]).append(clipped)
proposals=[]
for tier,parts in groups.items():
 # Shared Voronoi edges stay identical: independent simplification would create gaps/overlaps.
 g=unary_union(parts)
 proposals.append(feature(g,{'id':'city-'+str(tier),'minimum':tier,'label':f'Город: черновик {tier} ₽','layer':'proposal','status':'UNAPPROVED_HYPOTHESIS','method':'Voronoi of 150 m street samples and named reference points; clipped to OSM city footprint','note':'Эскиз для адресов вне таблицы. Не цена, не утверждённая граница. Точные улицы из таблицы предлагаются как исключения.'}))
uncertain=CITY.difference(support).simplify(35,preserve_topology=True)
context=[feature(CITY.simplify(30),{'id':'city-outline','label':'Симферополь: географический контур OSM','layer':'city-outline'})]
if not uncertain.is_empty:context.append(feature(uncertain,{'id':'no-near-reference','label':'Нет ориентира таблицы в пределах 500 м','layer':'uncertainty','note':'500 м — диагностический порог эскиза, не радиус доставки. Требует проверки.'}))
# Schematic direction only. The Central Market is independently a 2000 ₽ source entry.
market=geometry(BYID['way',95974262]).representative_point()
context.append(feature(LineString([ORIG,market]),{'id':'market-direction','label':'От Rolls Bar к Центральному рынку: уточнить участок 1500 ₽','layer':'question-direction','cells':['C10','D18'],'note':'Прямая показывает направление, не автомобильный маршрут и не границу.'}))
context.append(feature(ORIG,{'id':'rollsbar','label':'Rolls Bar · Кечкеметская улица, 1','layer':'origin','source':'https://rolls-bar-kechkemetskaja-ulitsa.clients.site/'}))
roads=[]
for e in ROADS:
 g=geometry(e)
 if g and not g.is_empty:roads.append(feature(g.simplify(18),{'name':e.get('tags',{}).get('name','')}))
package={'title':'Rolls Bar · черновая карта доставки','date':'2026-10-29','status':'DRAFT_FOR_REVIEW_NOT_LIVE','source':REG['source'],'source_sha256':REG['sha256'],'origin':ORIGIN,'rows':rows,'references':list(objects.values()),'layers':{'references':{'type':'FeatureCollection','features':features},'proposals':{'type':'FeatureCollection','features':proposals+locality_polygons},'context':{'type':'FeatureCollection','features':context},'roads':{'type':'FeatureCollection','features':roads}},'interpretations':interpretations,'method':{'urban':'Closest sampled source reference, 150 m sampling; geographic city clip. Proposal only, not travel time, road accessibility or approved coverage. Exact source streets/localities remain proposed exceptions.','uncertainty':'Geographic city area >500 m from a table reference; diagnostic only, never a delivery radius.','localities':'Existing OSM place polygons where available; point markers otherwise. No arbitrary circles or outer delivery limit inferred.','unlocated':'No invented coordinate for an ambiguous/unlocated landmark.'}}
for name,data in [('review-data.json',package),('draft-zones.geojson',package['layers']['proposals']),('references.geojson',package['layers']['references'])]:
 (OUT/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
audit={'source_rows':len(rows),'located_rows':sum(bool(r['references']) for r in rows),'boundary_rows':[r['cell'] for r in rows if r['map_status']=='boundary_question'],'unlocated':[{'cell':r['cell'],'source':r['source']} for r in rows if r['map_status']=='needs_location'],'references':len(objects),'proposed_city_tiers':sorted(groups),'all_seven_tiers_in_references':sorted({r['minimum'] for r in objects.values()}),'hypotheses_are_unapproved':True,'geometry_valid':all(shape(f['geometry']).is_valid for f in proposals+locality_polygons)}
city_parts=[unary_union(parts) for parts in groups.values()]
audit['city_gap_square_metres']=CITY.difference(unary_union(city_parts)).area
audit['city_overlap_square_metres']=sum(g.area for g in city_parts)-unary_union(city_parts).area
assert audit['source_rows']==92 and audit['geometry_valid']
assert abs(audit['city_gap_square_metres'])<0.01 and abs(audit['city_overlap_square_metres'])<0.01
assert len({r['cell'] for r in rows})==92
assert audit['all_seven_tiers_in_references']==[1200,1500,2000,2500,3000,3500,4000]
assert all(any(oid==o['id'] and r['cell'] in o['cells'] for o in objects.values()) for r in rows for oid in r['references'])
(OUT/'draft-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(audit,ensure_ascii=False,indent=2))
