"""HWPX 구조·편집 개체·배점과 실제 출력본의 원본 수식 영역을 교차검증합니다."""
from pathlib import Path
from collections import Counter
import argparse
import json
import re
import zipfile

from lxml import etree as E
import numpy as np
import fitz
from PIL import Image, ImageFilter
from hwpx_shapes import NS
from layout_guards import pdf_layout, equation_guard, normalize_script, metrics_guard


def paragraph_signature(parts):
    signature = []
    for kind, value in parts:
        if kind == 'text':
            # 내용 대조만 공백을 제외합니다. 실제 간격은 출력 지면에서 별도로 검사합니다.
            value = re.sub(r'\s+', '', value)
            if not value:
                continue
            if signature and signature[-1][0] == 'text':
                signature[-1] = ('text', signature[-1][1] + value)
                continue
        signature.append((kind, value))
    return tuple(signature)


def validate_plan(path, plan):
    with zipfile.ZipFile(path) as z:
        names = sorted((n for n in z.namelist() if re.fullmatch(r'Contents/section\d+\.xml', n)), key=lambda n:int(re.search(r'\d+', n).group()))
        roots = [E.fromstring(z.read(name), E.XMLParser(resolve_entities=False, no_network=True)) for name in names]
    anchors = [p for root in roots for p in root.findall('hp:p', NS)]
    if len(anchors) != len(plan['pages']):
        raise ValueError('원고와 출력의 명시적 페이지 문단 개수가 다릅니다.')
    counts = {'equations':0, 'native_paragraphs':0, 'inline_metrics':0}
    for page_number, (page, anchor) in enumerate(zip(plan['pages'], anchors), 1):
        expected_equations = []
        expected_paragraphs = []
        for block in page['blocks']:
            if block['type'] == 'equation':
                expected_equations.append(block)
            if block['type'] in ('text', 'paragraph'):
                runs = block.get('runs', [{'text':block.get('text', '')}])
                parts = []
                for run in runs:
                    if 'equation' in run:
                        settings = dict(block, **run, script=run['equation'])
                        expected_equations.append(settings)
                        parts.append(('equation', normalize_script(run['equation'])))
                    else:
                        parts.append(('text', run['text']))
                signature = paragraph_signature(parts)
                if signature:
                    expected_paragraphs.append(signature)
        actual_equations = anchor.findall('.//hp:equation', NS)
        if len(expected_equations) != len(actual_equations):
            raise ValueError(f'{page_number}쪽의 수식 개수가 원고와 다릅니다.')
        for expected, actual in zip(expected_equations, actual_equations):
            script = actual.find('hp:script', NS).text or ''
            if normalize_script(expected['script']) != script.strip():
                raise ValueError(f'{page_number}쪽 수식 내용/순서가 원고와 다릅니다: {script}')
            equation_guard(expected, script)
            if expected['type'] == 'paragraph':
                metrics_guard(expected)
                sz = actual.find('hp:sz', NS)
                pos = actual.find('hp:pos', NS)
                match = pos.get('treatAsChar') == '1'
                match = match and int(sz.get('width')) == round(expected['width'] * 100)
                match = match and int(sz.get('height')) == round(expected['height'] * 100)
                match = match and int(actual.get('baseLine')) == expected['baseline']
                match = match and actual.get('font') == expected['equation_font']
                match = match and int(actual.get('baseUnit')) == round(expected.get('size', 11) * 100)
                if not match:
                    raise ValueError(f'{page_number}쪽 인라인 수식의 치수/글꼴/기준선이 측정 원고와 다릅니다.')
                counts['inline_metrics'] += 1
        actual_paragraphs = []
        for para in anchor.findall('.//hp:tc/hp:subList/hp:p', NS):
            parts = []
            for run in para.findall('hp:run', NS):
                for child in run:
                    local = E.QName(child).localname
                    if local == 't':
                        parts.append(('text', ''.join(child.itertext())))
                    elif local == 'equation':
                        parts.append(('equation', (child.find('hp:script', NS).text or '').strip()))
            actual_paragraphs.append(paragraph_signature(parts))
        # 양식의 머리말 문단은 허용하되 본문 문단의 내용·순서·수식 위치는 보존해야 합니다.
        cursor = 0
        for expected in expected_paragraphs:
            try:
                cursor = actual_paragraphs.index(expected, cursor) + 1
            except ValueError as exc:
                raise ValueError(f'{page_number}쪽 본문의 내용/순서 또는 문단 내 수식 위치가 원고와 다릅니다: {expected}') from exc
        counts['equations'] += len(expected_equations)
        counts['native_paragraphs'] += len(expected_paragraphs)
    return counts


