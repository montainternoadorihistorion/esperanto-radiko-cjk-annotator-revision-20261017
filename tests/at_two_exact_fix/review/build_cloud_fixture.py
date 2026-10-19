"""Expected local results for Cloud comparison, never Cloud observations."""
from pathlib import Path
import gc, hashlib, importlib.util, json, logging, re, sys
logging.disable(logging.WARNING);sys.dont_write_bytecode=True
P=Path(__file__).resolve().parents[3]
TEXT='greganta preganta kordonita\n@greganta@ @preganta@ @kordonita@\n@agreganta@ @greganta preganta@ @ greganta @ @gregantaj@\ng@dominant@a p@dominant@a k@komandit@a\nsene kseno semajno testikito orkidita\n%@greganta@% %丸ᵀ炎ᵀ 丸ᴼ炎ᵀ 精子ˢᶻ%'
SUFFIX='\n%@literala@% %<b>&amp;</b>%\nĈapelo  fino\n'
EXPECTED='greganta preganta kordonita\ngreganta preganta kordonita\nagreganta greganta preganta  greganta  gregantaj\ngdominanta pdominanta kkomandita\nsene kseno semajno testikito orkidita\n@greganta@ 丸ᵀ炎ᵀ 丸ᴼ炎ᵀ 精子ˢᶻ\n@literala@ <b>&amp;</b>\nĈapelo  fino\n'
FORMATS={'pure':'替换后文字列のみ(仅)保留(简单替换)','kanji':'HTML格式_Ruby文字_大小调整_汉字替换','ruby':'HTML格式_Ruby文字_大小调整'}
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def strip(text):return re.sub(r'</?ruby>','',re.sub(r'<rt[^>]*>.*?</rt>','',text,flags=re.S))
inverse={};parsers={}
for lang,fn in [('JA','esperanto_converter.py'),('ZH','esperanto_converter_zh.py')]:
    im=module(P/f'Esperanto-Reverter-{lang}'/fn,'at_two_cloud_inverse_'+lang)
    parsers[lang]=module(P/f'Esperanto-Reverter-{lang}'/'html_source_recovery.py','at_two_cloud_html_'+lang)
    for edition,sid in [('current','pejvo-piv-20260620'),('legacy','pre-las-20261017')]:
        inverse[edition,lang]=(im,im.build_mapping_index_cached(im.effective_mapping_records(sid,im.load_dictionary_source(sid))))
rows=[]
for lang in ('JA','ZH','KO'):
    app=P/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
    ed=module(app/'esp_assignment_edition.py','at_two_cloud_ed_'+lang)
    rt=module(app/'esp_text_replacement_module.py','at_two_cloud_rt_'+lang)
    ov=module(app/'esp_overlay_module.py','at_two_cloud_ov_'+lang)
    ps=rt.import_placeholders(str(data/'placeholders_skip.txt'));pl=rt.import_placeholders(str(data/'placeholders_localcapture.txt'))
    for edition in ('current','legacy'):
        for mode in ('pure','kanji','ruby'):
            source=TEXT if mode=='pure' else TEXT+SUFFIX
            gg,gl,g2=ed.load_lists(data,mode,edition);om='kanji' if mode=='pure' else mode
            overlays=ov.load_overlay_entries(str(data),om,edition)
            if mode=='pure':overlays=[[a,strip(b),c] for a,b,c in overlays]
            gg=ov.merge_overlay(gg,overlays)
            def run(rules):return rt.orchestrate_comprehensive_esperanto_text_replacement(source,ps,gl,pl,rules,g2,FORMATS[mode],reviewed_local_decompositions=True)
            first=run(gg);auto=ov.auto_overlay_entries(first,str(data),om,edition)
            if mode=='pure':auto=[[a,strip(b),c] for a,b,c in auto]
            output=run(ov.merge_overlay(gg,auto)) if auto else first
            rendered=rt.apply_ruby_html_header_and_footer(output,FORMATS[mode])
            row={'forward_language':lang,'edition':edition,'mode':mode,'input':source,'raw_output':output,'rendered':rendered,
                 'rendered_sha256':hashlib.sha256(rendered.encode()).hexdigest(),'auto_rows':len(auto)}
            if mode=='pure':
                assert output.splitlines()[1]=='群ᴳ在a 压ᴾᴳ在a 带ᴷ受a',output
                row['plain_reverse_expected']={il:inv.convert_kanji_esperanto_to_alphabet(output,index) for il in ('JA','ZH') for inv,index in [inverse[edition,il]]}
            else:
                recovery_mode='annotation' if mode=='ruby' else 'kanji'
                recovered={il:m.recover_standard_html(rendered,recovery_mode)['text'] for il,m in parsers.items()}
                assert set(recovered.values())=={EXPECTED},(lang,edition,mode,recovered,EXPECTED)
                row['html_recovery_expected']=EXPECTED;row['html_recovery_mode']=recovery_mode
            rows.append(row);print(lang,edition,mode,flush=True)
            del gg,gl,g2;ed._load_lists_cached.clear();gc.collect()
result={'method':'Local production engines and full selected tables, saved/automatic overlays with reviewed local decomposition opt-in; actual JA/ZH inverse and HTML recovery APIs. Expected browser outputs, not Cloud observations.',
        'pure_input':TEXT,'html_input':TEXT+SUFFIX,'rows':rows}
(P/'tests/at_two_exact_fix/cloud_fixture.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('rows',len(rows),flush=True)
