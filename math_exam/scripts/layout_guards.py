"""수식의 늘어나는 괄호와 실제 PDF의 머리말·바닥글 위치를 검사합니다."""
import re
import math
import fitz


def normalize_script(script):
    # 측정과 조립에 같은 첨자 범위를 사용해야 폭이 달라지지 않습니다.
    if not isinstance(script, str) or not script.strip() or '\n' in script:
        raise ValueError('수식은 비어 있지 않은 한 행 스크립트여야 합니다.')
    return re.sub(r'([\^_])([0-9]+)', r'\1{\2}', script).strip()


def metrics_guard(block):
    required = ('width', 'height', 'baseline', 'equation_font', 'measurement')
    if not all(key in block for key in required):
        raise ValueError('인라인 수식 치수와 측정 출처가 필요합니다. measure_equations.py로 다시 측정하세요.')
    for key in ('width', 'height'):
        value = block[key]
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('수식 치수는 유한한 양수여야 합니다: ' + key)
    if not isinstance(block['baseline'], (int, float)) or not 0 <= block['baseline'] <= 100:
        raise ValueError('수식 기준선은 0~100 범위여야 합니다.')
    expected = {'script':normalize_script(block['script']), 'size':round(block.get('size', 11) * 100) / 100, 'font':block['equation_font']}
    if block['measurement'] != expected:
        raise ValueError('수식·글꼴·크기가 측정 당시와 다릅니다. 이전 치수를 재사용하지 말고 다시 측정하세요.')


def equation_guard(block, script):
    if re.search(r'[_^][A-Za-z]+[+\-=]', script):
        raise ValueError('첨자 뒤 연산이 첨자에 들어가지 않도록 범위를 중괄호로 지정하세요: ' + script)
    if re.search('[가-힣]', script):
        raise ValueError('한글 본문은 수식에 넣지 마세요. paragraph의 text run으로 분리하세요: ' + script)
    if re.search(r'\{\s*rm\s*\{\s*(sin|cos|tan|ln|log)\s*\}', script):
        raise ValueError('함수명은 한글 수식 내장 sin, cos, tan, ln, log를 사용하세요: ' + script)
    if re.search(r'\b(sin|cos|tan|ln|log)(?:\s*[_^]\s*\{[^{}]*\})*\s*~|,\s*~', script):
        raise ValueError('함수명 또는 쉼표 뒤 강제 ~ 간격을 제거하고 출력 간격을 확인하세요: ' + script)
    # LEFT/RIGHT는 보기 좋게 만드는 옵션이 아니라 원본 수식의 조판 정보입니다.
    left = len(re.findall(r'\bLEFT\s*\(', script))
    right = len(re.findall(r'\bRIGHT\s*\)', script))
    if left != right:
        raise ValueError('늘어나는 괄호의 LEFT/RIGHT 개수가 다릅니다: ' + script)
    source = block.get('source_script')
    if source is not None:
        for side, bracket in [('LEFT', '('), ('RIGHT', ')')]:
            pattern = r'\b' + side + r'\s*' + re.escape(bracket)
            if len(re.findall(pattern, source)) != len(re.findall(pattern, script)):
                raise ValueError('원본 수식의 LEFT/RIGHT 괄호 정보가 바뀌었습니다: ' + script)
    if block.get('stretch_parentheses_required'):
        if not re.search(r'\bLEFT\s*\(', script) or not re.search(r'\bRIGHT\s*\)', script):
            raise ValueError('분수·합·극한을 감싼 큰 괄호가 누락되었습니다: ' + script)
    if re.search(r'\bLEFT\s*\(', script) and not re.search(r'\bRIGHT\s*\)', script):
        raise ValueError('LEFT 괄호의 RIGHT 짝이 없습니다: ' + script)


def pdf_layout(path, spec):
    results = []
    with fitz.open(path) as doc:
        for check in spec.get('layout_checks', []):
            page = doc[check['page'] - 1]
            region = fitz.Rect(check['region'])
            lines = []
            spans = []
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines', []):
                    selected = [s for s in line['spans'] if fitz.Rect(s['bbox']).intersects(region)]
                    if selected:
                        lines.append(''.join(s['text'] for s in selected))
                        spans.extend(selected)
            compact = lambda value: re.sub(r'\s+', '', value)
            literal = compact(check['text'])
            matching = [s for s in spans if literal in compact(s['text'])]
            text_ok = literal in compact(''.join(lines))
            # 전체 문구가 한 PDF 행 안에 있어야 줄바꿈을 놓치지 않습니다.
            one_line = any(literal in compact(line) for line in lines)
            inside = all(region.contains(fitz.Rect(s['bbox'])) for s in matching)
            color_ok = all(s['color'] in check['colors'] for s in matching) if 'colors' in check else True
            if 'colors' in check and not matching:
                color_ok = False
            overlap = []
            if check.get('no_body_overlap'):
                body_top = check['body_top']
                for own in matching:
                    own_rect = fitz.Rect(own['bbox'])
                    for b in page.get_text('dict')['blocks']:
                        for line in b.get('lines', []):
                            for s in line['spans']:
                                r = fitz.Rect(s['bbox'])
                                intersection = own_rect & r
                                if s['text'] != own['text'] and r.y0 >= body_top and intersection.width > .5 and intersection.height > .5:
                                    overlap.append(s['text'])
            occurrences = compact(page.get_text(flags=0)).count(literal)
            expected = check.get('expected_occurrences')
            unique = expected is None or occurrences == expected
            passed = text_ok and inside and color_ok and not overlap and unique
            if check.get('max_lines') == 1:
                passed = passed and one_line
            results.append(dict(check, passed=passed, occurrences=occurrences, text_present=text_ok, single_line=one_line, inside_region=inside, color_match=color_ok, body_overlap=overlap, bboxes=[s['bbox'] for s in matching]))
    return {'checks': results, 'passed': all(row['passed'] for row in results), 'visual_verified': False}
