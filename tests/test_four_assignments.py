"""Four approved root displays, unchanged neighbours, and fixed legacy rules.

Legacy values and gzip digests were measured in the immutable pre-change release
96b7f71fb120b7d1a6ece4862b2f3969a80ba2be, in both global and local scopes.
"""
from pathlib import Path
import csv
import gc
import gzip
import hashlib
import io
import json
import re
import unittest

from test_tril_sfinks_alcion import visible, fragments

ROOT=Path(__file__).resolve().parent.parent
CSV='世界语词根-汉字对应列表_参照2新割当_7791.csv'
CURRENT={'almenaŭ':'至少','forniks':'拱ᶠ','karen':'船底','naŭz':'恶心'}
LEGACY={'almenaŭ':'至ᴬ','forniks':'脑弓','karen':'龙骨ᴷᴿ','naŭz':'呕'}
KEEPS={'ŝagrin':'鲨皮','volb':'拱','kil':'龙骨','ĝis':'至','solstic':'至ˢ',
       'irigaci':'水渠','tandem':'串联','semajn':'周'}
LEGACY_SHA={
    'JA':'215f0c297bf73efe29f4b323a982adb63a181d42e202dbed63f52c954baeb0fe',
    'ZH':'f05e779677489ebcf5d00b00389e841eb89cc8bf7af87bbf1d1e65309c0fd594',
    'KO':'8005ecf215185aa8fe9b8f482305f9fb1ec17aaf0d1c9c4fbbbb7928ef97508c',
}
BREAK=re.compile(r'<br\s*/?>',re.I)

def normalize(spelling):
    value=spelling.lower()
    for old,new in zip(('c^','g^','h^','j^','s^','u^'),'ĉĝĥĵŝŭ'):
        value=value.replace(old,new)
    return value

class FourReviewedAssignments(unittest.TestCase):
    def test_manual_authority_and_retained_roots(self):
        for language in ('JA','ZH','KO'):
            data=ROOT/f'Esperanto-Kanji-Ruby-{language}/app_data'
            mapping=dict(csv.reader(io.StringIO((data/CSV).read_text('utf-8'))))
            for root,glyph in {**CURRENT,**KEEPS}.items():
                self.assertEqual(mapping[root],glyph,(language,root))

    def test_both_rule_scopes_in_both_editions(self):
        for language in ('JA','ZH','KO'):
            for edition,values in (('current',CURRENT),('legacy',LEGACY)):
                if edition=='current':
                    raw=(ROOT/f'Esperanto-Kanji-Ruby-{language}/app_data/置換リスト_漢字.json').read_bytes()
                else:
                    compressed=(ROOT/f'assignment_editions/legacy/{language}/kanji.json.gz').read_bytes()
                    self.assertEqual(hashlib.sha256(compressed).hexdigest(),LEGACY_SHA[language])
                    raw=gzip.decompress(compressed)
                payload=json.loads(raw)
                expected={**values,**KEEPS}
                for prefix in ('全域','局部'):
                    rows=payload[next(k for k in payload if k.startswith(prefix))]
                    seen=set()
                    for row in rows:
                        # Normalize markup only for filtering. Assertions read the
                        # original fragments, including wrapped ruby spellings.
                        searchable=normalize(BREAK.sub('',row[1]))
                        if not any(root in searchable for root in expected):continue
                        for spelling,glyph in fragments(row[1]):
                            root=normalize(spelling)
                            if root in expected:
                                seen.add(root)
                                self.assertEqual(glyph,expected[root],(language,edition,prefix,row[0],spelling))
                    self.assertEqual(seen,set(expected),(language,edition,prefix))
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
