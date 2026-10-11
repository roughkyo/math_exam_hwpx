"""보통 한글 문단 안에 본문과 인라인 수식을 서로 다른 개체로 만듭니다."""
from copy import deepcopy
import re
import hwpx_shapes as m
from layout_guards import metrics_guard

NS = m.NS


def borderless_style(header):
    borders = header.find('.//hh:borderFills', NS)
    border = deepcopy(borders[0])
    ident = max(int(n.get('id')) for n in borders) + 1
    border.set('id', str(ident))
    for child in list(border):
        if m.E.QName(child).localname == 'fillBrush':
            border.remove(child)
        elif 'type' in child.attrib:
            child.set('type', 'NONE')
    borders.append(border)
    borders.set('itemCnt', str(len(borders)))
    return ident


def paragraph(parent, block, para_id, border_id, style, equation):
    # 한 셀의 일반 문단이므로 본문을 수식 편집기나 그리기 글상자로 열지 않습니다.
    parts = block.get('runs', [{'text': block.get('text', '')}])
    equations = [dict(block, **part) for part in parts if 'equation' in part]
    # 수식 실측 높이를 셀에 반영하고 위쪽 기호가 잘리지 않도록 여백을 둡니다.
    padding = 2 if equations else 0
    ascent = max([part.get('size', block.get('size', 11)) * .85 for part in parts if 'text' in part] + [part.get('height', 0) * part.get('baseline', 85) / 100 for part in equations] + [0])
    descent = max([part.get('size', block.get('size', 11)) * .25 for part in parts if 'text' in part] + [part.get('height', 0) * (1 - part.get('baseline', 85) / 100) for part in equations] + [0])
    if block['y'] < padding:
        raise ValueError('수식 위쪽 여백이 종이 밖으로 나갑니다. 문단을 아래로 옮기세요.')
    w = m.hu(block.get('width', 300))
    h = m.hu(max(block.get('height', 25), ascent + descent + 2 * padding))
    table = m.el('hp:tbl', parent, id=m.uid(), zOrder=2, numberingType='TABLE', textWrap='IN_FRONT_OF_TEXT', textFlow='BOTH_SIDES', lock=0, dropcapstyle='None', pageBreak='NONE', repeatHeader=0, rowCnt=1, colCnt=1, cellSpacing=0, borderFillIDRef=border_id, noAdjust=0)
    m.el('hp:sz', table, width=w, widthRelTo='ABSOLUTE', height=h, heightRelTo='ABSOLUTE', protect=0)
    m.position(table, block['x'], block['y'] - padding)
    m.el('hp:inMargin', table, left=0, right=0, top=0, bottom=0)
    tr = m.el('hp:tr', table)
    tc = m.el('hp:tc', tr, name='', header=0, hasMargin=1, protect=0, editable=1, dirty=0, borderFillIDRef=border_id)
    sub = m.el('hp:subList', tc, id='', textDirection='HORIZONTAL', lineWrap='BREAK', vertAlign='TOP', linkListIDRef=0, linkListNextIDRef=0, textWidth=0, textHeight=0, hasTextRef=0, hasNumRef=0)
    p = m.el('hp:p', sub, id=m.uid(), paraPrIDRef=para_id, styleIDRef=0, pageBreak=0, columnBreak=0, merged=0)
    previous = None
    for part in parts:
        if part.get('review_required'):
            raise ValueError('문단 안에 원본 대조가 끝나지 않은 run이 있습니다.')
        if ('text' in part) == ('equation' in part):
            raise ValueError('각 run에는 text 또는 equation 중 하나만 필요합니다.')
        settings = dict(block, **part)
        after_math = previous and 'equation' in previous and re.match('[가-힣]', part.get('text', ''))
        before_math = previous and 'equation' in part and re.search('[가-힣]$', previous.get('text', ''))
        if after_math or before_math:
            gap = m.el('hp:run', p, charPrIDRef=style(dict(block, size=5, bold=False)))
            m.el('hp:t', gap).text = ' '
        run = m.el('hp:run', p, charPrIDRef=style(settings))
        if 'text' in part:
            # 쉼표·조사·공백은 본문으로 보존합니다. 수식 안에 옮기지 않습니다.
            m.el('hp:t', run).text = part['text']
        else:
            settings['script'] = part['equation']
            metrics_guard(settings)
            node = equation(settings)
            node.set('textWrap', 'TOP_AND_BOTTOM')
            node.find('hp:pos', NS).attrib.update({'treatAsChar':'1', 'affectLSpacing':'1', 'flowWithText':'1', 'allowOverlap':'0', 'vertRelTo':'PARA', 'horzRelTo':'COLUMN', 'horzOffset':'0', 'vertOffset':'0'})
            run.append(node)
        previous = part
    m.el('hp:cellAddr', tc, colAddr=0, rowAddr=0)
    m.el('hp:cellSpan', tc, colSpan=1, rowSpan=1)
    m.el('hp:cellSz', tc, width=w, height=h)
    m.el('hp:cellMargin', tc, left=0, right=0, top=m.hu(padding), bottom=m.hu(padding))
    return table
