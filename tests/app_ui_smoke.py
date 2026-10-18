"""Run actual Streamlit forms from the repository root (not a browser test).

Run from the repository root with: python -B -X utf8 tests/app_ui_smoke.py
Results contain repository-relative paths only. Each language runs in a fresh
process so that modules with the same names cannot leak between language apps.
The working directory is set once per language and must remain unchanged across
reruns and page navigation. Resetting it before reruns would hide Cloud failures.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
SOURCE = '@semajn@tagoj & %amiko% ŝakisto semajntagoj'
EXPECTED = '周日oj & amiko 棋家o 周日oj'
REVISION_SOURCE = 'struto sinergio olivo @strut@ @sinergi@ @oliv@ @limak@o @orkidit@o @testikit@o @litografi@o @semajn@tagoj & %amiko% ŝakisto ovalo elipso'
REVISION_EXPECTED = '鸵o 协同o 榄o 鸵 协同 榄 螺ᴸo 丸ᴼ炎ᵀo 丸ᵀ炎ᵀo 石ᴸᵀ志ᴳo 周日oj & amiko 棋家o 椭圆o 椭圆ᴱo'
STAFILOKOK_SOURCE = REVISION_SOURCE + ' stafilokoko @stafilokok@o turmenti torturi uvo uveito'
STAFILOKOK_EXPECTED = REVISION_EXPECTED + ' 葡球菌o 葡球菌o 虐i 虐ᵀᵀi 葡ᵁo 葡膜炎ᵀo'
FOUR_SHARED_SOURCE = STAFILOKOK_SOURCE + ' psitako @psitak@o @uv@o limono @limon@o limonado @limonad@o uveo'
FOUR_SHARED_EXPECTED = STAFILOKOK_EXPECTED + ' 鹦ᴾˢo 鹦ᴾˢo 葡ᵁo 柠o 柠o 柠水o 柠水o 葡膜o'
UVE_SOURCE = FOUR_SHARED_SOURCE + ' @uve@o @uveit@o uveoj uveitoj @uveit@oj'
UVE_EXPECTED = FOUR_SHARED_EXPECTED + ' 葡膜o 葡膜炎ᵀo 葡膜oj 葡膜炎ᵀoj 葡膜炎ᵀoj'
OBSERVATORI_SOURCE = UVE_SOURCE + ' observatorio @observatori@o observatorioj @observatori@ojn @observ@i majesta subtila'
OBSERVATORI_EXPECTED = UVE_EXPECTED + ' 观台o 观台o 观台oj 观台ojn 观i 庄严a 精细a'
THREE_SHORT_SOURCE = OBSERVATORI_SOURCE + ' risorti @risort@i anĉo @anĉ@o lanterno @lantern@o lubriki @lubrik@i plando lampo lucerno gliti majesta subtila'
THREE_SHORT_EXPECTED = OBSERVATORI_EXPECTED + ' 簧i 簧i 簧ᴬo 簧ᴬo 灯ᴸᴺo 灯ᴸᴺo 滑ᴸi 滑ᴸi 足底o 灯o 灯ᴸᶜo 滑i 庄严a 精细a'
PROTEZ_RANC_SOURCE = THREE_SHORT_SOURCE + ' protezo @protez@o protezoj dentprotezo ranca @ranc@a ranci hangaro kontesti cisticerko kruco'
PROTEZ_RANC_EXPECTED = THREE_SHORT_EXPECTED + ' 假体o 假体o 假体oj 齿假体o 酸败a 酸败a 酸败i 棚库o 异议i 囊尾虫o 十字o'
FOUR_REVIEWED_SOURCE = PROTEZ_RANC_SOURCE + ' krepo @krep@o difrakto @difrakt@o mortezo @mortez@o megero @meger@o'
FOUR_REVIEWED_EXPECTED = PROTEZ_RANC_EXPECTED + ' 皱布o 皱布o 绕射o 绕射o 卯o 卯o 恶女o 恶女o'
SUTUR_FRAJ_SOURCE = FOUR_REVIEWED_SOURCE + ' suturo @sutur@o suturi frajo @fraj@o fraji prismo @prism@o kudri stebo ovo ovolo'
SUTUR_FRAJ_EXPECTED = FOUR_REVIEWED_EXPECTED + ' 缝ˢᴿo 缝ˢᴿo 缝ˢᴿi 卵ᶠo 卵ᶠo 卵ᶠi 棱镜o 棱镜o 缝i 缝ˢo 卵o 卵ᴼᴸo'
NOSTALGI_ONK_FORTRES_SOURCE = SUTUR_FRAJ_SOURCE + ' nostalgio @nostalgi@o onko @onk@o onkogena @onkogen@a onkologio @onkologi@o fortreso @fortres@o koincidi @koincid@i'
NOSTALGI_ONK_FORTRES_EXPECTED = SUTUR_FRAJ_EXPECTED + ' 怀ᴺo 怀ᴺo 瘤ᴼo 瘤ᴼo 瘤ᴼo生ᴳa 瘤ᴼ生ᴳa 瘤ᴼo学ᴸᴳo 瘤ᴼ学ᴸᴳo 堡ᶠᴿo 堡ᶠᴿo 巧合i 巧合i'
SATIR_SOURCE = NOSTALGI_ONK_FORTRES_SOURCE + ' satiro @satir@o karikaturo @karikatur@o sarkasmo @sarkasm@o spermo @sperm@o ĉuro @ĉur@o spermatozoo'
SATIR_EXPECTED = NOSTALGI_ONK_FORTRES_EXPECTED + ' 讽o 讽o 讽ᴷo 讽ᴷo 讽ˢᴿo 讽ˢᴿo 精液o 精液o 精液ᶜ̂o 精液ᶜ̂o 精子ˢᶻo'
SPERM_DISTINCTION_SOURCE = SATIR_SOURCE + ' @spermatozo@o spermatozooj @spermatozo@ojn spermato @spermat@o spermatio @spermati@o spermatocito @spermatocit@o spermatofitoj @spermatofit@oj spermatogenezo @spermatogenez@o silfo @silf@o'
SPERM_DISTINCTION_EXPECTED = SATIR_EXPECTED + ' 精子ˢᶻo 精子ˢᶻoj 精子ˢᶻojn 精子o 精子o 精子ˢᴵo 精子ˢᴵo 精子o胞ᶜᴵo 精子胞ᶜᴵo 精子o植ᶠoj 精子植ᶠoj 精子o源ᴳo 精子源ᴳo 精ˢo 精ˢo'
LANGUAGES = ('JA', 'ZH', 'KO')


def public_message(value):
    """Keep failures useful without exposing machine-specific absolute paths."""
    message = str(value)
    for path, replacement in ((ROOT, '<repo>'), (Path.home(), '<home>'),
                              (Path(sys.prefix), '<python>')):
        message = message.replace(str(path), replacement)
        message = message.replace(path.as_posix(), replacement)
    return re.sub(r'[A-Za-z]:[\\/][^\s\"\'<>]*', '<absolute-path>', message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_from_root(at):
    assert Path.cwd() == ROOT, 'The AppTest must start from the repository root'
    at.run()
    assert Path.cwd() == ROOT, 'The app changed the process working directory'
    if at.exception:
        raise AssertionError('; '.join(public_message(item.message) for item in at.exception))
    if at.error:
        raise AssertionError('; '.join(public_message(item.value) for item in at.error))
    return at


def run_language(language):
    from streamlit.testing.v1 import AppTest

    os.chdir(ROOT)
    app = ROOT / ('Esperanto-Kanji-Ruby-' + language)
    sys.path.insert(0, str(app))
    main = app / 'main.py'
    scripts = [main, *sorted((app / 'pages').glob('*.py'))]
    before = {path.relative_to(ROOT).as_posix(): sha256(path) for path in scripts}
    started = time.perf_counter()
    # Keep the entrypoint relative, as it is when launched from the repo root.
    at = run_from_root(AppTest.from_file(main.relative_to(ROOT), default_timeout=120))
    modes = list(at.radio[0].options[:3])
    assert len(modes) == 3, 'Expected the three built-in conversion modes'
    results = []
    for index, mode in enumerate(modes):
        mode_started = time.perf_counter()
        at.radio[0].set_value(mode)
        run_from_root(at)
        at.text_area(key='text0_value').set_value(SOURCE)
        submit = at.button(key='convert_text')
        submit.click()
        run_from_root(at)
        rendered = at.session_state['result_html']
        assert rendered and '@' not in rendered, 'The local marker was not removed'
        if SOURCE in (SUTUR_FRAJ_SOURCE, NOSTALGI_ONK_FORTRES_SOURCE, SATIR_SOURCE, SPERM_DISTINCTION_SOURCE) and index == 0:
            # Independent semantic expectations from the user-approved meaning.
            meanings = {
                'JA': ('魚・カエルなどの卵の集まり', '産卵する'),
                'ZH': ('鱼、蛙等的卵块', '产卵'),
                'KO': ('물고기·개구리 등의 알 덩어리', '산란하다'),
            }
            flatten = lambda value: re.sub(r'\s+', '', html.unescape(re.sub(r'<[^>]*>', '', value)))
            fraj_ruby = {flatten(gloss) for source, gloss in
                         re.findall(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', rendered, re.S)
                         if flatten(source).lower() == 'fraj'}
            assert fraj_ruby == {flatten(value) for value in meanings[language]}, (language, fraj_ruby)
        if SOURCE in (NOSTALGI_ONK_FORTRES_SOURCE, SATIR_SOURCE, SPERM_DISTINCTION_SOURCE) and index == 0:
            meanings = {
                'JA': {'nostalgi': '郷愁・懐かしさや憧れに伴う悲しさ', 'onk': '腫瘍（特に悪性）', 'fortres': '大規模で堅固な要塞'},
                'ZH': {'nostalgi': '思乡、怀旧或渴望引起的悲伤', 'onk': '肿瘤（尤指恶性）', 'fortres': '大型坚固要塞'},
                'KO': {'nostalgi': '향수·그리움·갈망의 슬픔', 'onk': '종양（특히 악성）', 'fortres': '크고 견고한 요새'},
            }
            pairs = [(flatten(source).lower(), flatten(gloss)) for source, gloss in
                     re.findall(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', rendered, re.S)]
            for root, meaning in meanings[language].items():
                assert {gloss for source, gloss in pairs if source == root} == {flatten(meaning)}, (language, root, pairs)
        if SOURCE == SPERM_DISTINCTION_SOURCE and index == 0:
            # Independently reviewed meanings: cell/liquid distinction and
            # botanical senses survive the shared kanji spelling.
            meaning_tokens = {
                'JA': {'sperm': ('精液',), 'ĉur': ('精液',),
                       'spermatozo': ('精子',), 'spermatofit': ('種子植物',),
                       'spermati': ('植物', '不動'), 'cit': ('細胞',)},
                'ZH': {'sperm': ('精液',), 'ĉur': ('精液',),
                       'spermatozo': ('精子',), 'spermatofit': ('种子植物',),
                       'spermati': ('植物', '不动'), 'cit': ('细胞',)},
                'KO': {'sperm': ('정액',), 'ĉur': ('정액',),
                       'spermatozo': ('정자',), 'spermatofit': ('종자식물',),
                       'spermati': ('식물', '비운동'), 'cit': ('세포',)},
            }
            for root, tokens in meaning_tokens[language].items():
                glosses = [gloss for source, gloss in pairs if source == root]
                assert glosses and all(all(flatten(token) in gloss for token in tokens)
                                       for gloss in glosses), (language, root, glosses)
            for root in ('sperm', 'ĉur'):
                cell_word = '정자' if language == 'KO' else '精子'
                assert all(cell_word not in gloss for source, gloss in pairs
                           if source == root), (language, root, pairs)
        assert 'amiko' in rendered and '%amiko%' not in rendered, 'The skip marker contract failed'
        assert '&' in html.unescape(rendered), 'The ampersand was not preserved'
        if index == 2:
            assert rendered == EXPECTED, 'Reviewed pure outputs differ'
            assert '<ruby' not in rendered and '<html' not in rendered, 'Pure mode emitted HTML'
        else:
            assert '<ruby' in rendered, 'Ruby mode emitted no ruby annotations'
        results.append({
            'language': language, 'mode': mode, 'source': SOURCE,
            'result_html': rendered, 'passed': True,
            'cwd_before_each_run': '.', 'cwd_after_each_run': '.',
            'elapsed_seconds': round(time.perf_counter() - mode_started, 3),
        })

    pages, returns = [], []
    for prefix, kind in (('1_', 'manual_correction'), ('2_', 'data_download')):
        matches = sorted((app / 'pages').glob(prefix + '*.py'))
        assert len(matches) == 1, 'Expected one page for ' + kind
        path = matches[0]
        page_started = time.perf_counter()
        page = run_from_root(at.switch_page(path.relative_to(app).as_posix()))
        assert page.title, 'The subpage displayed no title'
        if kind == 'manual_correction':
            assert page.text_input and page.button, 'The correction controls did not appear'
        else:
            assert len(page.header) >= 3, 'The download sections did not appear'
            assert len(page.get('download_button')) >= 3, 'The local downloads did not appear'
        # Rerun the selected page without restoring cwd, then return to the
        # original main entrypoint in the same AppTest session.
        run_from_root(page)
        pages.append({
            'language': language, 'page': path.relative_to(ROOT).as_posix(),
            'kind': kind, 'title': page.title[0].value, 'passed': True,
            'cwd_before_run': '.', 'cwd_after_run': '.', 'reruns': 2,
            'navigation_method': 'AppTest.switch_page',
            'exception_count': len(page.exception),
            'error_count': len(page.error),
            'download_button_count': len(page.get('download_button')),
            'elapsed_seconds': round(time.perf_counter() - page_started, 3),
        })
        return_started = time.perf_counter()
        run_from_root(at.switch_page('main.py'))
        assert at.radio and at.text_area, 'The main form did not return'
        at.radio[0].set_value(at.radio[0].options[2])
        run_from_root(at)
        at.text_area(key='text0_value').set_value(SOURCE)
        submit = at.button(key='convert_text')
        submit.click()
        run_from_root(at)
        returned = at.session_state['result_html']
        assert returned == EXPECTED, 'Conversion after returning to main failed'
        returns.append({
            'language': language, 'from_page': path.relative_to(ROOT).as_posix(),
            'to_page': main.relative_to(ROOT).as_posix(), 'passed': True,
            'navigation_method': 'AppTest.switch_page, same session',
            'cwd_before_each_run': '.', 'cwd_after_each_run': '.',
            'source': SOURCE, 'pure_result': returned,
            'elapsed_seconds': round(time.perf_counter() - return_started, 3),
        })

    after = {path.relative_to(ROOT).as_posix(): sha256(path) for path in scripts}
    assert before == after, 'App/page source changed while the checks were running'
    return {'language': language, 'results': results, 'pages': pages, 'returns': returns,
            'script_sha256': after, 'script_bytes_unchanged_during_run': True,
            'elapsed_seconds': round(time.perf_counter() - started, 3)}


def main():
    global SOURCE, EXPECTED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language', choices=LANGUAGES)
    scenario = parser.add_mutually_exclusive_group()
    scenario.add_argument('--revision', action='store_true', help='Exercise the current assignments and mirror identifiers')
    scenario.add_argument('--stafilokok', action='store_true', help='Exercise stafilokok and retained assignments; save a separate report')
    scenario.add_argument('--four-shared', action='store_true', help='Exercise four shared assignments and retained longer forms; save a new report')
    scenario.add_argument('--uve', action='store_true', help='Exercise uve/uveit and retained assignments; save a new report')
    scenario.add_argument('--observatori', action='store_true', help='Exercise observatori and retained assignments; save a new report')
    scenario.add_argument('--three-short', action='store_true', help='Exercise three shortened assignments and retained controls; save a new report')
    scenario.add_argument('--protez-ranc', action='store_true', help='Exercise protez/ranc and preserved controls; save a new report')
    scenario.add_argument('--four-reviewed', action='store_true', help='Exercise krep/difrakt/mortez/meger and preserved controls')
    scenario.add_argument('--sutur-fraj', action='store_true', help='Exercise sutur/fraj and preserved prism/shared identifiers')
    scenario.add_argument('--nostalgi-onk-fortres', action='store_true', help='Exercise three approved roots, onk component identifiers and retained koincid')
    scenario.add_argument('--satir', action='store_true', help='Exercise satir identifiers and semen controls with current spermatozo spelling')
    scenario.add_argument('--sperm-distinction', action='store_true', help='Exercise sperm cells versus semen, spermat family, botanical meanings and shared identifiers')
    args = parser.parse_args()
    if args.revision:
        SOURCE, EXPECTED = REVISION_SOURCE, REVISION_EXPECTED
    elif args.stafilokok:
        SOURCE, EXPECTED = STAFILOKOK_SOURCE, STAFILOKOK_EXPECTED
    elif args.four_shared:
        SOURCE, EXPECTED = FOUR_SHARED_SOURCE, FOUR_SHARED_EXPECTED
    elif args.uve:
        SOURCE, EXPECTED = UVE_SOURCE, UVE_EXPECTED
    elif args.observatori:
        SOURCE, EXPECTED = OBSERVATORI_SOURCE, OBSERVATORI_EXPECTED
    elif args.three_short:
        SOURCE, EXPECTED = THREE_SHORT_SOURCE, THREE_SHORT_EXPECTED
    if args.protez_ranc:
        SOURCE, EXPECTED = PROTEZ_RANC_SOURCE, PROTEZ_RANC_EXPECTED
    if args.four_reviewed:
        SOURCE, EXPECTED = FOUR_REVIEWED_SOURCE, FOUR_REVIEWED_EXPECTED
    if args.sutur_fraj:
        SOURCE, EXPECTED = SUTUR_FRAJ_SOURCE, SUTUR_FRAJ_EXPECTED
    if args.nostalgi_onk_fortres:
        SOURCE, EXPECTED = NOSTALGI_ONK_FORTRES_SOURCE, NOSTALGI_ONK_FORTRES_EXPECTED
    if args.satir:
        SOURCE, EXPECTED = SATIR_SOURCE, SATIR_EXPECTED
    if args.sperm_distinction:
        SOURCE, EXPECTED = SPERM_DISTINCTION_SOURCE, SPERM_DISTINCTION_EXPECTED
    if args.language:
        try:
            result = run_language(args.language)
        except Exception as exc:
            print(json.dumps({'language': args.language, 'passed': False,
                              'error_type': type(exc).__name__,
                              'error': public_message(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(result, ensure_ascii=False))
        return 0

    os.chdir(ROOT)
    rows, pages, returns, scripts, language_results = [], [], [], {}, []
    for language in LANGUAGES:
        child = subprocess.run(
            [sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()),
             '--language', language, *(['--revision'] if args.revision else ['--stafilokok'] if args.stafilokok else ['--four-shared'] if args.four_shared else ['--uve'] if args.uve else ['--observatori'] if args.observatori else ['--three-short'] if args.three_short else ['--protez-ranc'] if args.protez_ranc else ['--four-reviewed'] if args.four_reviewed else ['--sutur-fraj'] if args.sutur_fraj else ['--nostalgi-onk-fortres'] if args.nostalgi_onk_fortres else ['--satir'] if args.satir else ['--sperm-distinction'] if args.sperm_distinction else [])], cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', timeout=600)
        if child.returncode:
            try:
                failure = json.loads(child.stdout)
            except (ValueError, TypeError):
                failure = {'error': 'AppTest worker failed; return code ' + str(child.returncode)}
            print(language + ': FAILED: ' + public_message(failure.get('error', failure)), flush=True)
            return 1
        result = json.loads(child.stdout)
        rows.extend(result['results'])
        pages.extend(result['pages'])
        returns.extend(result['returns'])
        scripts.update(result['script_sha256'])
        language_results.append({'language': language, 'passed': True,
                                 'elapsed_seconds': result['elapsed_seconds']})
        print(language + ': 3 forms, 2 subpages, and 2 returns passed; cwd stayed at repo root', flush=True)

    import pandas
    import streamlit
    output = {
        'method': 'Streamlit AppTest: relative main.py entrypoint, forms, and same-session page round trips',
        'cwd_policy': 'Set repo root once per language; assert unchanged before and after every run',
        'limitations': [
            'AppTest is not a browser; visual layout and clipboard behavior were not tested.',
            'Subpages were checked for startup and controls, not full correction editing workflows.',
            'Remote download availability and Streamlit Cloud deployment were not tested.',
        ],
        'command': 'python -B -X utf8 tests/app_ui_smoke.py' + (' --revision' if args.revision else ' --stafilokok' if args.stafilokok else ' --four-shared' if args.four_shared else ' --uve' if args.uve else ' --observatori' if args.observatori else ' --three-short' if args.three_short else ' --protez-ranc' if args.protez_ranc else ' --four-reviewed' if args.four_reviewed else ' --sutur-fraj' if args.sutur_fraj else ' --nostalgi-onk-fortres' if args.nostalgi_onk_fortres else ' --satir' if args.satir else ' --sperm-distinction' if args.sperm_distinction else ''),
        'cwd': '.', 'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'environment': {'python': platform.python_version(), 'system': platform.system(),
                        'streamlit': streamlit.__version__, 'pandas': pandas.__version__},
        'passed': True, 'conversion_routes': len(rows), 'subpage_routes': len(pages),
        'return_to_main_routes': len(returns),
        'script_bytes_unchanged_during_run': True, 'script_sha256': scripts,
        'languages': language_results, 'results': rows, 'pages': pages, 'returns': returns,
    }
    output_name = 'app_ui_sperm_distinction.json' if args.sperm_distinction else 'app_ui_satir.json' if args.satir else 'app_ui_nostalgi_onk_fortres.json' if args.nostalgi_onk_fortres else 'app_ui_sutur_fraj.json' if args.sutur_fraj else 'app_ui_four_reviewed.json' if args.four_reviewed else 'app_ui_protez_ranc.json' if args.protez_ranc else 'app_ui_three_short.json' if args.three_short else 'app_ui_observatori.json' if args.observatori else 'app_ui_uve.json' if args.uve else 'app_ui_four_shared.json' if args.four_shared else 'app_ui_stafilokok.json' if args.stafilokok else 'app_ui_mirror_identifiers.json' if args.revision else 'app_ui_smoke.json'
    output_path = Path(__file__).with_name(output_name)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Saved tests/' + output_path.name + ' (9 conversions, 6 subpages, 6 returns)', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
