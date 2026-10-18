"""Portable checks that the fixed legacy edition cannot follow current updates.

Run: python -B -X utf8 assignment_editions/legacy/test_legacy_assets.py
This test only reads the fixed edition; it does not import current mapping data.
"""
from pathlib import Path
from collections import Counter, defaultdict
import csv
import gc
import gzip
import hashlib
import html
import io
import json
import re
import unittest
import unicodedata

HERE = Path(__file__).resolve().parent
EXPECTED_MANIFEST = '7ad3381ed0669389d7333ea81f4d6f936af5533b8d729589ee5a15afaa1740a3'
EXPECTED_COMMIT = '4c16c8937c601fdc149ccb8cbba1b6085cc94692'
EXPECTED_SIDE = '8ee9e27651413f87f1404eb5c328e7ad8ba4bda3be61a442ac9585911a4a9600'
LOCAL = '局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)'
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
EXPECTED_CORRECTIONS = {
    'limak':'螺ᴸ', 'orkidit':'丸炎', 'orkidektomi':'丸除', 'orkidoterapi':'丸疗',
    'testikit':'丸炎ᵀ', 'paniklit':'脂炎', 'kuriterapi':'kuri疗',
    'litografi':'石ᴸᵀ志ᴳ', 'fotolitografi':'拍石ᴸᵀ志ᴳ', 'kromolitografi':'色ᴷᴹ石ᴸᵀ志ᴳ',
}

def sha(raw): return hashlib.sha256(raw).hexdigest()
def encoded(value): return json.dumps(value, ensure_ascii=False).encode('utf-8')
def plain(s): return html.unescape(re.sub(r'<[^>]*>', '', s))
def visible(s): return plain(re.sub(r'<rt[^>]*>.*?</rt>', '', s, flags=re.S))
def stripped(s): return re.sub(r'<rt[^>]*>.*?</rt>', '', s).replace('<ruby>','').replace('</ruby>','')
def norm(s):
    for a,b in zip('ĉĝĥĵŝŭĈĜĤĴŜŬ',['c^','g^','h^','j^','s^','u^','C^','G^','H^','J^','S^','U^']):
        s=s.replace(b,a).replace(b[:-1]+'x',a)
    return unicodedata.normalize('NFC',s)
def rows_sha(rows, identity=False):
    h=hashlib.sha256()
    for row in rows:
        h.update(encoded([row[0],*row[2:]] if identity else row));h.update(b'\n')
    return h.hexdigest()

def checked_manifest(raw):
    if sha(raw)!=EXPECTED_MANIFEST: raise ValueError('Frozen legacy manifest changed')
    return json.loads(raw)

def checked_asset(item, raw):
    if len(raw)!=item['bytes'] or sha(raw)!=item['sha256']:
        raise ValueError('Frozen legacy asset changed: '+item['path'])
    decoded=gzip.decompress(raw) if item['path'].endswith('.gz') else raw
    if len(decoded)!=item['decoded_bytes'] or sha(decoded)!=item['decoded_sha256']:
        raise ValueError('Frozen legacy decoded payload changed: '+item['path'])
    return decoded

class LegacyAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=checked_manifest((HERE/'manifest.json').read_bytes())
        cls.files=cls.manifest['files']
        raw=(HERE/'_identifier_sidecar.tsv').read_bytes()
        cls.side={r['root']:r for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter='\t')}

    def test_01_frozen_authority_and_absent_later_roots(self):
        self.assertEqual(self.manifest['edition_id'],'legacy')
        self.assertEqual(self.manifest['canonical_commit'],EXPECTED_COMMIT)
        self.assertEqual(sha((HERE/'_identifier_sidecar.tsv').read_bytes()),EXPECTED_SIDE)
        self.assertEqual(len(self.side),10467)
        for root,value in {'las':'留','emancip':'放','dot':'嫁妆','greft':'嫁接','tualet':'妆',
                           'satir':'讽刺','spermat':'精ˢ','spermati':'精ˢᴵ','ananas':'菠萝'}.items():
            self.assertEqual(self.side[root]['disp'],value)
        self.assertNotIn('prioritat',self.side); self.assertNotIn('spermatozo',self.side)
        self.assertEqual({k:v['after'] for k,v in self.manifest['local_corrections'].items()},EXPECTED_CORRECTIONS)

    def test_02_all_files_pinned_and_bounded(self):
        self.assertEqual(len(self.files),9)
        self.assertEqual(len({f['path'] for f in self.files}),9)
        for item in self.files:
            path=(HERE.parent/item['path']).resolve()
            self.assertTrue(path.is_relative_to(HERE.resolve()))
            self.assertLess(item['bytes'],100*1024*1024)
            checked_asset(item,path.read_bytes())

    def test_03_rules_identities_local_scope_and_retained_differences(self):
        aliases=defaultdict(list)
        for root,row in self.side.items(): aliases[norm(root)].append(row)
        for item in [f for f in self.files if f['role']=='kanji']:
            data=json.loads(checked_asset(item,(HERE.parent/item['path']).read_bytes()))
            self.assertEqual(sum(map(len,data.values())),548982)
            for group,rows in data.items():
                meta=item['groups'][group]
                self.assertEqual(len(rows),meta['rows'])
                self.assertEqual(rows_sha(rows),meta['decoded_rows_sha256'])
                self.assertEqual(rows_sha(rows,True),meta['identities_sha256'])
                if group!=LOCAL:
                    self.assertEqual(meta['source_rows_sha256'],meta['decoded_rows_sha256'])
                    self.assertEqual(meta['changed'],0)
                else:self.assertEqual(meta['changed'],30)
            local={row[0]:row[1] for row in data[LOCAL]}
            for root,value in EXPECTED_CORRECTIONS.items():
                for spelling in (root,root.title(),root.upper()):
                    self.assertEqual(visible(local[spelling]),value)
                    self.assertEqual(plain(RUBY.fullmatch(local[spelling])[2]),spelling)
            remaining=Counter(); unresolved=[]
            for root,display in local.items():
                if root!=root.lower():continue
                chosen=self.side.get(root)
                if chosen is None and len(aliases[norm(root)])==1:chosen=aliases[norm(root)][0]
                if chosen is None:unresolved.append(root);continue
                if visible(display)==chosen['disp']:continue
                pieces=list(RUBY.finditer(display))
                same=len(pieces)==1 and norm(plain(pieces[0][2]))==norm(root)
                remaining['homograph' if same else 'decomposition']+=1
            self.assertEqual(remaining,{'homograph':9,'decomposition':42})
            self.assertEqual(len(unresolved),10)
            del data;gc.collect()

    def test_04_manual_csv_and_pure_derivation(self):
        for item in [f for f in self.files if f['role']=='kanji_csv']:
            rows=dict(csv.reader(io.StringIO(checked_asset(item,(HERE.parent/item['path']).read_bytes()).decode('utf-8-sig'))))
            for root,value in EXPECTED_CORRECTIONS.items():self.assertEqual(rows[root],value)
            self.assertEqual(rows['las'],'留');self.assertEqual(rows['emancip'],'放')
            self.assertNotIn('prioritat',rows);self.assertNotIn('spermatozo',rows)
        find=lambda role:next(f for f in self.files if f['role']==role and f['lang']=='JA')
        kanji_item,pure_item=find('kanji'),find('pure')
        kanji=json.loads(checked_asset(kanji_item,(HERE.parent/kanji_item['path']).read_bytes()))
        pure=json.loads(checked_asset(pure_item,(HERE.parent/pure_item['path']).read_bytes()))
        self.assertEqual(list(kanji),list(pure))
        for group,rows in kanji.items():
            self.assertEqual(pure[group],[[r[0],stripped(r[1]),*r[2:]] for r in rows])

    def test_05_reject_edited_manifest_and_asset(self):
        raw=(HERE/'manifest.json').read_bytes()
        with self.assertRaises(ValueError):checked_manifest(raw.replace(b'legacy',b'latest',1))
        item=next(f for f in self.files if f['role']=='kanji_csv')
        raw=(HERE.parent/item['path']).read_bytes()
        with self.assertRaises(ValueError):checked_asset(item,raw.replace('留'.encode(),'放'.encode(),1))

if __name__=='__main__':unittest.main(verbosity=2)
