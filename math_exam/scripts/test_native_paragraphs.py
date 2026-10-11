"""본문의 수식화·함수명 오조판·인라인 치수 누락을 실제 빌더에서 거부합니다."""
from pathlib import Path
import argparse
import json
import zipfile
from lxml import etree as E
from build_exam import build, NS, PACKAGE


def run(work):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=False)
    bad = [
        {'type':'equation','script':'a_n-3'},
        {'type':'equation','script':'X가 0 또는 1인 경우'},
        {'type':'equation','script':'{rm {sin}} it ~x'},
        {'type':'equation','script':'sin ~x'},
        {'type':'equation','script':'log _{5} ~3'},
        {'type':'equation','script':'(a,~b)'},
        {'type':'paragraph','runs':[{'text':'함수 '},{'equation':'sin x'},{'text':'의 값'}]}
    ]
    for i, block in enumerate(bad):
        block.update(x=60,y=240,width=300,height=30)
        path = work / f'bad-{i}.json'
        path.write_text(json.dumps({'pages':[{'blocks':[block]}]},ensure_ascii=False),encoding='utf-8')
        try:
            build(path,work/f'bad-{i}.hwpx')
        except ValueError:
            pass
        else:
            raise AssertionError(f'잘못된 입력 {i}를 통과시켰습니다.')
        assert not (work/f'bad-{i}.hwpx').exists()
    output = build(PACKAGE/'examples/2026-10-11-native-boundaries.json',work/'native.hwpx')
    with zipfile.ZipFile(output) as z:
        root=E.fromstring(z.read('Contents/section0.xml'))
    scripts=[n.text or '' for n in root.findall('.//hp:script',NS)]
    assert 'tan theta' in scripts
    text=''.join(t.text or '' for t in root.findall('.//hp:t',NS))
    assert '흰 공 1개와 검은 공 2개' in text
    inline=root.findall('.//hp:tc/hp:subList/hp:p/hp:run/hp:equation',NS)
    assert len(inline)==len(scripts)
    assert all(e.find('hp:pos',NS).get('treatAsChar')=='1' for e in inline)
    print(json.dumps({'passed':True,'rejected_bad_inputs':len(bad),'inline_equations':len(inline),'body_is_native_text':True},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',required=True)
    run(p.parse_args().work)
