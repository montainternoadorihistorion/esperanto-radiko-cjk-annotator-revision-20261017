"""Approved madz and tribord displays, unchanged neighbours, and fixed legacy rules.

Legacy values and gzip digests were measured in the immutable pre-change release
001b71faa665df1282f379c2dafbbd514bd5a59d, in both global and local scopes.
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
CURRENT={'madz':'棍ᴹ','tribord':'船右'}
LEGACY={'madz':'钉头锤','tribord':'右边'}
KEEPS={'proces':'程ᴾᶜ','procez':'程ᴾᶻ','klab':'棍','babord':'船左','semajn':'周'}
LEGACY_SHA={
    'JA':'6eb499e70b3b9d4de661665043f2bc0b5dfd7c61969ff5de907592500f3414be',
    'ZH':'9f5fc98b84d696bab738c80bba4a25499e5b140be01a9cb91b11bf6422868ed1',
    'KO':'04f7120578bef8d14862306a768527e0807e277e094bf4fbf7e8d32b6d697b22',
}
BREAK=re.compile(r'<br\s*/?>',re.I)

def normalize(spelling):
    value=spelling.lower()
    for old,new in zip(('c^','g^','h^','j^','s^','u^'),'ĉĝĥĵŝŭ'):
        value=value.replace(old,new)
    return value

class MadzTribordAssignment(unittest.TestCase):
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
