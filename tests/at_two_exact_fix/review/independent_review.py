"""Independent exact-payload review using real engine/data and a Git baseline.

The expected result is constructed with existing separate @root@/@ant@ atoms,
not by calling the new repair helper. No application/data files are written.
Each language must run in a fresh process because app module names are shared.
"""
from pathlib import Path
import argparse, gc, hashlib, importlib.util, json, logging, re, subprocess, sys, types
from unittest.mock import patch

logging.disable(logging.WARNING)
ROOT = Path(__file__).resolve().parents[3]
BASELINE = '469806409ac3c3cc8f3368bdb24b792cead6f81c'
FORMATS = {'pure':'替换后文字列のみ(仅)保留(简单替换)', 'kanji':'HTML格式_Ruby文字_大小调整_汉字替换', 'ruby':'HTML格式_Ruby文字_大小调整'}
TARGETS = ('greganta', 'preganta')

def module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result
    spec.loader.exec_module(result);return result

def strip_ruby(text):
    return re.sub(r'</?ruby>','',re.sub(r'<rt[^>]*>.*?</rt>','',text,flags=re.S|re.I),flags=re.I)

def contexts():
    approved=[]; controls=[]
    for word in TARGETS:
        atom='@'+word[:-4]+'@@ant@%a%'
        for template in ('{}','({}),','{}!','{} {}','A: {};','{}-{}','x{}','{}x','3{}','{}3','ü{}','{}ü','{}n','k{}a','%PROTECTED% {}','{} %PROTECTED%'):
            approved.append((template.format('@'+word+'@','@'+word+'@'),template.format(atom,atom)))
        controls.extend([word,word.title(),word.upper(),'x'+word,word+'x',word+'j',word+'n',word+'jn',
                         '@'+word.title()+'@','@'+word.upper()+'@','@a'+word+'@','@'+word+'x@','@'+word+'j@','@'+word+'n@','@'+word+'jn@',
                         '@ '+word+' @','@'+word+' @','@ '+word+'@','@'+word+' '+word+'@',
                         '%@'+word+'@%','%'+word+'%','%'+word+' @'+word+'@%', '@'+word[:-1]+'@a',
                         '@'+word[:-4]+'@anta','@'+word[:-4]+'ant@a','@'+word+'',''+word+'@'])
    controls.extend(['kordonita','@kordonita@','@kordonitaj@','@kordonit@a','@kordon@ita','@greganta preganta@','@agreganta@',
        '@ greganta @','@gregantaj@','g@dominant@a','p@dominant@a','k@komandit@a','dominanta','komandita',
        'sene','@sene@','kseno','@kseno@','%kseno%','ksenulo','semajno','@semajno@','testikito','orkidita','@orkidita@',
        'spermatofitoj','lasis','@lasis@','%丸ᵀ炎ᵀ 丸ᴼ炎ᵀ 气胶ˢ 精子ˢᶻ%','%A < B & C > D%',
        '@kaj@','@ddt@','@fortran@','@racionalism@','@hokkajdon@','%@@%','%greganta% greganta','preganta %preganta%',
        'person@greganta.example','person@preganta.example','greganta@example.com','preganta@example.com'])
    return approved,controls

