"""Bundled @stalagmit inflections preserve the unassigned independent root."""
from pathlib import Path
import gc,html,importlib.util,json,logging,re,sys,unittest
logging.disable(logging.WARNING)
ROOT=Path(__file__).resolve().parent.parent
BEFORE_ROOT=None
INVERSE_APP=None
REPORT_ROWS=[]
FORMATS={'pure':'替换后文字列のみ(仅)保留(简单替换)',
         'kanji':'HTML格式_Ruby文字_大小调整_汉字替换','ruby':'HTML格式_Ruby文字_大小调整'}
ENDINGS=('', 'o','oj','on','ojn','a','aj','an','ajn','e','en','i','as','is','os','us','u')
FORMS={form:(form[:9],form[9:]) for ending in ENDINGS for word in ('stalagmit'+ending,)
       for form in (word,word.capitalize(),word.upper())}
SKIP=['%901%','%902%'];CAPTURE=['@901@','@902@']
LOCAL=[['stal','STABLE','@1@'],['ag','ACT','@2@'],['mit','MYTH','@3@'],
       ['greg','GROUP','@4@'],['preg','PRESS','@5@'],['ant','ACTIVE','@6@']]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

def render(engine,text,enabled=True,local=LOCAL,global_rules=(),two=(),mode='pure'):
    return engine.orchestrate_comprehensive_esperanto_text_replacement(
        text,SKIP,local,CAPTURE,global_rules,two,FORMATS[mode],reviewed_local_decompositions=enabled)

def plain(value):
    return html.unescape(re.sub(r'<[^>]*>','',value)).replace('\xa0',' ')

def recovered(value,mode):
    if mode=='pure':return value
    value=re.sub(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',
                 lambda m:m[2] if mode=='kanji' else m[1],value,flags=re.S)
    return plain(value)