def structural(path):
    warnings = []
    texts, equations = [], []
    images = 0
    with zipfile.ZipFile(path) as z:
        if z.testzip():
            raise ValueError('손상된 ZIP 파일')
        if z.infolist()[0].filename != 'mimetype' or z.infolist()[0].compress_type != 0:
            raise ValueError('mimetype은 첫 항목이며 비압축이어야 합니다.')
        for name in z.namelist():
            if not re.fullmatch(r'Contents/section\d+\.xml', name):
                continue
            root = E.fromstring(z.read(name), E.XMLParser(resolve_entities=False, no_network=True))
            for t in root.findall('.//hp:t', NS):
                texts.append(''.join(t.itertext()))
            for eq in root.findall('.//hp:equation', NS):
                script = eq.find('hp:script', NS).text or ''
                if not script:
                    raise ValueError('비어 있는 한글 수식')
                # LEFT{ / RIGHT}는 그룹 중괄호가 아닌 늘어나는 경계 기호입니다.
                grouping = re.sub(r'\bLEFT\s*\{|\bRIGHT\s*\}', '', script)
                if grouping.count('{') != grouping.count('}'):
                    warnings.append({'id': eq.get('id'), 'reason': '중괄호 개수 불일치', 'script': script})
                equation_guard({}, script)
                size = float(eq.get('baseUnit', 1100))
                height = int(eq.find('hp:sz', NS).get('height'))
                if height > size * 4 and 'matrix' not in script:
                    warnings.append({'id': eq.get('id'), 'reason': '비정상적으로 높은 수식: 줄 병합 확인', 'script': script})
                equations.append(script)
            images += len(root.findall('.//hp:pic', NS))
    return {'equation_count': len(equations), 'image_count': images, 'score_count': len(re.findall(r'\[[234]점\]', ''.join(texts))), 'warnings': warnings, 'visual_verified': False}


