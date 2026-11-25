"""Verify that choosing the ethnic meaning applies only to that occurrence."""
import argparse
from pathlib import Path
import sys


def check(root, language):
    app = root / f'Esperanto-Kanji-Ruby-{language}'
    sys.path.insert(0, str(app))
    import esp_assignment_edition as editions
    import esp_occurrence_senses as senses
    import esp_overlay_module as overlay
    import esp_text_replacement_module as engine

    data = app / 'app_data'
    source = 'akeo Akeo @Ake@o @akeo@ %Akeo% aKE lakeo akeo@example.org nefrito'
    candidates = senses.find_occurrences(source)
    assert [item['source'] for item in candidates] == ['akeo', 'Akeo', 'Ake', 'akeo', 'nefrito']
    ethnic = {'JA': 'アカイア人', 'ZH': '亚该亚人', 'KO': '아카이아인'}[language]
    animal = {'JA': 'ナマケモノ', 'ZH': '树懒', 'KO': '나무늘보'}[language]
    skip = engine.import_placeholders(str(data / 'placeholders_skip.txt'))
    local = engine.import_placeholders(str(data / 'placeholders_localcapture.txt'))
    for edition in ('current', 'legacy'):
        for mode, fmt in [('pure', '替换后文字列のみ(仅)保留(简单替换)'),
                          ('kanji', overlay.KANJI_FMT), ('ruby', overlay.RUBY_FMT)]:
            global_rules, local_rules, two_letter = editions.load_lists(data, mode, edition)
            selected = senses.render_selections(source, [1, 2, 4], data, fmt, edition=edition, bundled=True)
            assert len(selected) == (3 if edition == 'current' else 2)
            assert not senses.render_selections(source, [1], data, fmt, edition=edition, bundled=False)
            result = engine.orchestrate_comprehensive_esperanto_text_replacement(
                source, skip, local_rules, local, global_rules, two_letter, fmt,
                reviewed_local_decompositions=True, explicit_occurrences=selected)
            assert '@Ake@' not in result
            if mode == 'ruby':
                annotations = result.replace('<br>', '')
                assert annotations.count(ethnic) == 2 and annotations.count(animal) >= 2, result
            elif mode == 'pure':
                assert result.startswith('树懒o Akeo Akeo 树懒o Akeo '), result
            else:
                assert result.count('树懒') >= 2 and ' Akeo Akeo ' in result, result
            try:
                corrupted = [dict(selected[0], sense_key='nefrit.mineral')]
                engine.orchestrate_comprehensive_esperanto_text_replacement(
                    source, skip, local_rules, local, global_rules, two_letter, fmt,
                    explicit_occurrences=corrupted)
            except ValueError:
                pass
            else:
                raise AssertionError('A meaning for a different root was accepted')
            editions._load_lists_cached.clear()
    print(language, 'passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--lang', required=True, choices=['JA','ZH','KO'])
    args = parser.parse_args()
    check(args.root.resolve(), args.lang)

