"""Portable independent checks for component identifiers in whole-root displays."""
import argparse,csv,hashlib,importlib.util,io,json,re,unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;BASELINE=None
SCOPE_PATH=HERE/'reviewed_mirror_identifiers_20261017.json'
SCOPE_SHA256='d0b5dfc0c31fb35bbd27308b6841651c76987e0e6da222dd118771d92878f681'
scope_raw=SCOPE_PATH.read_bytes()
if hashlib.sha256(scope_raw).hexdigest()!=SCOPE_SHA256:raise ValueError('Test scope fingerprint changed')
SCOPE=json.loads(scope_raw)
spec=importlib.util.spec_from_file_location('mirror_test_helpers',HERE/'test_reviewed_at_sync.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
REPORT={'tables':[],'manual':[],'controls':[]}
def norm(root):
    root=root.lower()
    for a,b in zip(('c^','g^','h^','j^','s^','u^'),'ĉĝĥĵŝŭ'):root=root.replace(a,b)
    return root
VALUES={norm(r['root']):r for r in SCOPE['changes']}
# Current-value checks follow the later approved uve shortening. Keep the
# historical scope and its fingerprint unchanged, including the before value.
VALUES['uveit']={**VALUES['uveit'],'after':'葡膜炎ᵀ'}
# Later user-approved onk component propagates only to these two whole-root mirrors.
VALUES['onkogen']={**VALUES['onkogen'],'after':'瘤ᴼ生ᴳ'}
VALUES['onkologi']={**VALUES['onkologi'],'after':'瘤ᴼ学ᴸᴳ'}
# Later approved sozi/fobi revision changes only current mirror expectations.
# The fingerprinted historical scope and all original before values stay intact.
for _r,_v in {'agorafobi': '场ᴬ怕ᶠ', 'hidrofobi': '水ᴴ怕ᶠ', 'ksenofobi': '外ᴷˢ怕ᶠ', 'hidrofob': '水ᴴ怕ᶠᴼ', 'ksenofob': '外ᴷˢ怕ᶠᴼ', 'simptomologi': '症学ᴸᴳ'}.items():
    VALUES[_r]={**VALUES[_r],'after':_v}
# Previously approved microbial mirror; only the current expectation changes.
VALUES['mikrobologi']={**VALUES['mikrobologi'],'after':'微生物学ᴸᴳ'}
ABSENT=set(SCOPE.get('currently_absent_csv_roots',[]))
PRESERVED={(norm(r['root']),r['display']) for r in SCOPE.get('preserved_senses',[])}

# Later approved fraj annotations are the only changes to these historical
# mirror-guard files. Keep the old SCOPE and its fingerprint intact; pin both
# reviewed byte identities here instead of accepting hashes from current data.
# Full non-fraj comparisons: test_sutur_fraj_assignments.py and its regression
# report; independent frozen-baseline proof is recorded in the integrated repo
# at sutur_fraj_assignments_20261017/public_mirror_guard_fraj_delta_verification.json.
FRAJ_ANNOTATION_HASHES = {
    'Esperanto-Kanji-Ruby-JA/app_data/word_anno.json': ('6ce53f8b589aff7be20cb1c952974eab0054279e37566d6add1e891859d991d9', 'f07e289b475a13bd08c3f53aa6d6a3f8f010886d3a19d9ab345773133da96f6a'),
    'Esperanto-Kanji-Ruby-JA/app_data/エスペラント語根-日本語訳ルビ対応リスト.csv': ('33ce469efce8d77111c281df36585e981269409f1d33753da620d56c6ad5ce0e', '0c3b4d2dc71f2c458e2ed2d50caa33f6a4d6887cfddd732d9b1f8daa19073f4a'),
    'Esperanto-Kanji-Ruby-JA/app_data/世界语词根-中文注释对应列表.csv': ('908effbda970c0a54690c8c464e1f7a9905f67c40021fa290ce7ac41d73e4657', '71e31ab74e56c08ea4a13e27a233a1cb122686334ad87b290352d0597704a4b3'),
    'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_ルビ.json': ('daf095b589e04434ff5067e7d446c6d2f563aa13e4077f4b97f26037a01ae018', '097a0dc04fb7f3dcb1efb64975fae6fc6cf3580989743887fcef4bb6cb84c776'),
    'Esperanto-Kanji-Ruby-JA/app_data/에스페란토 어근-한국어 번역 루비 대응 목록.csv': ('b9f64f8594d757412c25d645c21180a4648294b7c4fac61b7926f1e875b0b9dd', '767d74f4fa5fe826484da9a0b70569399f2ac30b7335cc2a59a94c4f72756129'),
    'Esperanto-Kanji-Ruby-KO/app_data/word_anno.json': ('8d2664e4e926a2260e3e0c3a15b0adac76ab1dcb3d120131fcaa145028c56f18', 'f21832d98283ff917fe23776c652f78f76e4e09d377c2464caab7e5d62e31e49'),
    'Esperanto-Kanji-Ruby-KO/app_data/世界语词根-中文注释对应列表.csv': ('908effbda970c0a54690c8c464e1f7a9905f67c40021fa290ce7ac41d73e4657', '71e31ab74e56c08ea4a13e27a233a1cb122686334ad87b290352d0597704a4b3'),
    'Esperanto-Kanji-Ruby-KO/app_data/置換リスト_ルビ.json': ('e4e03fa2608ebd30644fba2d113b43f5938b05a5262d4be8883d3d14a04ab921', '78ba62b0c77186cd113fbedc9bb51890b425c177aff715fcc7754ec306e24354'),
    'Esperanto-Kanji-Ruby-KO/app_data/에스페란토 어근-한국어 번역 루비 대응 목록.csv': ('a5a2ba458907d5b6a3512bd7fe5d6a9c7bb6d6a84a1b23dc6652a32a0fb9866e', '56783ebb5a1a0ce5782e213c0509eaf44e7a37a235a2060a36447adf8b9a1986'),
    'Esperanto-Kanji-Ruby-ZH/app_data/word_anno.json': ('7ca2a850f7f9a71552145912368921bb7bea75fe4367909668ac46f21f452837', '3dae711b271bfbe17ef0666e1b420f2ab5cc88fd40042110f92b3622d967bf57'),
    'Esperanto-Kanji-Ruby-ZH/app_data/世界语词根-中文注释对应列表.csv': ('6b8255b364f8d7d8d76a8d32fc4b1f931e24dc2d8accaebfa244107814c723ac', '7cbd98b2fb545d6d6d3eede4d401862cb10a9d89dbf535ae6f28bdc14ef2f673'),
    'Esperanto-Kanji-Ruby-ZH/app_data/置換リスト_ルビ.json': ('fb524e3401700f5e8ecba705502c34e1cd37cfe7d93505474f4e9c3e9b887e83', 'a313d4ba8c3b60d750c034976d665ccf64fbe97705ded0dcdc4d5ab7e508c84f'),
}
assert set(FRAJ_ANNOTATION_HASHES) <= set(SCOPE['unchanged_app_data_sha256'])

# Exact complete-root gloss deltas proved by test_nostalgi_onk_fortres_assignments.py.
# Each pair is the already-reviewed fraj identity and the subsequent 3-root identity.
# Preserve SCOPE and the previous FRAJ layer unchanged.
NOF_ANNOTATION_HASHES = {'Esperanto-Kanji-Ruby-JA/app_data/word_anno.json': ('f07e289b475a13bd08c3f53aa6d6a3f8f010886d3a19d9ab345773133da96f6a', 'dadf4aeaffb802dc7db56be0ce881925682325902f572d21c2ef30a8dd89bca0'), 'Esperanto-Kanji-Ruby-JA/app_data/エスペラント語根-日本語訳ルビ対応リスト.csv': ('0c3b4d2dc71f2c458e2ed2d50caa33f6a4d6887cfddd732d9b1f8daa19073f4a', 'bd5191da078d6a8923269c81f896a1a3e074cf10c4e94e35326e51a2d4b7746a'), 'Esperanto-Kanji-Ruby-JA/app_data/世界语词根-中文注释对应列表.csv': ('71e31ab74e56c08ea4a13e27a233a1cb122686334ad87b290352d0597704a4b3', 'e6c09e35a6b6da19c7caf2e4ae56ddb2c0e39f74b6d17df2e4f329f7d5640c0b'), 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_ルビ.json': ('097a0dc04fb7f3dcb1efb64975fae6fc6cf3580989743887fcef4bb6cb84c776', '753a0d02b7193a3254572a65d92fefa765013f952a0d3b251f1baf3d97a8ae02'), 'Esperanto-Kanji-Ruby-JA/app_data/에스페란토 어근-한국어 번역 루비 대응 목록.csv': ('767d74f4fa5fe826484da9a0b70569399f2ac30b7335cc2a59a94c4f72756129', 'a45f48c48be3b117dc41ebe0af93bbda29668ceb4a956fc19b7683acbee9d1a6'), 'Esperanto-Kanji-Ruby-KO/app_data/word_anno.json': ('f21832d98283ff917fe23776c652f78f76e4e09d377c2464caab7e5d62e31e49', 'd4cd11a060b4b942421782db53437d182d0c45aaf474fa9d55ec0b5db9c10653'), 'Esperanto-Kanji-Ruby-KO/app_data/世界语词根-中文注释对应列表.csv': ('71e31ab74e56c08ea4a13e27a233a1cb122686334ad87b290352d0597704a4b3', 'e6c09e35a6b6da19c7caf2e4ae56ddb2c0e39f74b6d17df2e4f329f7d5640c0b'), 'Esperanto-Kanji-Ruby-KO/app_data/置換リスト_ルビ.json': ('78ba62b0c77186cd113fbedc9bb51890b425c177aff715fcc7754ec306e24354', '7989cabe3bee5e1365fa5eaa48d20bd3e8b40638a7fb07d6e6fd6e32c732d0a8'), 'Esperanto-Kanji-Ruby-KO/app_data/에스페란토 어근-한국어 번역 루비 대응 목록.csv': ('56783ebb5a1a0ce5782e213c0509eaf44e7a37a235a2060a36447adf8b9a1986', 'cfc7ddd482b89b78b1b0d8e859bee59b48068851ce1927be95b3290556c840af'), 'Esperanto-Kanji-Ruby-ZH/app_data/word_anno.json': ('3dae711b271bfbe17ef0666e1b420f2ab5cc88fd40042110f92b3622d967bf57', '03b7563e8dbd00a5e760b46670aab0f9b3099927a77a1d9f1dedaf15ce9e3489'), 'Esperanto-Kanji-Ruby-ZH/app_data/世界语词根-中文注释对应列表.csv': ('7cbd98b2fb545d6d6d3eede4d401862cb10a9d89dbf535ae6f28bdc14ef2f673', 'd03ea98938820a14ded0eea0291b88c9e10191707981471e9b5ea9f40e92c184'), 'Esperanto-Kanji-Ruby-ZH/app_data/置換リスト_ルビ.json': ('a313d4ba8c3b60d750c034976d665ccf64fbe97705ded0dcdc4d5ab7e508c84f', 'bb2aa68b3e0f06610197862101ebd57a6a6d6f6f4093fb4b8a3ede0ece0feebd')}
assert set(NOF_ANNOTATION_HASHES) == set(FRAJ_ANNOTATION_HASHES)

# Exact current annotation delta is independently checked in test_sperm_distinction.
SPERM_ANNOTATION_HASHES = {'Esperanto-Kanji-Ruby-JA/app_data/word_anno.json': ('dadf4aeaffb802dc7db56be0ce881925682325902f572d21c2ef30a8dd89bca0', 'f618d16b431e6076f8a3a5c3e2db748acd4a7935b42ec1368be15130cfb3aa00'), 'Esperanto-Kanji-Ruby-JA/app_data/エスペラント語根-日本語訳ルビ対応リスト.csv': ('bd5191da078d6a8923269c81f896a1a3e074cf10c4e94e35326e51a2d4b7746a', 'c7a0357f5c778f1bfb331c0b53cff1e8b45e3674b14c973a57353e990e818738'), 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_ルビ.json': ('753a0d02b7193a3254572a65d92fefa765013f952a0d3b251f1baf3d97a8ae02', '87899aa835f0e2e35884cc6d356947656e403cd3f893530f7ad637af73180879'), 'Esperanto-Kanji-Ruby-KO/app_data/word_anno.json': ('d4cd11a060b4b942421782db53437d182d0c45aaf474fa9d55ec0b5db9c10653', 'c0b1fb5915099c14dc9bff98d05212aac16f26669fcbc653bbc578318e357cf9'), 'Esperanto-Kanji-Ruby-KO/app_data/置換リスト_ルビ.json': ('7989cabe3bee5e1365fa5eaa48d20bd3e8b40638a7fb07d6e6fd6e32c732d0a8', 'e132e8e772c8eddbd5d10e04dad4893f7ca59d35f8bdd5e3e9d2634141307110'), 'Esperanto-Kanji-Ruby-KO/app_data/에스페란토 어근-한국어 번역 루비 대응 목록.csv': ('cfc7ddd482b89b78b1b0d8e859bee59b48068851ce1927be95b3290556c840af', '4abae9f5baf529a7131c20d6136724fad276b59b20069c6625b35231ebc74372'), 'Esperanto-Kanji-Ruby-ZH/app_data/word_anno.json': ('03b7563e8dbd00a5e760b46670aab0f9b3099927a77a1d9f1dedaf15ce9e3489', 'e2f202ff4cdde4e8470999cfb1abce988324066629dc7d69829aa2db9194012b'), 'Esperanto-Kanji-Ruby-ZH/app_data/世界语词根-中文注释对应列表.csv': ('d03ea98938820a14ded0eea0291b88c9e10191707981471e9b5ea9f40e92c184', 'ee5a67c89525e32521422b6ed7d9ab81aafb4eaca744e1a00c2db21aa55e59ff'), 'Esperanto-Kanji-Ruby-ZH/app_data/置換リスト_ルビ.json': ('bb2aa68b3e0f06610197862101ebd57a6a6d6f6f4093fb4b8a3ede0ece0feebd', '24dd6b3a866dbf1f6918815cdb6aa3cdb37bc5c5a4a6dd18b0e5421936d7bbb5')}
assert set(SPERM_ANNOTATION_HASHES) <= set(NOF_ANNOTATION_HASHES)
for _r,_v in {'spermatocit': '精子胞ᶜᴵ', 'spermatofit': '精子植ᶠ', 'spermatogenez': '精子源ᴳ'}.items():VALUES[_r]={**VALUES[_r],'after':_v}

# Strict current-byte chain; full non-target proof is test_dot_greft.
DOT_GREFT_ANNOTATION_HASHES = {'Esperanto-Kanji-Ruby-JA/app_data/word_anno.json': ('f618d16b431e6076f8a3a5c3e2db748acd4a7935b42ec1368be15130cfb3aa00', '7377498c0e03cbc7a2c4847423a35a11174b028e6cad1d4d9eb169233342c5f7'), 'Esperanto-Kanji-Ruby-JA/app_data/エスペラント語根-日本語訳ルビ対応リスト.csv': ('c7a0357f5c778f1bfb331c0b53cff1e8b45e3674b14c973a57353e990e818738', '9ca45ed392676dbc82a4e0a3c415da6aa436a12ce6f661297c6848640eb0812d'), 'Esperanto-Kanji-Ruby-JA/app_data/世界语词根-中文注释对应列表.csv': ('e6c09e35a6b6da19c7caf2e4ae56ddb2c0e39f74b6d17df2e4f329f7d5640c0b', '837ecfed98cbb61c469d1c60d84d339a95286358880c5df93024bb908e804c6a'), 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_ルビ.json': ('87899aa835f0e2e35884cc6d356947656e403cd3f893530f7ad637af73180879', 'd02fd6ef33ab2da0d59e3e170f152e219d289de39e0bf358e05f6384bc292dca'), 'Esperanto-Kanji-Ruby-JA/app_data/에스페란토 어근-한국어 번역 루비 대응 목록.csv': ('a45f48c48be3b117dc41ebe0af93bbda29668ceb4a956fc19b7683acbee9d1a6', '015eb5968a673a950c8454a7b316dc6bbd086fec4a4d3963645e9aed77cc05a4'), 'Esperanto-Kanji-Ruby-ZH/app_data/word_anno.json': ('e2f202ff4cdde4e8470999cfb1abce988324066629dc7d69829aa2db9194012b', 'c469442ac632c00ba4d4d14112617a9133d7e13b26ae3b53bc0df59676226a3d'), 'Esperanto-Kanji-Ruby-ZH/app_data/世界语词根-中文注释对应列表.csv': ('ee5a67c89525e32521422b6ed7d9ab81aafb4eaca744e1a00c2db21aa55e59ff', 'f98beb1f6e096936850a479cf10a9563df5b815b4970d5959d356e47a3b83f2c'), 'Esperanto-Kanji-Ruby-ZH/app_data/置換リスト_ルビ.json': ('24dd6b3a866dbf1f6918815cdb6aa3cdb37bc5c5a4a6dd18b0e5421936d7bbb5', 'a20a2d89b4f9f44a7be82a6a18ee94858a74ea205988f49b0e7c05c2c138e4de'), 'Esperanto-Kanji-Ruby-KO/app_data/word_anno.json': ('c0b1fb5915099c14dc9bff98d05212aac16f26669fcbc653bbc578318e357cf9', '544b2998afb59b9da6d907b17afe69a616005a235383dd0473a8038b755e64ef'), 'Esperanto-Kanji-Ruby-KO/app_data/世界语词根-中文注释对应列表.csv': ('e6c09e35a6b6da19c7caf2e4ae56ddb2c0e39f74b6d17df2e4f329f7d5640c0b', '837ecfed98cbb61c469d1c60d84d339a95286358880c5df93024bb908e804c6a'), 'Esperanto-Kanji-Ruby-KO/app_data/置換リスト_ルビ.json': ('e132e8e772c8eddbd5d10e04dad4893f7ca59d35f8bdd5e3e9d2634141307110', '1a5a36d92494308458e40ec41f16c44de8d02d7e6b7eb2c2bfe5ebcd10157e8c'), 'Esperanto-Kanji-Ruby-KO/app_data/에스페란토 어근-한국어 번역 루비 대응 목록.csv': ('4abae9f5baf529a7131c20d6136724fad276b59b20069c6625b35231ebc74372', '5a868c02499ae7447710dac0d894542aacb2303cec125cc53978d280f5e172ab')}

def neutral(value,phase,context):
    def visit(m):
        root=norm(h.plain(m[2]));display=m[1]
        if root not in VALUES:return m[0]
        if display==VALUES[root][phase]:return '<mirror>'+h.plain(m[2])+'</mirror>'
        for rule in SCOPE.get('word_scoped_changes',[]):
            if norm(rule['root'])==root and display==rule[phase] and any(re.fullmatch(p,norm(context.replace('/','').strip())) for p in rule['context_patterns']):
                return '<mirror>'+h.plain(m[2])+'</mirror>'
        if (root,display) in PRESERVED:return m[0]
        raise AssertionError((root,display,phase,context))
    return h.RUBY.sub(visit,value)

class MirrorTests(unittest.TestCase):
    def test_all_rows_and_csv(self):
        for lang in ('JA','ZH','KO'):
            data=ROOT/f'Esperanto-Kanji-Ruby-{lang}'/'app_data';path=data/h.MODES['kanji'][0]
            current=json.loads(path.read_bytes());old=json.loads(h.baseline_bytes(path)) if BASELINE else None
            groups={}
            for group,rows in current.items():
                changed=0
                if old:self.assertEqual(len(rows),len(old[group]))
                for i,row in enumerate(rows):
                    n=neutral(row[1],'after',row[0])
                    if old:
                        before=old[group][i]
                        self.assertEqual(before[:1]+before[2:],row[:1]+row[2:])
                        self.assertEqual(neutral(before[1],'before',before[0]),n)
                        self.assertEqual(h.original(before[1],'kanji'),h.original(row[1],'kanji'))
                        changed+=before!=row
                groups[group]={'rows':len(rows),'changed':changed}
            raw=(data/h.CSV_NAME).read_bytes();mapping=dict(csv.reader(io.StringIO(raw.decode('utf-8'))))
            for root,row in VALUES.items():
                if root in ABSENT:self.assertNotIn(root,mapping)
                else:self.assertEqual(mapping[root],row['after'])
            if BASELINE:
                oldraw=h.baseline_bytes(data/h.CSV_NAME).decode('utf-8');newlines=[]
                for line in oldraw.splitlines(keepends=True):
                    body=line.rstrip('\r\n');ending=line[len(body):];parts=next(csv.reader([body]),[])
                    if parts and norm(parts[0]) in VALUES:
                        expected=VALUES[norm(parts[0])];self.assertEqual(parts[1],expected['before'])
                        line=parts[0]+','+expected['after']+ending
                    newlines.append(line)
                self.assertEqual(raw,''.join(newlines).encode('utf-8'))
                anno=data/h.MODES['ruby'][0];self.assertEqual(anno.read_bytes(),h.baseline_bytes(anno))
            for rel,expected in SCOPE['unchanged_app_data_sha256'].items():
                if rel.startswith(f'Esperanto-Kanji-Ruby-{lang}/'):
                    if rel in FRAJ_ANNOTATION_HASHES:
                        historical, current_expected = FRAJ_ANNOTATION_HASHES[rel]
                        self.assertEqual(expected, historical, rel)
                        expected = current_expected
                    if rel in NOF_ANNOTATION_HASHES:
                        prior_expected, current_expected = NOF_ANNOTATION_HASHES[rel]
                        self.assertEqual(expected, prior_expected, rel)
                        expected = current_expected
                    if rel in SPERM_ANNOTATION_HASHES:
                        prior_expected,current_expected=SPERM_ANNOTATION_HASHES[rel]
                        self.assertEqual(expected,prior_expected,rel)
                        expected=current_expected
                    if rel in DOT_GREFT_ANNOTATION_HASHES:
                        prior_expected,current_expected=DOT_GREFT_ANNOTATION_HASHES[rel]
                        self.assertEqual(expected,prior_expected,rel)
                        expected=current_expected
                    self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),expected,rel)
            if lang=='JA':
                pure=json.loads((data/h.MODES['pure'][0]).read_bytes())
                for group,rows in current.items():self.assertEqual(pure[group],[[r[0],h.strip_ruby(r[1]),*r[2:]] for r in rows])
                del pure
            REPORT['tables'].append({'language':lang,'groups':groups,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            del current,old

    def test_all_manual_generation_and_nine_paths(self):
        roots=sorted(VALUES.keys()-ABSENT)
        controls=['testikito','@testikit@o','orkidito','@orkidit@o','@testikito@','@TESTIKIT@O',
                  'testikitoj','testikiton','testikitojn','Testikito','TESTIKITO','orkidektomio','orkidoterapio',
                  'paniklito','alkoholato','@alkoholat@o','salpingito','@salpingit@o','otosalpingito','@otosalpingit@o',
                  'fotografio','@fotografi@o','milio','@mili@o','@piroz@o','pirozo','@riboz@o','ribozo',
                  'lasi','emancipi','ananaso','jakvo','prioritato','struto','sinergio','olivo','ovalo','elipso',
                  'semajntagoj','@semajn@tagoj','ŝakisto','%testikito%','@testikit@o & %amiko%']
        expected={'testikito':'丸ᵀ炎ᵀo','@testikit@o':'丸ᵀ炎ᵀo','orkidito':'丸ᴼ炎ᵀo','@orkidit@o':'丸ᴼ炎ᵀo',
                  '@testikito@':'丸ᵀ炎ᵀo','@TESTIKIT@O':'丸ᵀ炎ᵀO','testikitoj':'丸ᵀ炎ᵀoj','testikiton':'丸ᵀ炎ᵀon',
                  'testikitojn':'丸ᵀ炎ᵀojn','Testikito':'丸ᵀ炎ᵀo','TESTIKITO':'丸ᵀ炎ᵀO',
                  'orkidektomio':'丸ᴼ除ᴱᴷo','orkidoterapio':'丸ᴼo疗o','paniklito':'脂ᴾ炎ᵀo',
                  'alkoholato':'醇盐ᴬo','@alkoholat@o':'醇盐ᴬo','salpingito':'卵管炎ᵀo','@salpingit@o':'卵管炎ᵀo',
                  'otosalpingito':'耳ᴼᵀo管ˢ炎ᵀo','@otosalpingit@o':'待o卵管炎ᵀo',
                  'milio':'粟ᴹo','@mili@o':'毫o','@piroz@o':'梨富ᴼo','pirozo':'火ᴾ症ᴼo','@riboz@o':'醋栗富ᴼo','ribozo':'核ᴿ糖ᴼo',
                  'lasi':'放i','emancipi':'放ᴱi','ananaso':'菠o','jakvo':'菠蜜o','prioritato':'优先o','struto':'鸵o',
                  'sinergio':'协同o','olivo':'榄o','ovalo':'椭圆o','elipso':'椭圆ᴱo','semajntagoj':'周日oj',
                  '@semajn@tagoj':'周日oj','ŝakisto':'棋家o','%testikito%':'testikito','@testikit@o & %amiko%':'丸ᵀ炎ᵀo & amiko'}
        for lang in ('JA','ZH','KO'):
            app=ROOT/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
            runtime=h.load_module(app,'esp_text_replacement_module.py','mirror_runtime_'+lang)
            overlay=h.load_module(app,'esp_overlay_module.py','mirror_overlay_'+lang)
            corrections=[overlay.build_correction(root+'/o',str(data)) for root in roots]
            for mode,(filename,fmt) in h.MODES.items():
                owner=ROOT/'Esperanto-Kanji-Ruby-JA/app_data' if mode=='pure' else data
                payload=json.loads((owner/filename).read_bytes());key='ruby' if mode=='ruby' else 'kanji'
                user=overlay.load_overlay_entries(str(data),key)
                if mode=='pure':user=[[a,h.strip_ruby(b),c] for a,b,c in user]
                payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],user)
                first=h.render(runtime,data,payload,controls,fmt)
                auto=overlay.auto_overlay_entries(' ◆ '.join(first.values()),str(data),key)
                if mode=='pure':auto=[[a,h.strip_ruby(b),c] for a,b,c in auto]
                if auto:
                    payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],auto);final=h.render(runtime,data,payload,controls,fmt)
                else:final=first
                for word,value in final.items():
                    if mode!='ruby' and word in expected:self.assertEqual(h.visible(value),expected[word],word)
                    if mode!='pure':self.assertEqual(h.original(value,mode),word.replace('@','').replace('%',''))
                    REPORT['controls'].append({'language':lang,'mode':mode,'input':word,'first':first[word],'final':value})
                pairs=[p for correction in corrections for p in correction[key]]
                desired={w:h.strip_ruby(v) if mode=='pure' else v for w,v in pairs}
                # Every generated correction is checked, including all case variants.
                for word,value in desired.items():
                    if mode!='ruby':self.assertEqual(h.visible(value),VALUES[norm(word[:-1])]['after']+word[-1])
                    if mode!='pure':self.assertEqual(h.original(value,mode),word)
                # Thousands of simultaneous session corrections exercise the
                # existing quadratic merge cost, unrelated to this data change.
                # Real full-runtime integration covers the competing whole roots,
                # alternate sense, missing-i variants and preserved split examples.
                representatives=set(roots[:3]+roots[-3:])|{'testikit','orkidit','alkoholat','salpingit',
                    'metapsiki','pedofili','polifoni','polipodi','kseroftalmi','fotografi','endoskop','mikroskop','dodekaedr','telefoni'}
                probes={w:v for w,v in desired.items() if norm(w[:-1]) in representatives}
                payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],[[w,v,f'${93000000+i}$'] for i,(w,v) in enumerate(probes.items())])
                actual=h.render(runtime,data,payload,list(probes),fmt)
                self.assertEqual(actual,probes)
                REPORT['manual'].append({'language':lang,'mode':mode,'generated_roots':len(roots),'generated_forms':len(desired),'runtime_forms':len(actual),'passed':True})
                print('manual',lang,mode,len(desired),'generated,',len(actual),'runtime',flush=True)
                del payload

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--app-root',type=Path);parser.add_argument('--baseline-ref')
    parser.add_argument('--report',type=Path);selection=parser.add_mutually_exclusive_group()
    selection.add_argument('--runtime-only',action='store_true');selection.add_argument('--tables-only',action='store_true');args=parser.parse_args()
    ROOT=args.app_root.resolve() if args.app_root else ROOT;BASELINE=args.baseline_ref;h.ROOT=ROOT;h.BASELINE=BASELINE
    suite=(unittest.TestSuite([MirrorTests('test_all_manual_generation_and_nine_paths')]) if args.runtime_only else
           unittest.TestSuite([MirrorTests('test_all_rows_and_csv')]) if args.tables_only else unittest.defaultTestLoader.loadTestsFromTestCase(MirrorTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if args.report:args.report.write_text(json.dumps({'passed':result.wasSuccessful(),'scope_sha256':SCOPE_SHA256,**REPORT},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
