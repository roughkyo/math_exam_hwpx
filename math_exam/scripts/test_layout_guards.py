"""실제 보고된 괄호 소실·바닥글 줄바꿈·머리말 본문 침범을 재현합니다."""
import tempfile
import json
from pathlib import Path
import fitz
from layout_guards import equation_guard, pdf_layout
from build_exam import build


def run():
    source = 'LEFT ( {1} over {27} RIGHT )^{x}'
    equation_guard({'source_script': source}, source)
    try:
        equation_guard({'source_script': source}, '({1} over {27})^{x}')
    except ValueError:
        pass
    else:
        raise AssertionError('큰 괄호를 잃은 수식을 통과시켰습니다.')
    work = Path.cwd() / 'work'
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work) as folder:
        folder = Path(folder)
        plan = {'pages': [{'blocks': [{'type': 'equation', 'x': 60, 'y': 240, 'width': 300, 'height': 40, 'script': '( {1} over {27} )^{x}', 'source_script': source}]}]}
        plan_path = folder / 'bad-plan.json'
        plan_path.write_text(json.dumps(plan), encoding='utf-8')
        try:
            build(plan_path, folder / 'rejected.hwpx')
        except ValueError:
            pass
        else:
            raise AssertionError('빌더가 원본 괄호 유실을 허용했습니다.')
        assert not (folder / 'rejected.hwpx').exists()
        path = Path(folder) / 'fixture.pdf'
        doc = fitz.open()
        good = doc.new_page()
        good.insert_text((40, 40), 'ODD', color=(0, 0, 1))
        good.insert_text((40, 100), 'BODY')
        good.insert_text((40, 760), 'COPYRIGHT NOTICE')
        bad = doc.new_page()
        bad.insert_text((40, 100), 'ODD')
        bad.insert_text((40, 100), 'BODY')
        bad.insert_text((40, 760), 'COPYRIGHT')
        bad.insert_text((40, 774), 'NOTICE')
        doc.save(path)
        doc.close()
        checks = []
        for page in (1, 2):
            checks.extend([
                {'page': page, 'text': 'ODD', 'region': [0, 0, 200, 70], 'colors': [255], 'no_body_overlap': True, 'body_top': 80},
                {'page': page, 'text': 'COPYRIGHT NOTICE', 'region': [0, 740, 300, 800], 'max_lines': 1},
            ])
        result = pdf_layout(path, {'layout_checks': checks})
        assert [row['passed'] for row in result['checks']] == [True, True, False, False], result
        overlap = pdf_layout(path, {'layout_checks': [{'page': 2, 'text': 'ODD', 'region': [0, 80, 200, 140], 'no_body_overlap': True, 'body_top': 80}]})
        assert overlap['checks'][0]['body_overlap'] == ['BODY'] and not overlap['passed']
    print('PASS: stretch parentheses, header bounds/color, wrapped footer')


if __name__ == '__main__':
    run()