def compare(source_pdf, output_pdf, spec, report_dir):
    src, out = fitz.open(source_pdf), fitz.open(output_pdf)
    report_dir = Path(report_dir)
    results = []
    for index, region in enumerate(spec.get('regions', [])):
        a, b = src[region['source_page'] - 1], out[region['output_page'] - 1]
        rect = fitz.Rect(region['bbox'])
        target = fitz.Rect(rect.x0 * b.rect.width / a.rect.width, rect.y0 * b.rect.height / a.rect.height, rect.x1 * b.rect.width / a.rect.width, rect.y1 * b.rect.height / a.rect.height)
        pa = a.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect, colorspace=fitz.csGRAY, alpha=False)
        pb = b.get_pixmap(matrix=fitz.Matrix(2, 2), clip=target, colorspace=fitz.csGRAY, alpha=False)
        ia = Image.frombytes('L', (pa.width, pa.height), pa.samples)
        ib = Image.frombytes('L', (pb.width, pb.height), pb.samples).resize(ia.size)
        aa, bb = np.asarray(ia) < 185, np.asarray(ib) < 185
        ad = np.asarray(Image.fromarray(aa.astype('uint8') * 255).filter(ImageFilter.MaxFilter(3))) > 0
        bd = np.asarray(Image.fromarray(bb.astype('uint8') * 255).filter(ImageFilter.MaxFilter(3))) > 0
        score = float(((aa & bd).sum() / max(1, aa.sum()) + (bb & ad).sum() / max(1, bb.sum())) / 2)
        low = score < spec.get('threshold', .35)
        row = dict(region, pixel_score=round(score, 4), requires_human_review=low)
        if low:
            panel = Image.new('RGB', (ia.width * 2, ia.height), 'white')
            panel.paste(ia, (0, 0))
            panel.paste(ib, (ia.width, 0))
            name = f'low-{index+1:04}.png'
            panel.save(report_dir / name)
            row['comparison'] = name
        results.append(row)
    pages = []
    for mapping in spec.get('pages', []):
        a = re.sub(r'\s+', '', src[mapping['source_page'] - 1].get_text())
        b = re.sub(r'\s+', '', out[mapping['output_page'] - 1].get_text())
        scores_a = Counter(re.findall(r'\[[234]점\]', a))
        scores_b = Counter(re.findall(r'\[[234]점\]', b))
        checks = {literal: re.sub(r'\s+', '', literal) in b for literal in mapping.get('required_text', [])}
        pages.append(dict(mapping, source_scores=dict(scores_a), output_scores=dict(scores_b), score_match=scores_a == scores_b, required_text_checks=checks))
    return {'source_pages': len(src), 'output_pages': len(out), 'regions': results, 'pages': pages, 'low_count': sum(r['requires_human_review'] for r in results), 'visual_verified': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('hwpx')
    p.add_argument('report_dir')
    p.add_argument('--source-pdf')
    p.add_argument('--output-pdf')
    p.add_argument('--spec')
    p.add_argument('--layout-spec', help='실제 PDF의 머리말·바닥글 위치 검사 JSON')
    p.add_argument('--plan', help='조립 후에도 수식의 원본 괄호 보존을 검사할 원고 JSON')
    a = p.parse_args()
    folder = Path(a.report_dir)
    folder.mkdir(parents=True, exist_ok=False)
    result = structural(a.hwpx)
    if a.plan:
        plan = json.loads(Path(a.plan).read_text(encoding='utf-8'))
        result['plan_checks'] = validate_plan(a.hwpx, plan)
        if a.output_pdf:
            with fitz.open(a.output_pdf) as doc:
                if len(doc) != len(plan['pages']):
                    raise ValueError('실제 출력 PDF의 쪽 수가 원고와 다릅니다.')
    if a.layout_spec:
        if not a.output_pdf:
            p.error('--layout-spec에는 --output-pdf가 필요합니다.')
        result['layout'] = pdf_layout(a.output_pdf, json.loads(Path(a.layout_spec).read_text(encoding='utf-8')))
    if a.source_pdf or a.spec:
        if not (a.source_pdf and a.output_pdf and a.spec):
            p.error('영상 비교는 --source-pdf, --output-pdf, --spec 세 가지가 모두 필요합니다.')
        result['comparison'] = compare(a.source_pdf, a.output_pdf, json.loads(Path(a.spec).read_text(encoding='utf-8')), folder)
    (folder / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {k: v for k, v in result.items() if k not in ('comparison', 'layout')}
    if 'layout' in result:
        summary['layout'] = {'passed': result['layout']['passed'], 'checks': len(result['layout']['checks']), 'failures': sum(not row['passed'] for row in result['layout']['checks'])}
    print(json.dumps(summary, ensure_ascii=False))
    if result.get('layout') and not result['layout']['passed']:
        raise SystemExit(1)
    if result.get('comparison') and any(not row['score_match'] or not all(row['required_text_checks'].values()) for row in result['comparison']['pages']):
        raise SystemExit(1)
    if result.get('comparison', {}).get('low_count', 0):
        print('낮은 영상 비교 점수가 남았습니다. 크롭을 직접 검토하고 검증 기록에 판단을 남기세요.')
        raise SystemExit(2)
