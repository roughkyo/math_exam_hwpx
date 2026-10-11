"""한글에서 인라인 수식의 실제 폭·높이·기준선을 측정한 새 원고를 만듭니다."""
from pathlib import Path
import argparse
import json
import sys
import os
import zipfile
from lxml import etree as E
from hwpx_shapes import NS
from layout_guards import equation_guard, normalize_script


def measure(plan_path, output):
    if sys.platform != 'win32':
        raise RuntimeError('자동 수식 측정에는 Windows 한글이 필요합니다. 다른 OS에서는 검증된 예제 치수 또는 한글에서 측정한 치수를 입력하세요.')
    plan_path, output = Path(plan_path).resolve(), Path(output).resolve()
    native = output.with_suffix('.measurement.hwpx')
    if output.exists() or native.exists():
        raise FileExistsError('측정 결과는 새 경로로 저장하세요.')
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    keys = {}
    for page in plan['pages']:
        for block in page['blocks']:
            if block['type'] == 'paragraph':
                for run in block['runs']:
                    if 'equation' in run:
                        script = normalize_script(run['equation'])
                        equation_guard(run, script)
                        size = round(run.get('size', block.get('size', 11)) * 100) / 100
                        font = run.get('equation_font', block.get('equation_font', 'HYhwpEQ'))
                        keys[(script, size, font)] = True
    import win32com.client
    h = win32com.client.DispatchEx('HWPFrame.HwpObject')
    try:
        h.XHwpWindows.Item(0).Visible = False
        h.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModuleExample')
        h.SetMessageBoxMode(0x00020000)
        action = h.CreateAction('EquationCreate')
        for script, size, font in keys:
            settings = action.CreateSet()
            action.GetDefault(settings)
            settings.SetItem('String', script)
            settings.SetItem('BaseUnit', round(size * 100))
            settings.SetItem('EqFontName', font)
            if not action.Execute(settings):
                raise RuntimeError('수식 생성 실패: ' + script)
            h.HAction.Run('MoveRight')
            h.HAction.Run('BreakPara')
        output.parent.mkdir(parents=True, exist_ok=True)
        if not h.SaveAs(str(native), 'HWPX', ''):
            raise RuntimeError('측정 문서 저장 실패')
    finally:
        h.Quit()
    with zipfile.ZipFile(native) as z:
        root = E.fromstring(z.read('Contents/section0.xml'))
    measures = {}
    for eq in root.findall('.//hp:equation', NS):
        sz = eq.find('hp:sz', NS)
        key = (eq.find('hp:script', NS).text, int(eq.get('baseUnit')) / 100, eq.get('font'))
        measures[key] = {'width':int(sz.get('width')) / 100, 'height':int(sz.get('height')) / 100, 'baseline':int(eq.get('baseLine')), 'equation_font':eq.get('font'), 'measurement':{'script':key[0], 'size':key[1], 'font':key[2]}}
    if len(measures) != len(keys):
        raise RuntimeError('요청한 수식과 측정 결과 개수가 다릅니다.')
    for page in plan['pages']:
        # 새 원고를 다른 폴더에 두어도 그림 경로가 원본을 가리키도록 맞춥니다.
        if page.get('background'):
            page['background'] = os.path.relpath(plan_path.parent / page['background'], output.parent)
        for block in page['blocks']:
            if block['type'] == 'image':
                block['path'] = os.path.relpath(plan_path.parent / block['path'], output.parent)
            if block['type'] == 'paragraph':
                for run in block['runs']:
                    if 'equation' in run:
                        key = (normalize_script(run['equation']), round(run.get('size', block.get('size', 11)) * 100) / 100, run.get('equation_font', block.get('equation_font', 'HYhwpEQ')))
                        run.update(measures[key])
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan')
    p.add_argument('output')
    a = p.parse_args()
    print(measure(a.plan, a.output))
