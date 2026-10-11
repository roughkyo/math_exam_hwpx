"""검증된 기존 수학 HWPX 작업에서 필요한 개체 생성 함수만 추출했습니다."""

from lxml import etree as E

NS = {'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph','hc':'http://www.hancom.co.kr/hwpml/2011/core','hh':'http://www.hancom.co.kr/hwpml/2011/head','hs':'http://www.hancom.co.kr/hwpml/2011/section','opf':'http://www.idpf.org/2007/opf/'}

COUNTER = 3100000000

def el(tag_name, parent=None, **attrs):
    prefix, local = tag_name.split(':')
    tag = '{' + NS[prefix] + '}' + local
    values = {k: str(v) for k, v in attrs.items()}
    if parent is None:
        return E.Element(tag, values)
    return E.SubElement(parent, tag, values)

def uid():
    global COUNTER
    COUNTER += 1
    return COUNTER

def hu(value):
    return round(value * 100)

def common_shape(node, width, height):
    el('hp:offset', node, x=0, y=0)
    el('hp:orgSz', node, width=width, height=height)
    el('hp:curSz', node, width=width, height=height)
    el('hp:flip', node, horizontal=0, vertical=0)
    el('hp:rotationInfo', node, angle=0, centerX=width//2, centerY=height//2, rotateimage=1)
    ri = el('hp:renderingInfo', node)
    for name in ('transMatrix', 'scaMatrix', 'rotMatrix'):
        el('hc:'+name, ri, e1=1, e2=0, e3=0, e4=0, e5=1, e6=0)

def position(node, x, y):
    el('hp:pos', node, treatAsChar=0, affectLSpacing=0, flowWithText=0, allowOverlap=1, holdAnchorAndSO=0, vertRelTo='PAPER', horzRelTo='PAPER', vertAlign='TOP', horzAlign='LEFT', vertOffset=hu(y), horzOffset=hu(x))
    el('hp:outMargin', node, left=0, right=0, top=0, bottom=0)

def image_shape(parent, image_id, width, height):
    w, h = hu(width), hu(height)
    node = el('hp:pic', parent, id=uid(), zOrder=0, numberingType='PICTURE', textWrap='BEHIND_TEXT', textFlow='BOTH_SIDES', lock=1, dropcapstyle='None', href='', groupLevel=0, instid=uid(), reverse=0)
    common_shape(node, w, h)
    el('hc:img', node, binaryItemIDRef=image_id, bright=0, contrast=0, effect='REAL_PIC', alpha=0)
    rect = el('hp:imgRect', node)
    for i, (x,y) in enumerate(((0,0),(w,0),(w,h),(0,h))):
        el('hc:pt'+str(i), rect, x=x, y=y)
    el('hp:imgClip', node, left=0, right=w, top=0, bottom=h)
    el('hp:inMargin', node, left=0, right=0, top=0, bottom=0)
    el('hp:imgDim', node, dimwidth=w, dimheight=h)
    el('hp:effects', node)
    el('hp:sz', node, width=w, widthRelTo='ABSOLUTE', height=h, heightRelTo='ABSOLUTE', protect=1)
    position(node, 0, 0)
    el('hp:shapeComment', node).text = '원본 PDF의 본문·선·그래프·그림. 수식 글자는 제외.'
