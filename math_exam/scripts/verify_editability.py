"""복사본에서 보통 글자 입력으로 본문을 바꾸고 수식 불변을 확인합니다."""
from pathlib import Path
import argparse
import json
import zipfile
from lxml import etree as E
from hwpx_shapes import NS


def inspect(path):
    texts, scripts = [], []
    with zipfile.ZipFile(path) as z:
        for name in sorted(z.namelist(), key=lambda name: (len(name), name)):
            if name.startswith('Contents/section') and name.endswith('.xml'):
                root=E.fromstring(z.read(name))
                texts.extend(t.text or '' for t in root.findall('.//hp:t',NS))
                scripts.extend(t.text or '' for t in root.findall('.//hp:script',NS))
    return ''.join(texts), scripts


def verify(source, output, search, replacement):
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists() or output.with_suffix('.json').exists():
        raise FileExistsError(output)
    before,eq_before=inspect(source)
    if search not in before or replacement in before:
        raise ValueError('찾을 본문이 존재하고 시험 대체 문구는 아직 없어야 합니다.')
    import win32com.client
    h=win32com.client.DispatchEx('HWPFrame.HwpObject')
    try:
        h.XHwpWindows.Item(0).Visible=False
        h.RegisterModule('FilePathCheckDLL','FilePathCheckerModuleExample')
        h.SetMessageBoxMode(0x00020000)
        if not h.Open(str(source),'HWPX','forceopen:true'):
            raise RuntimeError('한글 열기 실패')
        h.HAction.Run('MoveDocBegin')
        action=h.CreateAction('RepeatFind')
        params=action.CreateSet()
        action.GetDefault(params)
        params.SetItem('FindString',search)
        params.SetItem('IgnoreMessage',1)
        params.SetItem('Direction',0)
        if not action.Execute(params):
            raise RuntimeError('일반 본문 찾기에 실패했습니다.')
        action=h.CreateAction('InsertText')
        params=action.CreateSet()
        action.GetDefault(params)
        params.SetItem('Text',replacement)
        if not action.Execute(params):
            raise RuntimeError('보통 텍스트 입력에 실패했습니다.')
        if not h.SaveAs(str(output),'HWPX',''):
            raise RuntimeError('시험 복사본 저장 실패')
    finally:
        h.Quit()
    after,eq_after=inspect(output)
    # 찾기 결과 한 곳만 바뀌고 나머지 본문과 수식 순서가 유지되어야 합니다.
    positions = []
    start = 0
    while True:
        index = before.find(search, start)
        if index < 0:
            break
        positions.append(index)
        start = index + len(search)
    assert any(after == before[:index] + replacement + before[index + len(search):] for index in positions), '시험 대상 이외의 본문이 변경되었습니다.'
    assert eq_before==eq_after,'본문 수정 중 수식이 변경되었습니다.'
    result={'passed':True,'search':search,'replacement':replacement,'equations_unchanged':len(eq_after),'equation_order_unchanged':True,'unrelated_text_unchanged':True,'method':'Hancom RepeatFind and InsertText in a separate copy'}
    output.with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source')
    p.add_argument('output')
    p.add_argument('--search',required=True)
    p.add_argument('--replacement',required=True)
    a=p.parse_args()
    print(json.dumps(verify(a.source,a.output,a.search,a.replacement),ensure_ascii=False))
