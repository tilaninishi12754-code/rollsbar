#!/usr/bin/env python3
"""Build public website media from verified private packages; never publish XLSX/ZIP.

Build is optional provenance tooling. Runtime needs only committed manifest/images.
All source validation completes in memory before any output is written.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import struct
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
VERSION = 'client-media-2026-10-21'
OUTPUT = ROOT / 'wordpress/data/product-media/client-2026-10-21'
SOURCES = {
    '19-10-2026_09-24-58.zip': (7550703, '9ce332520d715225a527bde90b439aa9a306579415ed3d18ab18212e1889b531'),
    '21-10-2026_10-48-20.zip': (8280976, '336150f653fc2247e92612fe3388a996449222b3bc17e2b351c97d804d5d00ef'),
}
DEFERRED = {'Охотничья', 'Салями'}
CATEGORIES = {'WOK и рис': 'wok', 'Запеченные': 'baked', 'Пицца': 'pizza', 'Роллы': 'rolls', 'Темпура': 'tempura'}
# These are proven by exact category and composition, not approximate name matching.
ALIASES = {'Запеченный рис спайси': 'baked-rice-shrimp', 'Запеченный рис унаги': 'baked-rice-salmon'}
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def normalized(value):
    return re.sub(r'\s+', ' ', str(value or '').lower().replace('ё', 'е')).strip()


def image_info(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png', struct.unpack('>II', data[16:24])
    require(data[:4] == b'RIFF' and data[8:12] == b'WEBP', 'Unsupported image bytes')
    kind = data[12:16]
    if kind == b'VP8X':
        size = tuple(int.from_bytes(data[p:p+3], 'little') + 1 for p in (24, 27))
    elif kind == b'VP8 ':
        require(data[23:26] == b'\x9d\x01\x2a', 'Invalid WebP frame')
        size = tuple(x & 0x3fff for x in struct.unpack('<HH', data[26:30]))
    elif kind == b'VP8L':
        require(data[20] == 0x2f, 'Invalid WebP lossless frame')
        bits = int.from_bytes(data[21:25], 'little')
        size = ((bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1)
    else:
        raise ValueError('Unknown WebP frame')
    return 'image/webp', size


def table_rows(data):
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        strings = []
        if 'xl/sharedStrings.xml' in book.namelist():
            for entry in ET.fromstring(book.read('xl/sharedStrings.xml')).findall('s:si', NS):
                strings.append(''.join(t.text or '' for t in entry.iterfind('.//s:t', NS)))
        rows = []
        for row in ET.fromstring(book.read('xl/worksheets/sheet1.xml')).findall('.//s:row', NS):
            cells = {}
            for cell in row.findall('s:c', NS):
                v = cell.find('s:v', NS)
                value = v.text if v is not None else ''
                if cell.get('t') == 's':
                    value = strings[int(value)]
                elif cell.get('t') == 'inlineStr':
                    value = ''.join(t.text or '' for t in cell.iterfind('.//s:t', NS))
                cells[re.sub(r'\d', '', cell.get('r'))] = value
            if int(row.get('r')) > 3 and cells.get('G'):
                rows.append({'table_row': int(row.get('r')), 'category': cells.get('A', ''),
                             'product_name': cells.get('B', ''), 'variant': cells.get('C', '') or None,
                             'photo_name': cells['G'], '_cells': cells})
        return rows


def resolve(row, catalog):
    cat = CATEGORIES.get(row['category'])
    if row['product_name'] in DEFERRED:
        require(cat == 'pizza' and row['table_row'] in (83, 84, 85, 86), 'Unexpected deferred row')
        require(not any(normalized(p['name']) == normalized(row['product_name']) for p in catalog), 'Deferred product now exists: new decision required')
        return None, 'deferred_new_product_identity'
    matches = [p for p in catalog if p['cat'] == cat and normalized(p['name']) == normalized(row['product_name'])]
    basis = 'exact_normalized_category_name_variant'
    if row['product_name'] in ALIASES:
        matches = [p for p in catalog if p['id'] == ALIASES[row['product_name']] and p['cat'] == cat
                   and normalized(p['desc']) == normalized(row['_cells'].get('F'))]
        basis = 'explicit_alias_exact_category_and_composition'
    require(len(matches) == 1, 'Unresolved/ambiguous product: ' + row['product_name'])
    product = matches[0]
    variants = product.get('variants', [])
    require(not variants or row['variant'] in [v['label'] for v in variants], 'Unknown variant')
    require(not row['variant'] or bool(variants), 'Unexpected variant on simple product')
    return product['id'], basis


def slug(name):
    alphabet = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                        ['a','b','v','g','d','e','e','zh','z','i','y','k','l','m','n','o','p','r','s','t','u','f','h','c','ch','sh','sch','','y','','e','yu','ya']))
    value = ''.join(alphabet.get(c, c) for c in name.lower())
    return re.sub(r'[^a-z0-9]+', '-', value).strip('-')


def build(source_dir):
    catalog = json.loads((ROOT / 'wordpress/data/catalog.json').read_text(encoding='utf-8'))['products']
    tables, pool, sources, private = [], {}, [], {}
    for filename, (length, expected) in SOURCES.items():
        data = (source_dir / filename).read_bytes()
        require(len(data) == length and sha(data) == expected, 'Source archive checksum mismatch: ' + filename)
        private[filename] = data
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            table_names = [n for n in package.namelist() if n.lower().endswith('.xlsx')]
            require(len(table_names) == 1 and Path(table_names[0]).name == 'Таблица Роллс бар.xlsx', 'Unexpected source table')
            table = package.read(table_names[0])
            private[filename + '.xlsx'] = table
            tables.append(table_rows(table))
            sources.append({'filename': filename, 'bytes': length, 'sha256': expected,
                            'table': {'filename': table_names[0], 'sha256': sha(table),
                                      'status': 'current_photo_assignment_authority' if len(tables) == 2 else 'historical_customer_evidence',
                                      'mapped_rows': len(tables[-1])}})
            for entry in package.infolist():
                if entry.is_dir() or entry.filename in table_names:
                    continue
                blob = package.read(entry)
                mime, dimensions = image_info(blob)
                require(dimensions == (1254, 1254), 'Unexpected image dimensions')
                name = Path(entry.filename).stem
                if name in pool:
                    require(sha(pool[name]['bytes']) == sha(blob), 'Duplicate basename with conflicting bytes')
                else:
                    pool[name] = {'bytes': blob, 'mime': mime, 'dimensions': list(dimensions), 'provenance': []}
                pool[name]['provenance'].append({'archive': filename, 'member': entry.filename})
    old, latest = tables
    signature = lambda r: (r['category'], r['product_name'], r['variant'], r['photo_name'])
    require(len(old) == 50 and len(latest) == 61, 'Source table count mismatch')
    require(len(set(r['product_name'] for r in latest)) == 47, 'Source name count mismatch')
    require(set(map(signature, old)) <= set(map(signature, latest)) and len(set(map(signature, latest)) - set(map(signature, old))) == 11, 'Historical assignment conflict')
    require(len(pool) == 36 and set(pool) == {r['photo_name'] for r in latest}, 'Missing/unknown/unused photo')
    require(Counter(p['mime'] for p in pool.values()) == {'image/webp': 32, 'image/png': 4}, 'MIME count mismatch')
    require(len({sha(p['bytes']) for p in pool.values()}) == 36, 'Unexpected duplicate binary')
    assets, rows, files, differences = [], [], {}, []
    by_id = {p['id']: p for p in catalog}
    for row in latest:
        sid, basis = resolve(row, catalog)
        cells = row['_cells']
        record = {k: v for k, v in row.items() if k != '_cells'}
        record.update({'source_id': sid, 'media_key': slug(row['photo_name']),
                       'status': 'resolved' if sid else 'deferred_new_product_identity', 'resolution': basis})
        if sid is None:
            record['reason'] = 'No canonical RollsBar source ID currently exists; separate catalog decision required.'
        else:
            record['catalog_name'] = by_id[sid]['name']
            record['catalog_category'] = by_id[sid]['cat']
        rows.append(record)
        if sid:
            p = by_id[sid]
            expected_price = next((str(v['price']) for v in p.get('variants', []) if v['label'] == row['variant']), str(p['price']))
            for field, actual, canonical in [('name', cells.get('B'), p['name']), ('price', cells.get('D'), expected_price),
                                              ('description', cells.get('F'), p.get('desc')), ('weight', cells.get('E'), None),
                                              ('options', cells.get('C') if not p.get('variants') else None, p.get('options'))]:
                if str(actual or '') != str(canonical or ''):
                    differences.append({'source_id': sid, 'table_row': row['table_row'], 'field': field,
                                        'customer': actual, 'catalog': canonical, 'action': 'review_only_not_applied'})
    assignments = {}
    for row in rows:
        if row['source_id']:
            require(row['source_id'] not in assignments or assignments[row['source_id']] == row['media_key'], 'Conflicting photos for variable parent/product')
            assignments[row['source_id']] = row['media_key']
    for name, p in sorted(pool.items()):
        key = slug(name)
        ext = 'png' if p['mime'] == 'image/png' else 'webp'
        filename = f'images/{key}.{ext}'
        require(filename not in files, 'Duplicate media key conflict')
        files[filename] = p['bytes']
        associated = [r for r in rows if r['media_key'] == key]
        assets.append({'canon_version': VERSION, 'media_key': key, 'original_photo_name': name,
                       'file': filename, 'source_ids': sorted({r['source_id'] for r in associated if r['source_id']}),
                       'assignment_rows': [r['table_row'] for r in associated], 'provenance': p['provenance'],
                       'source_sha256': sha(p['bytes']), 'derived_sha256': sha(p['bytes']),
                       'source_mime': p['mime'], 'derived_mime': p['mime'], 'dimensions': p['dimensions']})
    counts = {'assets': len(assets), 'preserved_rows': len(rows), 'resolved_rows': sum(r['status'] == 'resolved' for r in rows),
              'resolved_source_ids': len(assignments), 'deferred_rows': sum(r['status'] != 'resolved' for r in rows), 'deferred_products': 2}
    require(counts == {'assets':36,'preserved_rows':61,'resolved_rows':57,'resolved_source_ids':45,'deferred_rows':4,'deferred_products':2}, 'Manifest count mismatch')
    manifest = {'schema_version': 1, 'canon_version': VERSION, 'canon_date': '2026-10-21',
                'rule': 'For product media assignments covered by CLIENT MEDIA CANON v2026-10-21, client-supplied media manifest overrides legacy catalog/Yandex image sources. Do not change this rule without new explicit customer/user media input.',
                'sources': sources, 'counts': counts, 'assets': assets, 'assignments': rows}
    return manifest, files, private, differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--private-evidence', type=Path, help='Private directory OUTSIDE the public repo')
    parser.add_argument('--check', action='store_true', help='Validate source bytes and compare committed outputs without writing')
    args = parser.parse_args()
    manifest, files, private, differences = build(args.source_dir)
    files['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if args.private_evidence:
        require(not args.private_evidence.resolve().is_relative_to(ROOT), 'Private originals must be outside public repo')
    for name, data in files.items():
        target = OUTPUT / name
        if args.check:
            require(target.read_bytes() == data, 'Committed canon differs: ' + name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    if args.private_evidence and not args.check:
        args.private_evidence.mkdir(parents=True, exist_ok=True)
        private['non-media-differences-REVIEW-ONLY.json'] = (json.dumps(differences, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        for name, data in private.items():
            target = args.private_evidence / name
            if target.exists():
                require(target.read_bytes() == data, 'Refusing to overwrite private provenance')
            else:
                with target.open('xb') as output:
                    output.write(data)
    print(json.dumps({'status':'PASS','counts':manifest['counts'],'non_media_differences_review_only':len(differences)}))


if __name__ == '__main__':
    main()
