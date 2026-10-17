"""Make a small public fixture from the final runtime plus default/auto overlays."""
import argparse, gc, hashlib, html, importlib.util, json, re
from pathlib import Path
GLOBAL='全域替换用のリスト(列表)型配列(replacements_final_list)'
LOCAL='局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)'
TWO='二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)'
MODES={'ruby':('置換リスト_ルビ.json','HTML格式_Ruby文字_大小调整'),
       'kanji':('置換リスト_漢字.json','HTML格式_Ruby文字_大小调整_汉字替换'),
       'pure':('置換リスト_漢字_純粋置換.json','替换后文字列のみ(仅)保留(简单替换)')}
RUBY=re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',re.S)
def strip_ruby(x):return re.sub(r'<rt[^>]*>.*?</rt>','',x,flags=re.S).replace('<ruby>','').replace('</ruby>','')
def module(path,key):
    spec=importlib.util.spec_from_file_location(key,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


SOURCE = 'uveo @uve@o uveito @uveit@o uveoj uveitojn Uveo Uveito uvo @uv@o vito psitako limono limonado konkordo stafilokoko testikito orkidito @testikit@o @orkidit@o @semajn@tagoj & %amiko% ŝakisto'

def text(value):
    value=re.sub(r'<br\s*/?>\r?\n?','\n',value)
    return html.unescape(re.sub('<[^>]*>','',value)).replace('\xa0',' ')
def ruby_text(value,which):
    def replace(m):return re.sub(r'<br\s*/?>','',m[which])
    return text(RUBY.sub(replace,value))
def main():
    p=argparse.ArgumentParser();p.add_argument('--app-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    cases=[]
    for lang in ('JA','ZH','KO'):
        app=a.app_root/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
        runtime=module(app/'esp_text_replacement_module.py','cloud_runtime_'+lang)
        overlay=module(app/'esp_overlay_module.py','cloud_overlay_'+lang)
        kanji=None
        for mode,(filename,fmt) in MODES.items():
            owner=a.app_root/'Esperanto-Kanji-Ruby-JA/app_data' if mode=='pure' else data
            raw=(owner/filename).read_bytes();payload=json.loads(raw);key='ruby' if mode=='ruby' else 'kanji'
            user=overlay.load_overlay_entries(str(data),key)
            if mode=='pure':user=[[w,strip_ruby(v),n] for w,v,n in user]
            payload[GLOBAL]=overlay.merge_overlay(payload[GLOBAL],user)
            def run():return runtime.orchestrate_comprehensive_esperanto_text_replacement(SOURCE,runtime.import_placeholders(str(data/'placeholders_skip.txt')),payload[LOCAL],runtime.import_placeholders(str(data/'placeholders_localcapture.txt')),payload[GLOBAL],payload[TWO],fmt)
            first=run();auto=overlay.auto_overlay_entries(first,str(data),key)
            if mode=='pure':auto=[[w,strip_ruby(v),n] for w,v,n in auto]
            if auto:payload[GLOBAL]=overlay.merge_overlay(payload[GLOBAL],auto)
            final=run() if auto else first
            visible=ruby_text(final,1) if mode!='pure' else final
            restored=ruby_text(final,2 if mode=='kanji' else 1) if mode!='pure' else kanji['restored_text']
            assert restored==SOURCE.replace('@','').replace('%',''),(lang,mode,restored)
            if mode=='pure':assert visible==kanji['visible']
            case={'language':lang,'mode':mode,'input':SOURCE,'first':first,'output':final,'visible':visible,'restored_text':restored,
                  'restoration_method':'source spelling from ruby' if mode!='pure' else 'matching Kanji ruby source; pure output equality checked (not reverse-dictionary reconstruction)',
                  'source_json_sha256':hashlib.sha256(raw).hexdigest(),'runtime_sha256':hashlib.sha256((app/'esp_text_replacement_module.py').read_bytes()).hexdigest(),'overlay_sha256':hashlib.sha256((app/'esp_overlay_module.py').read_bytes()).hexdigest(),'auto_overlay_entries':len(auto)}
            cases.append(case)
            if mode=='kanji':kanji=case
            print(lang,mode,flush=True);del payload;gc.collect()
    a.output.write_text(json.dumps({'schema_version':1,'method':'Local current application runtime plus default and automatic correction overlays; not a browser execution','input':SOURCE,'cases':cases,
        'limitations':['Annotation data and existing forced local decompositions are unchanged. Local annotation mode may retain medical it as passive perfect. These annotation meanings were not newly reviewed or repaired in the uve/uveit assignments change.',
                       'Passed means reproducible output and complete source reconstruction, not that every annotation translation is semantically correct.',
                       'Pure-mode source reconstruction uses the corresponding Kanji ruby result, not the reverse dictionary. Independent reverse-dictionary checks are recorded separately.'],
        'passed':True},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
if __name__=='__main__':main()
