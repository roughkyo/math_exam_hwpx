"""PDF의 글자 좌표와 원본 지면을 추출합니다. 수식 판독은 검토 대상으로 남깁니다."""
from pathlib import Path
import argparse
import json
import fitz


def extract(source, destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    source = Path(source).resolve()
    doc = fitz.open(source)
    records = []
    for index, page in enumerate(doc):
        page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(destination / f'page-{index+1:03}.png')
        spans = []
        for block in page.get_text('rawdict')['blocks']:
            for line_index, line in enumerate(block.get('lines', [])):
                for span in line['spans']:
                    spans.append({'text': ''.join(c['c'] for c in span['chars']), 'bbox': span['bbox'], 'origin': span['origin'], 'font': span['font'], 'size': span['size'], 'line_bbox': line['bbox'], 'chars': span['chars'], 'math_candidate': 'EQ' in span['font'].upper()})
        records.append({'page': index + 1, 'paper': [page.rect.width, page.rect.height], 'spans': spans, 'needs_visual_transcription': not spans})
    (destination / 'extracted.json').write_text(json.dumps({'source': source.name, 'pages': records}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('추출 쪽 수:', len(records))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source')
    p.add_argument('destination')
    a = p.parse_args()
    extract(a.source, a.destination)
