"""Read-only geographic extract for an owner-review draft, never checkout rules."""
import json,subprocess,hashlib,zipfile,gzip,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'wordpress/docs/delivery-draft-2026-10-29';OUT.mkdir(exist_ok=True)
registry=json.loads((ROOT/'wordpress/wp-content/plugins/rollsbar-core/data/delivery-minimum.json').read_text(encoding='utf8'))
source=Path('C:/Users/Nikita Born/Downloads/Telegram Desktop/маршрут доставка.xlsx')
assert hashlib.sha256(source.read_bytes()).hexdigest()==registry['sha256']
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(source) as z:
 strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)] if 'xl/sharedStrings.xml' in z.namelist() else []
 cells={}
 for c in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:c',ns):
  v=c.find('s:v',ns)
  cells[c.attrib['r']]=strings[int(v.text)] if c.attrib.get('t')=='s' and v is not None else ''.join(c.find('s:is',ns).itertext()) if c.attrib.get('t')=='inlineStr' else v.text if v is not None else ''
 for r in registry['rules']:assert cells.get(r['cell'],'').strip()==r['source'].strip(),r['cell']
(OUT/'source-audit.json').write_text(json.dumps({'file':source.name,'sha256':registry['sha256'],'sheet':registry['sheet'],'matched_source_cells':len(registry['rules']),'overrides':{'G8':'Мазанка = 4000 instead of original 3500; owner confirmation'}},ensure_ascii=False,indent=2),encoding='utf8')
query='''[out:json][timeout:35];(
nwr["place"]["name"](44.65,33.65,45.3,34.7);
way["highway"]["name"](44.83,34.0,45.06,34.25);
nwr["amenity"~"hospital|bus_station|marketplace"]["name"](44.83,34.0,45.06,34.25);
nwr["shop"="mall"]["name"](44.83,34.0,45.06,34.25);
nwr["railway"="station"]["name"](44.83,34.0,45.06,34.25);
relation["boundary"="administrative"]["name"="Симферополь"](44.83,34.0,45.06,34.25);
);out geom;'''
(OUT/'osm-query.txt').write_text(query,encoding='utf8')
# Explicit regeneration only. Ordinary rebuilds use the committed geographic snapshot.
if __name__=='__main__':
 import sys
 if '--fetch' not in sys.argv:
  print('Workbook audit PASS. Geography unchanged; pass --fetch to refresh public bbox.');sys.exit(0)
 endpoint='https://maps.mail.ru/osm/tools/overpass/api/interpreter'
 raw=subprocess.check_output(['curl.exe','--fail','--silent','--show-error','--max-time','55','--data-urlencode',f'data@{OUT / "osm-query.txt"}',endpoint])
 data=json.loads(raw);assert data.get('elements')
 (OUT/'osm-extract.json.gz').write_bytes(gzip.compress(raw,mtime=0))
 (OUT/'osm-source.json').write_text(json.dumps({'endpoint':endpoint,'query':'osm-query.txt','osm_base':data.get('osm3s',{}).get('timestamp_osm_base'),'sha256_uncompressed':hashlib.sha256(raw).hexdigest(),'license':'ODbL; © OpenStreetMap contributors','elements':len(data['elements']),'privacy':'Generic public geographic bbox query only; client table and pricing were not sent externally.'},ensure_ascii=False,indent=2),encoding='utf8')
 print('OSM',len(data['elements']),'elements',len(raw),'bytes',flush=True)
