from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'wordpress/docs/delivery-draft-2026-10-29'
template=(ROOT/'qa/delivery-draft/review-template.html').read_text(encoding='utf8')
license_text=(ROOT/'qa/delivery-draft/vendor/LICENSE').read_text(encoding='utf8')
template=template.replace('<head>','<head><!-- Embedded Leaflet license:\n'+license_text+'\n-->')
for marker,path in [('/*LEAFLET_CSS*/',ROOT/'qa/delivery-draft/vendor/leaflet.css'),('/*LEAFLET_JS*/',ROOT/'qa/delivery-draft/vendor/leaflet.js'),('/*REVIEW_DATA*/',OUT/'review-data.json')]:
 text=path.read_text(encoding='utf8').replace('</script','<\\/script')
 template=template.replace(marker,text)
(OUT/'index.html').write_text(template,encoding='utf8')
print('Portable review HTML:',(OUT/'index.html').stat().st_size,'bytes')
