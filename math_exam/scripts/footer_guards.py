"""저작권 바닥글의 본문 중복 및 양식과의 이중 배치를 막습니다."""
from copy import deepcopy
import re


def copyright_text(block):
    if block.get('type') not in ('text', 'paragraph'):
        return ''
    runs = block.get('runs', [{'text': block.get('text', '')}])
    if any('equation' in run for run in runs):
        return ''
    text = ''.join(run.get('text', '') for run in runs)
    compact = re.sub(r'\s+', '', text)
    return compact if '문제지' in compact and '저작권' in compact else ''


def prepare_footers(plan, paper_height):
    result = deepcopy(plan)
    presence = []
    for page in result['pages']:
        seen = set()
        kept = []
        for block in page['blocks']:
            text = copyright_text(block) if block.get('y', 0) >= paper_height * .85 else ''
            if text and text in seen:
                continue
            if text:
                seen.add(text)
            kept.append(block)
        page['blocks'] = kept
        presence.append(bool(seen))
    # 마스터는 여러 쪽에서 공유되므로 일부 쪽만 지우면 다른 쪽의 바닥글이 사라집니다.
    if any(presence) and not all(presence):
        raise ValueError('저작권 바닥글은 모든 쪽의 본문에 넣거나 모두 양식에 맡기세요. 혼합 배치는 바닥글 누락 위험이 있습니다.')
    return result, all(presence) and bool(presence)


def remove_template_copyright(root, ns):
    for para in list(root.findall('.//hp:p', ns)):
        if para.findall('.//hp:p', ns):
            continue
        text = ''.join(para.itertext())
        if '문제지' in text and '저작권' in text:
            # 위치·테두리·쪽번호는 보존하고 해당 문구만 비웁니다.
            for node in para.findall('.//hp:t', ns):
                node.text = ''


def check_background_footer(page, paper, base):
    if not page.get('background'):
        return
    from PIL import Image
    import numpy as np
    with Image.open(base / page['background']) as image:
        rgb = image.convert('RGB')
        for block in page['blocks']:
            if block.get('y', 0) < paper[1] * .85 or not copyright_text(block):
                continue
            rect = block.get('source_bbox', [block['x'], block['y'], block['x'] + block.get('width', 300), block['y'] + block.get('height', 25)])
            x0, y0, x1, y1 = rect
            box = (max(0, int((x0-2)*rgb.width/paper[0])), max(0, int((y0-2)*rgb.height/paper[1])), min(rgb.width, int((x1+2)*rgb.width/paper[0])+1), min(rgb.height, int((y1+2)*rgb.height/paper[1])+1))
            pixels = np.asarray(rgb.crop(box))
            if pixels.size and (pixels.min(axis=2) < 220).sum() > 5:
                raise ValueError('바닥글 배경에 글자 또는 선이 남았습니다. 원본을 확인하고 prepare_background.py의 clear_boxes로 해당 문구만 지우세요.')
