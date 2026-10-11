"""실제 배포 ZIP의 검증기가 내용 변조와 오래된 치수를 잡는지 확인합니다."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import zipfile
import hashlib
from lxml import etree as E

NS = {'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph'}


def changed_hwpx(source, target, kind):
    with zipfile.ZipFile(source) as z:
        data = {name:z.read(name) for name in z.namelist()}
    root = E.fromstring(data['Contents/section0.xml'])
    if kind == 'equation':
        root.find('.//hp:script', NS).text = 'y=0'
    else:
        node = next(t for t in root.findall('.//hp:t', NS) if '곡선과 직선으로' in (t.text or ''))
        node.text = '원고와 다른 문장'
    data['Contents/section0.xml'] = E.tostring(root, encoding='UTF-8', xml_declaration=True)
    with zipfile.ZipFile(target, 'x') as z:
        z.writestr('mimetype', data.pop('mimetype'), compress_type=zipfile.ZIP_STORED)
        for name, value in data.items():
            z.writestr(name, value, compress_type=zipfile.ZIP_DEFLATED)


def run(package, work):
    package, work = Path(package).resolve(), Path(work).resolve()
    work.mkdir(exist_ok=False, parents=True)
    results = {}
    # 정상 원고를 먼저 통과시켜, 검증기가 모든 입력을 거부하는 오류를 구별합니다.
    for name in ('area-three', 'regression-layout', '2026-10-11-stretch-layout', '2026-10-11-native-boundaries'):
        proc = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(package/'scripts/validate_exam.py'), str(package/'examples'/f'{name}.hwpx'), str(work/(name+'-positive')), '--plan', str(package/'examples'/f'{name}.json'), '--output-pdf', str(package/'examples'/f'{name}.pdf')], capture_output=True, text=True, encoding='utf-8')
        (work/(name+'-positive.log')).write_text(proc.stdout + proc.stderr, encoding='utf-8')
        results[name + '_accepted'] = proc.returncode == 0
    for kind in ('equation', 'text'):
        path = work / (kind + '.hwpx')
        changed_hwpx(package/'examples/area-three.hwpx', path, kind)
        proc = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(package/'scripts/validate_exam.py'), str(path), str(work/(kind+'-report')), '--plan', str(package/'examples/area-three.json')], capture_output=True, text=True, encoding='utf-8')
        (work/(kind+'.log')).write_text(proc.stdout + proc.stderr, encoding='utf-8')
        expected = '수식 내용/순서' if kind == 'equation' else '본문의 내용/순서'
        results[kind + '_change_rejected'] = proc.returncode != 0 and expected in proc.stderr
    plan = json.loads((package/'examples/2026-10-11-native-boundaries.json').read_text(encoding='utf-8'))
    plan['pages'][0]['blocks'][0]['runs'][0]['equation'] = 'sin theta+cos theta'
    changed = work / 'stale-metrics.json'
    changed.write_text(json.dumps(plan, ensure_ascii=False), encoding='utf-8')
    proc = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(package/'scripts/build_exam.py'), str(changed), str(work/'stale-metrics.hwpx')], capture_output=True, text=True, encoding='utf-8')
    results['stale_equation_metrics_rejected'] = proc.returncode != 0
    from layout_guards import metrics_guard, normalize_script
    assert normalize_script('x^2-1') == 'x^{2}-1'
    assert normalize_script('a_12+3') == 'a_{12}+3'
    results['measurement_builder_normalization_agrees'] = True
    original = json.loads((package/'examples/2026-10-11-native-boundaries.json').read_text(encoding='utf-8'))
    run = original['pages'][0]['blocks'][0]['runs'][0]
    settings = dict(original['pages'][0]['blocks'][0], **run, script=run['equation'])
    metrics_guard(settings)
    for key, value in (('size', 19), ('equation_font', 'OtherFont'), ('width', 0), ('height', -1)):
        try:
            metrics_guard(dict(settings, **{key:value}))
        except ValueError:
            results[key + '_invalid_measurement_rejected'] = True
        else:
            results[key + '_invalid_measurement_rejected'] = False
    install = work / 'installed'
    subprocess.run([sys.executable, '-X', 'utf8', '-B', str(package/'scripts/install_skill.py'), '--engine', 'codex', '--project', str(install)], check=True, capture_output=True)
    target = install / '.agents/skills/math-exam'
    manifest = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
    results['installed_manifest_matches'] = all(hashlib.sha256((target/n).read_bytes()).hexdigest() == h for n,h in manifest.items())
    (work/'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return all(results.values())


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('work')
    a = p.parse_args()
    raise SystemExit(0 if run(Path(__file__).resolve().parent.parent, a.work) else 1)
