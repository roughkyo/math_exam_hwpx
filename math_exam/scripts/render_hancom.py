"""Windows 한글에서 읽기 전용 원고를 새 HWPX/PDF로 저장합니다."""
from pathlib import Path
import argparse
import sys


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source')
    p.add_argument('pdf')
    p.add_argument('--native-hwpx')
    a = p.parse_args()
    if sys.platform != 'win32':
        raise SystemExit('실제 한글 렌더링은 Windows와 설치된 한글이 필요합니다. 구조 검증은 다른 OS에서도 가능합니다.')
    outputs = [Path(a.pdf).resolve()]
    if a.native_hwpx:
        outputs.append(Path(a.native_hwpx).resolve())
    for out in outputs:
        if out.exists():
            raise FileExistsError(out)
        out.parent.mkdir(parents=True, exist_ok=True)
    import pythoncom
    import win32com.client
    h = win32com.client.dynamic.Dispatch(pythoncom.CoCreateInstance('HWPFrame.HwpObject', None, pythoncom.CLSCTX_LOCAL_SERVER, pythoncom.IID_IDispatch))
    try:
        h.XHwpWindows.Item(0).Visible = False
        # 사용자 PC에 등록된 보안 모듈이 없으면 한글의 파일 접근 확인이 나타날 수 있습니다.
        h.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModuleExample')
        h.SetMessageBoxMode(0x00020000)
        if not h.Open(str(Path(a.source).resolve()), 'HWPX', 'forceopen:true'):
            raise RuntimeError('한글 열기 실패')
        if a.native_hwpx and not h.SaveAs(str(outputs[1]), 'HWPX', ''):
            raise RuntimeError('HWPX 저장 실패')
        if not h.SaveAs(str(outputs[0]), 'PDF', ''):
            raise RuntimeError('PDF 저장 실패')
    finally:
        h.Quit()
    print(outputs[0])
