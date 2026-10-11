"""바닥글 중복과 작은 셀의 상단 수식 잘림에 대한 구조 회귀 검사."""
from pathlib import Path
import argparse
import json
import zipfile
import fitz
from lxml import etree as E
from build_exam import build, NS
from footer_guards import prepare_footers, remove_template_copyright
from layout_guards import pdf_layout


def run(work, render=False):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=False)
    text = '이 문제지에 관한 저작권은 예제 제작자에게 있습니다.'
    footer = {'type':'text', 'text':text, 'x':350, 'y':1050, 'width':370, 'height':20}
    metric = {'equation':'vec {a} =(k,2)', 'width':39.4, 'height':13.5, 'baseline':87, 'equation_font':'HYhwpEQ', 'measurement':{'script':'vec {a} =(k,2)', 'size':11.0, 'font':'HYhwpEQ'}}
    para = {'type':'paragraph', 'x':80, 'y':240, 'width':300, 'height':11, 'size':11, 'runs':[{'text':'두 벡터 '},metric,{'text':'의 값'}]}
    reference = {'type':'equation', 'x':80, 'y':300, 'width':39.4, 'height':13.5, 'size':11, 'script':metric['equation'], 'baseline':87, 'equation_font':'HYhwpEQ'}
    plan = {'pages':[{'blocks':[para, reference, footer, dict(footer, x=351)]}]}
    clean, body = prepare_footers(plan, 1116.85)
    assert body and len(clean['pages'][0]['blocks']) == 3
    assert len(plan['pages'][0]['blocks']) == 4
    mixed = {'pages':[{'blocks':[footer]}, {'blocks':[]}]}
    try:
        prepare_footers(mixed, 1116.85)
    except ValueError:
        pass
    else:
        raise AssertionError('공유 마스터 바닥글의 일부 쪽 유실 위험을 허용했습니다.')
    source = work/'plan.json'
    source.write_text(json.dumps(plan,ensure_ascii=False),encoding='utf-8')
    hwpx = build(source, work/'example.hwpx')
    with zipfile.ZipFile(hwpx) as archive:
        root = E.fromstring(archive.read('Contents/section0.xml'))
    equation = root.find('.//hp:equation', NS)
    assert equation.find('hp:pos', NS).get('affectLSpacing') == '1'
    cell = equation.getparent().getparent().getparent().getparent()
    assert E.QName(cell).localname == 'tc'
    margin = cell.find('hp:cellMargin', NS)
    assert int(margin.get('top')) >= 200 and int(margin.get('bottom')) >= 200
    assert int(cell.find('hp:cellSz', NS).get('height')) > 1350
    assert ''.join(root.itertext()).count(text) == 1
    # 실제 PDF 중복 횟수 검사가 기존의 존재 여부 검사보다 강한지 확인합니다.
    document = fitz.open()
    page = document.new_page()
    for y in (700, 701):
        page.insert_text((50,y), 'Copyright example', fontsize=10)
    pdf = work/'duplicate.pdf'
    document.save(pdf)
    spec = {'layout_checks':[{'page':1,'text':'Copyright example','region':[40,680,250,730],'expected_occurrences':1}]}
    result = pdf_layout(pdf,spec)
    assert not result['passed'] and result['checks'][0]['occurrences']==2
    # 글자가 포함된 배경은 다시 본문을 올리기 전에 거부해야 합니다.
    from PIL import Image, ImageDraw
    from footer_guards import check_background_footer
    background = Image.new('RGB', (771,1117), 'white')
    ImageDraw.Draw(background).rectangle((355,1052,360,1060),fill='blue')
    background.save(work/'background.png')
    try:
        check_background_footer({'background':'background.png','blocks':[footer]},[771,1117],work)
    except ValueError:
        pass
    else:
        raise AssertionError('배경 바닥글의 잉크를 놓쳤습니다.')
    ink_ratio = None
    if render:
        import subprocess
        import sys
        import numpy as np
        output = work/'native.pdf'
        subprocess.run([sys.executable,str(Path(__file__).with_name('render_hancom.py')),str(hwpx),str(output)],check=True)
        with fitz.open(output) as doc:
            # 동일 HYhwpEQ 수식을 독립 개체로 출력한 화살표를 대조군으로 사용합니다.
            arrows = [char for span in doc[0].get_texttrace() if span['font'].lower()=='hyhwpeq' for char in span['chars'] if char[0] in (0xe06d,0xe06e)]
            assert len(arrows)==4, '회귀 예제의 화살표 글리프 구성이 달라졌습니다.'
            counts = []
            for group in (arrows[:2],arrows[2:]):
                rect = fitz.Rect(group[0][3]) | fitz.Rect(group[1][3])
                rect.y1 = rect.y0 + rect.height * .4
                pix = doc[0].get_pixmap(matrix=fitz.Matrix(12,12),clip=rect,colorspace=fitz.csGRAY)
                counts.append(int((np.frombuffer(pix.samples,dtype=np.uint8)<180).sum()))
            assert counts[1]>20, '비교 기준 화살표의 잉크가 없습니다.'
            ink_ratio = counts[0]/counts[1]
            assert .85 <= ink_ratio <= 1.15, f'인라인 화살표 상단 잘림 가능성: {ink_ratio}'
            assert ''.join(doc[0].get_text(flags=0).split()).count(''.join(text.split()))==1
    print(json.dumps({'passed':True,'arrow_ink_ratio':ink_ratio,'duplicate_footer_removed':True,'mixed_ownership_rejected':True,'equation_clearance_reserved':True,'rendered_duplicate_detected':True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',required=True)
    parser.add_argument('--render',action='store_true',help='Windows 한글로 화살표 잉크와 바닥글 개수를 검사')
    args=parser.parse_args()
    run(args.work,args.render)
