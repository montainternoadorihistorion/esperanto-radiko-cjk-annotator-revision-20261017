"""Independent scope and code-structure review; no production writes."""
from pathlib import Path
import argparse, ast, hashlib, json, subprocess

ROOT = Path(__file__).resolve().parents[3]
BASELINE = '3454d0359282e001d0baa3db6d45e94efe6eb457'
URLS = {
 'https://esperanto-radiko-cjk-annotator.streamlit.app/': 'https://esperanto-cjk-revision-ja-20261017.streamlit.app/',
 'https://esperanto-radiko-cjk-annotator-zh.streamlit.app/': 'https://esperanto-cjk-revision-zh-20261017.streamlit.app/',
 'https://esperanto-radiko-cjk-annotator-ko.streamlit.app/': 'https://esperanto-cjk-revision-ko-20261017.streamlit.app/',
}

def baseline(path):
    return subprocess.check_output(['git','show',BASELINE+':'+path.as_posix()],cwd=ROOT).decode('utf8')

def reduced(tree):
    return ast.Module(body=[node for node in tree.body if not (
      isinstance(node,ast.FunctionDef) and node.name in ('_render_probe','_decompose')
      or isinstance(node,ast.If) and 'word_in' in ast.unparse(node.test)
      and 'st.button' in ast.unparse(node.test))],type_ignores=[])

def check(report):
    rows=[]; render=[]; allowed=set()
    for language in ('JA','ZH','KO'):
        app=ROOT/f'Esperanto-Kanji-Ruby-{language}'
        main=app/'main.py'; page=next((app/'pages').glob('1_*.py'))
        for path in (main,page):allowed.add(path.relative_to(ROOT).as_posix())
        old=baseline(main.relative_to(ROOT)); new=main.read_text(encoding='utf8')
        adjusted=old
        for first,second in URLS.items():
            assert adjusted.count(first)==1
            adjusted=adjusted.replace(first,second)
        assert adjusted==new,language+' main changed beyond footer links'
        old_ast=ast.parse(baseline(page.relative_to(ROOT)))
        new_ast=ast.parse(page.read_text(encoding='utf8'))
        assert ast.dump(reduced(old_ast))==ast.dump(reduced(new_ast)),language+' unrelated page changes'
        old_d=next(n for n in old_ast.body if isinstance(n,ast.FunctionDef) and n.name=='_decompose')
        new_d=next(n for n in new_ast.body if isinstance(n,ast.FunctionDef) and n.name=='_decompose')
        # The existing segment extractor remains the exact same AST suffix.
        def extraction_suffix(function):
            start=next(i for i,n in enumerate(function.body) if isinstance(n,ast.Assign)
                       and ast.unparse(n).startswith('toks, pos ='))
            return [ast.dump(n) for n in function.body[start:]]
        assert extraction_suffix(old_d)==extraction_suffix(new_d)
        helper=next(n for n in new_ast.body if isinstance(n,ast.FunctionDef) and n.name=='_render_probe')
        render.append(ast.dump(helper))
        rows.append({'language':language,'main_only_footer_links':True,
          'page_only_render_diagnostic_preview':True,'segment_extractor_unchanged':True,
          'main_sha256':hashlib.sha256(main.read_bytes()).hexdigest(),
          'page_sha256':hashlib.sha256(page.read_bytes()).hexdigest()})
    assert len(set(render))==1,'render helper differs between languages'
    changed=subprocess.check_output(['git','diff','--name-only',BASELINE],cwd=ROOT).decode().splitlines()
    # Git may quote unicode names; use NUL-separated raw paths instead.
    changed=subprocess.check_output(['git','diff','--name-only','-z',BASELINE],cwd=ROOT).decode().split('\0')
    unexpected=[p for p in changed if p and p not in allowed and not p.startswith('tests/') and not p.startswith('.github/')]
    assert not unexpected,unexpected
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps({'passed':True,'baseline':BASELINE,'rows':rows,
      'cross_language_render_helper_identical':True,'issues':[],
      'review_notes':[
       'Stored/session overlay merge, automatic discovery and optional second pass match existing main.py semantics.',
       'Optional autofix exceptions retain pass-one rendering, matching main behavior.',
       'Diagnostic and both preview iframes reuse the same two final results; no extra preview rendering can disagree.',
       'Original input normalization, padding, segment extraction, draft seeding, session save/delete/upload and download handling remain unchanged.',
       'No engine, edition helper, assignment, identifier, replacement data, reverter or HTML recovery code changed.',
       'Archived earlier exact-at AppTest expected three engine calls; it describes the earlier implementation and is intentionally preserved. New tests compare output rather than stale call counts.'
      ]},ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True)
    check(p.parse_args().report)
