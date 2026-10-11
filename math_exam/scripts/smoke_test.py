"""새 작업 폴더에서 재현성·수식 범위·미검토 원고 거부·원본 보존을 검사합니다."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

from lxml import etree as E
from build_exam import build, PACKAGE, NS
from validate_exam import structural


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', required=True, help='아직 없는 새 작업 하위 폴더')
    a = p.parse_args()
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=False)
    plan = PACKAGE / 'examples/area-three.json'
    template = PACKAGE / 'assets/forms/default_exam.hwpx'
    before = hashlib.sha256(template.read_bytes()).hexdigest()
    first = build(plan, work / 'sample-a.hwpx')
    second = build(plan, work / 'sample-b.hwpx')
    assert first.read_bytes() == second.read_bytes()
    assert hashlib.sha256(template.read_bytes()).hexdigest() == before
    result = structural(first)
    assert result['equation_count'] == 51 and result['image_count'] == 3 and result['score_count'] == 3
    with zipfile.ZipFile(first) as z:
        root = E.fromstring(z.read('Contents/section0.xml'))
        scripts = [n.text for n in root.findall('.//hp:script', NS)]
        assert 'y=-x^{2}+4x+1, y=x+1' in scripts
        authored = {b['text'] for page in json.loads(plan.read_text(encoding='utf-8'))['pages'] for b in page['blocks'] if b['type'] == 'text'}
        drawing_texts = {''.join(n.itertext()) for n in root.findall('.//hp:drawText', NS)}
        assert not authored.intersection(drawing_texts)
        assert len(root.findall('.//hp:tc/hp:subList/hp:p', NS)) > 30
    try:
        build(plan, first)
        raise AssertionError('덮어쓰기가 거부되지 않았습니다.')
    except FileExistsError:
        pass
    unresolved = {'pages': [{'blocks': [{'type': 'unresolved', 'review_required': True}]}]}
    scratch = work / 'unresolved.json'
    scratch.write_text(json.dumps(unresolved), encoding='utf-8')
    try:
        build(scratch, work / 'must-not-exist.hwpx')
        raise AssertionError('미검토 원고가 통과했습니다.')
    except ValueError:
        pass
    assert not (work / 'must-not-exist.hwpx').exists()
    print(json.dumps({'passed': True, 'byte_identical': True, 'template_unchanged': True, 'equations': 51, 'pictures': 3, 'scores': 3, 'overwrite_rejected': True, 'unreviewed_rejected': True, 'warnings_need_visual_review': result['warnings']}, ensure_ascii=False, indent=2))
