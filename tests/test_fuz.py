"""Approved fuz displays, exact identifiers and fixed legacy roots.

The legacy mapping and payload digests were observed in immutable release
86d949a52f1691a424c20b25c46471d4e288ec53. Global rules deliberately retain
their existing component decomposition; whole-root mirrors exist in @ rules.
"""
from pathlib import Path
import csv, gc, gzip, hashlib, io, json, re, unittest
from test_tril_sfinks_alcion import visible, fragments

ROOT=Path(__file__).resolve().parent.parent
CSV='世界语词根-汉字对应列表_参照2新割当_7791.csv'
CURRENT={'fuz': '燃ᶠᶻ'}
LEGACY={'fuz': '信管'}
KEEPS={'fuel': '燃ᶠ', 'brul': '燃', 'fuzi': '聚变', 'stal': '畜棚', 'knedlik': '面团', 'dizel': '柴油', 'disel': '柴油ᴰˢ', 'semajn': '周'}
LEGACY_SHA={'JA':'215f0c297bf73efe29f4b323a982adb63a181d42e202dbed63f52c954baeb0fe',
            'ZH':'f05e779677489ebcf5d00b00389e841eb89cc8bf7af87bbf1d1e65309c0fd594',
            'KO':'8005ecf215185aa8fe9b8f482305f9fb1ec17aaf0d1c9c4fbbbb7928ef97508c'}
BASE_ROOTS={'fuz'}
BREAK=re.compile(r'<br\s*/?>',re.I)

def normalize(spelling):
    value=spelling.lower()
    for old,new in zip(('c^','g^','h^','j^','s^','u^'),'ĉĝĥĵŝŭ'):
        value=value.replace(old,new)
    return value

class FuzAssignment(unittest.TestCase):
    def test_manual_authority_and_retained_roots(self):
        for language in ('JA','ZH','KO'):
            data=ROOT/f'Esperanto-Kanji-Ruby-{language}/app_data'
            mapping={normalize(k):v for k,v in csv.reader(io.StringIO((data/CSV).read_text('utf-8')))}
            for root,glyph in {**CURRENT,**KEEPS}.items():
                self.assertEqual(mapping[root],glyph,(language,root))

    def test_global_component_and_local_whole_root_scopes_in_both_editions(self):
        for language in ('JA','ZH','KO'):
            for edition,values in (('current',CURRENT),('legacy',LEGACY)):
                if edition=='current':
                    raw=(ROOT/f'Esperanto-Kanji-Ruby-{language}/app_data/置換リスト_漢字.json').read_bytes()
                else:
                    compressed=(ROOT/f'assignment_editions/legacy/{language}/kanji.json.gz').read_bytes()
                    self.assertEqual(hashlib.sha256(compressed).hexdigest(),LEGACY_SHA[language])
                    raw=gzip.decompress(compressed)
                payload=json.loads(raw)
                for prefix in ('全域','局部'):
                    rows=payload[next(k for k in payload if k.startswith(prefix))]
                    seen=set()
                    for row in rows:
                        searchable=normalize(BREAK.sub('',row[1]))
                        if not any(root in searchable for root in values):continue
                        for spelling,glyph in fragments(row[1]):
                            root=normalize(spelling)
                            if root in values:
                                seen.add(root)
                                self.assertEqual(glyph,values[root],(language,edition,prefix,row[0],spelling))
                    self.assertEqual(seen,BASE_ROOTS if prefix=='全域' else set(values))
                    if prefix=='局部':
                        wanted={s for root in values for s in (root,root.title(),root.upper())}
                        table={r[0]:r[1] for r in rows if r[0] in wanted}
                        for root,glyph in values.items():
                            for spelling in (root,root.title(),root.upper()):
                                self.assertEqual(visible(table[spelling]),glyph)
                                self.assertEqual(fragments(table[spelling]),[(spelling,glyph)])
                del raw,payload,rows,table
                gc.collect()

if __name__=='__main__':unittest.main()
