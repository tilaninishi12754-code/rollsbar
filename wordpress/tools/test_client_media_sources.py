"""Focused source-build negative cases; no private assets or workbook contents committed."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

import build_client_media_canon as media


class Sources(unittest.TestCase):
    def test_wrong_archive_checksum_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            first = next(iter(media.SOURCES))
            (Path(d) / first).write_bytes(b'wrong archive bytes')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                media.build(Path(d))
            self.assertEqual([p.name for p in Path(d).iterdir()], [first])

    def test_unresolved_unknown_product(self):
        with self.assertRaisesRegex(ValueError, 'Unresolved/ambiguous'):
            media.resolve({'category':'Роллы','product_name':'Unknown','_cells':{},'variant':None}, [])

    def test_ambiguous_product(self):
        product = {'cat':'rolls','name':'Same','id':'id'}
        with self.assertRaisesRegex(ValueError, 'Unresolved/ambiguous'):
            media.resolve({'category':'Роллы','product_name':'Same','_cells':{},'variant':None}, [product,product])

    def test_known_deferred_is_not_failure(self):
        for row, name in [(83,'Охотничья'),(84,'Охотничья'),(85,'Салями'),(86,'Салями')]:
            self.assertEqual(media.resolve({'category':'Пицца','product_name':name,'table_row':row}, []),
                             (None,'deferred_new_product_identity'))

    def test_wrong_bytes_with_webp_extension(self):
        with self.assertRaises(ValueError):
            media.image_info(b'pretend-webp')

    def test_missing_and_conflicting_assets(self):
        # Exercise the actual build before its first write, with tiny synthetic XLSX/packages.
        def package(entries):
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as z:
                for name, data in entries.items(): z.writestr(name,data)
            return stream.getvalue()
        def rows(n, photo='asset'):
            return [{'table_row': i+4,'category':'Роллы','product_name':'P'+str(i % 47),'variant':str(i // 47),
                     'photo_name': photo, '_cells':{}} for i in range(n)]
        for conflict in [False, True]:
            with tempfile.TemporaryDirectory() as d:
                a=package({'Таблица Роллс бар.xlsx':b'old','asset.webp':b'a'})
                b=package({'Таблица Роллс бар.xlsx':b'new',**({'asset.webp':b'b'} if conflict else {})})
                sources={'a.zip':(len(a),media.sha(a)),'b.zip':(len(b),media.sha(b))}
                for name, data in [('a.zip',a),('b.zip',b)]: (Path(d)/name).write_bytes(data)
                with patch.object(media,'SOURCES',sources), patch.object(media,'table_rows',side_effect=[rows(50),rows(61)]), patch.object(media,'image_info',return_value=('image/webp',(1254,1254))):
                    with self.assertRaisesRegex(ValueError,'Duplicate basename' if conflict else 'Missing/unknown/unused photo'):
                        media.build(Path(d))
                self.assertEqual(len(list(Path(d).iterdir())),2)


if __name__ == '__main__':
    unittest.main()
