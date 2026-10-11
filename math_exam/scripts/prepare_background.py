"""검토된 문자 영역만 지운 PDF 그림·프레임을 원래 쪽 비율로 저장합니다."""
from pathlib import Path
import argparse
import json
import fitz


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source')
    p.add_argument('regions', help='JSON: {"page": 1, "remove_boxes": [[x0,y0,x1,y1], ...]}')
    p.add_argument('output')
    a = p.parse_args()
    out = Path(a.output)
    if out.exists():
        raise FileExistsError(out)
    spec = json.loads(Path(a.regions).read_text(encoding='utf-8'))
    doc = fitz.open(a.source)
    page = doc[spec['page'] - 1]
    # 이미지와 벡터 선은 지우지 않습니다. 숨은 글자/윤곽선은 출력 후 별도 확인합니다.
    for box in spec['remove_boxes']:
        page.add_redact_annot(fitz.Rect(box), fill=False)
    page.apply_redactions(images=0, graphics=0, text=0)
    page.get_pixmap(matrix=fitz.Matrix(5, 5), alpha=False).save(out)