class StalagmitLocalFix(unittest.TestCase):
    def engine(self):
        app=ROOT/'Esperanto-Kanji-Ruby-JA'
        if str(app) not in sys.path:sys.path.insert(0,str(app))
        return load(app/'esp_text_replacement_module.py','esp_text_replacement_module')

    def test_complete_forms_local_gloss_and_unassigned_fallback(self):
        engine=self.engine()
        self.assertEqual(engine._REVIEWED_LOCAL_ATOMIC_FORMS,FORMS)
        self.assertEqual(set(engine._REVIEWED_LOCAL_DECOMPOSITIONS),{'greganta','preganta'})
        for word,(root,ending) in FORMS.items():
            self.assertEqual(render(engine,'@'+word+'@'),word)
            self.assertEqual(render(engine,'@'+root+'@'+ending),word)
            custom=LOCAL+[[root,'<ruby>'+root+'<rt>GLOSS</rt></ruby>','@7@']]
            before=repr(custom)
            self.assertEqual(render(engine,'@'+word+'@',local=custom),custom[-1][1]+ending)
            self.assertEqual(repr(custom),before)
        self.assertEqual(render(engine,'@greganta@ @preganta@'),'GROUPACTIVEa PRESSACTIVEa')
        self.assertEqual(engine._reviewed_local_atomic_renderings(['other'],None,True),{})
        self.assertEqual(engine._reviewed_local_atomic_renderings(['stalagmito'],None,False),{})
        for bad in (LOCAL+[['stalagmit','','@7@']],
                    LOCAL+[['stalagmit','ONE','@7@'],['stalagmit','TWO','@8@']]):
            with self.assertRaises(ValueError):render(engine,'@stalagmito@',local=bad)

    def test_boundaries_protection_custom_default_and_compatibility_api(self):
        engine=self.engine()
        controls=('stalagmito','@ stalagmito @','@stalagmito stalagmito@','@stalagmitojn!@',
                  '@stalagmiteto@','@stalagmitanto@','@malstalagmito@','@xstalagmito@',
                  '@stalagmitox@','@StAlAgMiTo@','%@stalagmito@%','@%stalagmito%@',
                  'stalagmito@example.com','@stal@','@ŝtal@','@stalaktit@','@kristal@')
        for text in controls:
            self.assertEqual(render(engine,text,True),render(engine,text,False),text)
        self.assertEqual(render(engine,'@stalagmito@',False),'STABLEACTMYTHo')
        self.assertEqual(engine.orchestrate_comprehensive_esperanto_text_replacement(
            '@stalagmito@',SKIP,LOCAL,CAPTURE,[],[],FORMATS['pure']),'STABLEACTMYTHo')
        self.assertEqual(render(engine,'@stalagmito@',False,[['stalagmito','CUSTOM','@1@']]),'CUSTOM')
        self.assertEqual(render(engine,'%stalagmito% @stalagmito@'),'stalagmito stalagmito')
        self.assertEqual(render(engine,'x@stalagmito@y'),'xstalagmitoy')
        self.assertEqual(render(engine,'@stalagmit@o @stalagmitoj@'),'stalagmito stalagmitoj')
        self.assertEqual(render(engine,'<@stalagmito@> & %@stalagmito@%',mode='kanji'),
                         '&lt;stalagmito&gt; &amp; @stalagmito@')
        rows=engine.create_replacements_list_for_localized_replacement(
            '@stalagmito@ @greganta@',CAPTURE,LOCAL,[],reviewed_local_decompositions=True)
        self.assertEqual([r[2] for r in rows],['stalagmito','GROUPACTIVEa'])
        for workers in (1,2):
            text='@stalagmito@\n@STALAGMITOJ@\n%@stalagmito@%\n@greganta@'
            actual=engine.parallel_process(text,workers,SKIP,LOCAL,CAPTURE,[],[],FORMATS['pure'],
                                           reviewed_local_decompositions=True)
            self.assertEqual(actual,render(engine,text))

    def test_bundled_editions_languages_modes_and_roundtrips(self):
        inverse_app=INVERSE_APP or ROOT/'Esperanto-Reverter-JA'
        recovery=load(inverse_app/'html_source_recovery.py','stalagmit_html_recovery')
        inverse=load(inverse_app/'esperanto_converter.py','stalagmit_inverse')
        indices={edition:inverse.build_mapping_index_cached(inverse.effective_mapping_records(
            key,inverse.load_dictionary_source(key))) for edition,key in
            (('current','pejvo-piv-20260620'),('legacy','pre-las-20261017'))}
        controls=['stalagmito','stalagmitoj','Stalagmito','STALAGMITO',
                  '@stal@o','@ŝtal@o','@stalaktit@o','@kristal@o',
                  '@malstalagmito@','@stalagmiteto@','@xstalagmito@','@stalagmitox@',
                  '@stalagmito kaj stalaktito@','@ stalagmito @','@stalagmito!@',
                  '%@stalagmito@%','stalagmito@example.com','@greganta@','@preganta@',
                  '@kordonita@','@semajn@o','knedliko','dizelo','diselo']
        for lang in ('JA','ZH','KO'):
            app=ROOT/f'Esperanto-Kanji-Ruby-{lang}';sys.path.insert(0,str(app))
            ed=load(app/'esp_assignment_edition.py','stalagmit_ed_'+lang)
            engine=load(app/'esp_text_replacement_module.py','stalagmit_rt_'+lang)
            before=load(BEFORE_ROOT/f'Esperanto-Kanji-Ruby-{lang}/esp_text_replacement_module.py',
                        'stalagmit_before_'+lang) if BEFORE_ROOT else None
            for edition in ('current','legacy'):
                for mode in FORMATS:
                    gg,gl,g2=ed.load_lists(app/'app_data',mode,edition)
                    atoms={k:v for k,v,_ in gl if k in {'stalagmit','Stalagmit','STALAGMIT'}}
                    if mode=='ruby':self.assertEqual(set(atoms),{'stalagmit','Stalagmit','STALAGMIT'})
                    inputs=['@'+word+'@' for word in FORMS]+controls
                    def batch(rt,words,enabled=True):
                        value=render(rt,' ◆ '.join(words),enabled,gl,gg,g2,mode)
                        parts=[piece.strip() for piece in value.split('◆')]
                        self.assertEqual(len(parts),len(words))
                        return dict(zip(words,parts))
                    outputs=batch(engine,inputs)
                    previous=batch(before,inputs) if before else {}
                    for word,(root,ending) in FORMS.items():
                        text='@'+word+'@';actual=outputs[text]
                        expected=atoms[root]+engine.safe_replace(ending,gl) if root in atoms else word
                        self.assertEqual(actual,expected,(lang,edition,mode,text))
                        self.assertNotIn('@',actual)
                        self.assertEqual(recovered(actual,mode),word)
                        # Plain inverse intentionally normalizes Latin case; HTML
                        # recovery preserves the exact original spelling below.
                        self.assertEqual(inverse.convert_kanji_esperanto_to_alphabet(word,indices[edition]),word.lower())
                        if mode!='pure':
                            document=engine.apply_ruby_html_header_and_footer(actual,FORMATS[mode])
                            self.assertEqual(recovery.recover_standard_html(document,
                                'annotation' if mode=='ruby' else 'kanji')['text'],word)
                        old=previous.get(text)
                        if mode=='ruby' and before:
                            self.assertEqual(actual,old,('Existing annotation changed',lang,edition,text))
                        REPORT_ROWS.append({'language':lang,'edition':edition,'mode':mode,'input':text,
                                            'before':old,'after':actual,'source':word,'kind':'approved_exact_form'})
                    for text in controls:
                        actual=outputs[text]
                        if before:
                            old=previous[text]
                            self.assertEqual(actual,old,(lang,edition,mode,text))
                            REPORT_ROWS.append({'language':lang,'edition':edition,'mode':mode,'input':text,
                                                'before':old,'after':actual,'kind':'unchanged_control'})
                    # Even the bundled bytes behave exactly as before when loaded as custom JSON.
                    if before:
                        custom_inputs=('@stalagmito@','@STALAGMITOJ@','@stalagmit@o')
                        custom=batch(engine,custom_inputs,False);old_custom=batch(before,custom_inputs,False)
                        for text in custom_inputs:
                            actual=custom[text];old=old_custom[text]
                            self.assertEqual(actual,old)
                            REPORT_ROWS.append({'language':lang,'edition':edition,'mode':mode,'input':text,
                                                'before':old,'after':actual,'kind':'custom_optout'})
                    ed._load_lists_cached.clear();del gg,gl,g2;gc.collect()
            sys.path.pop(0)

if __name__=='__main__':unittest.main(verbosity=2)