def check(language, report_path):
    app=ROOT/f'Esperanto-Kanji-Ruby-{language}';data=app/'app_data';sys.path.insert(0,str(app))
    import esp_text_replacement_module as engine
    import esp_assignment_edition as editions
    import esp_overlay_module as overlay
    before=types.ModuleType('at_two_baseline_'+language);before.__file__=str(app/'esp_text_replacement_module.py');sys.modules[before.__name__]=before
    old_code=subprocess.check_output(['git','show',f'{BASELINE}:Esperanto-Kanji-Ruby-{language}/esp_text_replacement_module.py'],cwd=ROOT).decode('utf8')
    exec(compile(old_code,before.__file__,'exec'),before.__dict__)
    inverse={};parsers={}
    for il,fn in [('JA','esperanto_converter.py'),('ZH','esperanto_converter_zh.py')]:
        im=module(ROOT/f'Esperanto-Reverter-{il}'/fn,'at_two_review_inverse_'+il)
        parsers[il]=module(ROOT/f'Esperanto-Reverter-{il}'/'html_source_recovery.py','at_two_review_html_'+il)
        for edition,sid in [('current','pejvo-piv-20260620'),('legacy','pre-las-20261017')]:
            inverse[edition,il]=(im,im.build_mapping_index_cached(im.effective_mapping_records(sid,im.load_dictionary_source(sid))))
    ps=engine.import_placeholders(str(data/'placeholders_skip.txt'));pl=engine.import_placeholders(str(data/'placeholders_localcapture.txt'))
    approved,controls=contexts();source='\n'.join([s for s,_ in approved]+controls)
    oracle_source='\n'.join([s for _,s in approved]+controls)
    correction_bytes=(data/'user_corrections.json').read_bytes();rows=[]

    def render(rt,text,lists,mode,edition,*,opt_in=False,manual=None,parallel=False,automatic=True):
        gg,gl,g2=lists;om='kanji' if mode=='pure' else mode
        stored=overlay.load_overlay_entries(str(data),om,edition)
        if mode=='pure':stored=[[a,strip_ruby(b),c] for a,b,c in stored]
        gg=overlay.merge_overlay(gg,stored)
        if manual:gg=overlay.merge_overlay(gg,manual)
        def run(rules):
            args=(text,ps,gl,pl,rules,g2,FORMATS[mode])
            kwargs={'reviewed_local_decompositions':True} if opt_in else {}
            return rt.parallel_process(text,2,*args[1:],**kwargs) if parallel else rt.orchestrate_comprehensive_esperanto_text_replacement(*args,**kwargs)
        first=run(gg)
        auto=overlay.auto_overlay_entries(first,str(data),om,edition) if automatic else []
        if mode=='pure':auto=[[a,strip_ruby(b),c] for a,b,c in auto]
        return run(overlay.merge_overlay(gg,auto)) if auto else first

    for edition in ('current','legacy'):
        for mode in ('pure','kanji','ruby'):
            lists=editions.load_lists(data,mode,edition)
            prior=render(before,source,lists,mode,edition)
            default=render(engine,source,lists,mode,edition)
            result=render(engine,source,lists,mode,edition,opt_in=True)
            expected=render(before,oracle_source,lists,mode,edition)
            assert default==prior,(language,edition,mode,'default API changed')
            assert result==expected,(language,edition,mode,'not equal to existing independently rendered root + ant + a atoms')
            # Some annotation text contains <br> itself; compare controls as a separate full batch.
            control_text='\n'.join(controls)
            assert render(engine,control_text,lists,mode,edition,opt_in=True)==render(before,control_text,lists,mode,edition)
            single=render(engine,'@greganta@ @preganta@ @kordonita@',lists,mode,edition,opt_in=True)
            row={'edition':edition,'mode':mode,'contexts':len(approved)+len(controls),'approved_contexts':len(approved),'unchanged_controls':len(controls),
                 'default_api_unchanged':True,'oracle_existing_atoms_match':True,'target_output':single,
                 'before_sha256':hashlib.sha256(prior.encode()).hexdigest(),'after_sha256':hashlib.sha256(result.encode()).hexdigest()}
            if mode=='pure':
                assert single=='群ᴳ在a 压ᴾᴳ在a 带ᴷ受a',single
                for il in ('JA','ZH'):
                    inv,index=inverse[edition,il]
                    assert inv.convert_kanji_esperanto_to_alphabet(single,index)=='greganta preganta kordonita'
                    old=render(before,control_text,lists,mode,edition)
                    new=render(engine,control_text,lists,mode,edition,opt_in=True)
                    assert inv.convert_kanji_esperanto_to_alphabet(new,index)==inv.convert_kanji_esperanto_to_alphabet(old,index)
                row['target_inverse_checks']=6;row['inverse_control_checks']=2*len(controls)
            else:
                document=engine.apply_ruby_html_header_and_footer(result,FORMATS[mode])
                old_doc=before.apply_ruby_html_header_and_footer(prior,FORMATS[mode])
                target_doc=engine.apply_ruby_html_header_and_footer(single,FORMATS[mode])
                for il,parser in parsers.items():
                    rm='annotation' if mode=='ruby' else 'kanji'
                    assert parser.recover_standard_html(document,rm)['text']==parser.recover_standard_html(old_doc,rm)['text']
                    assert parser.recover_standard_html(target_doc,rm)['text']=='greganta preganta kordonita'
                row['html_recovery_checks']=4
            # Worker path, including protected literals and untouched controls.
            parallel_text='@greganta@ @preganta@\n%@greganta@%\n@kordonita@\nsene kseno\ng@dominant@a'
            assert render(engine,parallel_text,lists,mode,edition,opt_in=True,parallel=True)==render(engine,parallel_text,lists,mode,edition,opt_in=True)
            row['parallel_matches']=True
            # A user's global manual overlay remains in force on normal text only.
            manual=[[w,'MANUAL'+str(i),f'${9000500+i}$'] for i,w in enumerate(TARGETS)]
            manual_text='greganta preganta\n@greganta@ @preganta@'
            actual_manual=render(engine,manual_text,lists,mode,edition,opt_in=True,manual=manual,automatic=False)
            expected_manual=render(before,'greganta preganta\n@greg@@ant@%a% @preg@@ant@%a%',lists,mode,edition,manual=manual,automatic=False)
            assert actual_manual==expected_manual,(edition,mode,'manual global overlay overwritten')
            row['manual_overlay_preserved']=True
            with patch.object(overlay,'load_overlay_entries',return_value=manual):
                stored_result=render(engine,manual_text,lists,mode,edition,opt_in=True,automatic=False)
                stored_expected=render(before,'greganta preganta\n@greg@@ant@%a% @preg@@ant@%a%',lists,mode,edition,automatic=False)
                assert stored_result==stored_expected,(edition,mode,'stored overlay overwritten')
            row['in_memory_stored_overlay_preserved']=True
            # Existing positional APIs and explicit False are equivalent, including custom lists.
            custom=([['greganta','CUSTOM-G','$9000600$'],['preganta','CUSTOM-P','$9000601$']],
                    [['greg','CUSTOM-ROOT-G','$9000602$'],['preg','CUSTOM-ROOT-P','$9000603$'],['ant','CUSTOM-ANT','$9000604$']],[])
            custom_args=('@greganta@ @preganta@\ngreganta preganta',ps,custom[1],pl,custom[0],custom[2],FORMATS[mode])
            custom_before=before.orchestrate_comprehensive_esperanto_text_replacement(*custom_args)
            assert engine.orchestrate_comprehensive_esperanto_text_replacement(*custom_args)==custom_before
            assert engine.orchestrate_comprehensive_esperanto_text_replacement(*custom_args,reviewed_local_decompositions=False)==custom_before
            assert engine.create_replacements_list_for_localized_replacement(custom_args[0],pl,custom[1],custom[0])==before.create_replacements_list_for_localized_replacement(custom_args[0],pl,custom[1],custom[0])
            row['custom_default_and_compatibility_checks']=3
            rows.append(row);print(language,edition,mode,'PASS',flush=True)
            del lists;editions._load_lists_cached.clear();gc.collect()
    assert (data/'user_corrections.json').read_bytes()==correction_bytes
    paths=[app/name for name in ('esp_text_replacement_module.py','esp_assignment_edition.py','main.py')]+list((app/'pages').glob('1_*.py'))
    hashes={path.relative_to(app).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report={'passed':True,'language':language,'baseline':BASELINE,'source_sha256':hashes,'method':'Actual engines/data and saved/automatic overlays; independent oracle uses old separate @greg@/@preg@ + @ant@ + protected a. No app/data writes.',
            'contexts':{'approved':[s for s,_ in approved],'controls':controls},'rows':rows,'saved_corrections_unchanged':True}
    report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--language',required=True);p.add_argument('--report',type=Path,required=True)
    a=p.parse_args();check(a.language,a.report)
