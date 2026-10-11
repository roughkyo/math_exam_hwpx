"""검토한 페이지 원고를 편집 가능한 본문·한글 수식·그림으로 조립합니다."""
from pathlib import Path
from copy import deepcopy
import argparse
import json
import re
import zipfile

from lxml import etree as E
from PIL import Image
import hwpx_shapes as m
from layout_guards import equation_guard, normalize_script
import native_paragraphs

PACKAGE = Path(__file__).resolve().parent.parent
NS = m.NS


def xml(data):
    return E.fromstring(data, E.XMLParser(resolve_entities=False, no_network=True))


def serialize(tree):
    return E.tostring(tree, encoding='UTF-8', xml_declaration=True, standalone=True)


def build(plan_path, output, template=None):
    # 같은 프로세스에서 재호출해도 개체 ID가 달라지지 않도록 초기화합니다.
    m.COUNTER = 3100000000
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    template = Path(template or PACKAGE / 'assets/forms/default_exam.hwpx').resolve()
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('기존 결과물은 덮어쓰지 않습니다: ' + str(output))
    with zipfile.ZipFile(template) as z:
        data = {n: z.read(n) for n in z.namelist()}
    original = xml(data['Contents/section0.xml'])
    header = xml(data['Contents/header.xml'])
    hpf = xml(data['Contents/content.hpf'])
    seed = original.find('.//hp:equation', NS)
    if seed is None:
        raise ValueError('사용자 양식에 수식 개체가 없습니다. 한글에서 수식 하나를 넣은 복사본을 준비하세요.')
    adapter = plan.get('adapter', {})
    if template != (PACKAGE / 'assets/forms/default_exam.hwpx').resolve() and not adapter:
        raise ValueError('사용자 양식은 profile 후 adapter를 명시해야 합니다. 기본 문단 번호를 추측하지 않습니다.')
    scaffold_index = adapter.get('scaffold_paragraph', 0)
    scaffold = original[scaffold_index]
    if scaffold.find('.//hp:secPr', NS) is None or scaffold.find('.//hp:colPr', NS) is None:
        raise ValueError('scaffold에 secPr와 colPr가 모두 있어야 지면 크기가 유지됩니다.')
    pagepr = scaffold.find('.//hp:pagePr', NS)
    paper = [int(pagepr.get('width')) / 100, int(pagepr.get('height')) / 100]
    section = E.Element(original.tag, nsmap=original.nsmap)
    header.set('secCnt', '1')
    manifest = hpf.find('opf:manifest', NS)
    for node in list(manifest):
        if re.fullmatch(r'section\d+', node.get('id', '')) and node.get('id') != 'section0':
            manifest.remove(node)
    for node in hpf.findall('.//opf:itemref', NS):
        if re.fullmatch(r'section\d+', node.get('idref', '')) and node.get('idref') != 'section0':
            node.getparent().remove(node)
    for name in list(data):
        if re.fullmatch(r'Contents/section\d+\.xml', name) and name != 'Contents/section0.xml':
            data.pop(name)
    title = hpf.find('.//opf:title', NS)
    if title is not None:
        title.text = plan.get('title', '수학 문제지')
    if template == (PACKAGE / 'assets/forms/default_exam.hwpx').resolve():
        for name in list(data):
            if re.fullmatch(r'Contents/masterpage\d+\.xml', name):
                master = xml(data[name])
                for t in master.findall('.//hp:t', NS):
                    if t.text == '20':
                        t.text = str(len(plan['pages']))
                data[name] = serialize(master)
    paras = header.find('.//hh:paraProperties', NS)
    para = deepcopy(paras[0])
    para_id = max(int(c.get('id')) for c in paras) + 1
    para.set('id', str(para_id))
    para.find('hh:align', NS).set('horizontal', 'LEFT')
    for node in para.iter():
        if E.QName(node).localname in ('intent', 'left', 'right', 'prev', 'next') and 'value' in node.attrib:
            node.set('value', '0')
    paras.append(para)
    paras.set('itemCnt', str(len(paras)))
    para.set('snapToGrid', '0')
    for node in para.iter():
        if E.QName(node).localname == 'lineSpacing':
            node.set('type', 'PERCENT')
            node.set('value', '100')
    border_id = native_paragraphs.borderless_style(header)
    chars = header.find('.//hh:charProperties', NS)
    styles = {}

    def style(block):
        key = (block.get('size', 11), block.get('bold', False), block.get('ratio', 100))
        if key not in styles:
            cp = deepcopy(chars[adapter.get('char_seed', 0)])
            cid = max(int(c.get('id')) for c in chars) + 1
            cp.set('id', str(cid))
            cp.set('height', str(round(key[0] * 100)))
            for local, value in [('ratio', key[2]), ('spacing', 0), ('relSz', 100), ('offset', 0)]:
                child = cp.find('hh:' + local, NS)
                for a in child.attrib:
                    child.set(a, str(value))
            bold = cp.find('hh:bold', NS)
            if bold is not None:
                cp.remove(bold)
            if key[1]:
                m.el('hh:bold', cp)
            chars.append(cp)
            styles[key] = cid
        return styles[key]

    def picture(run, block, index):
        path = (plan_path.parent / block['path']).resolve()
        with Image.open(path) as im:
            if im.format != 'PNG':
                raise ValueError('그림은 PNG로 준비하세요: ' + str(path))
        ident = 'math_exam_image_' + str(index)
        name = 'BinData/' + ident + '.png'
        data[name] = path.read_bytes()
        m.el('opf:item', manifest, id=ident, href=name, **{'media-type': 'image/png', 'isEmbeded': '1'})
        m.image_shape(run, ident, block['width'], block['height'])
        node = run[-1]
        node.find('hp:pos', NS).set('horzOffset', str(m.hu(block['x'])))
        node.find('hp:pos', NS).set('vertOffset', str(m.hu(block['y'])))
        node.set('lock', '0')
        node.find('hp:shapeComment', NS).text = '그림 개체; 표기 본문과 수식은 별도 편집 개체로 작성'

    def equation(block):
        script = normalize_script(block['script'])
        equation_guard(block, script)
        node = deepcopy(seed)
        node.set('id', str(m.uid()))
        node.set('zOrder', '3')
        node.set('baseUnit', str(round(block.get('size', 11) * 100)))
        if 'baseline' in block:
            node.set('baseLine', str(block['baseline']))
        if 'equation_font' in block:
            node.set('font', block['equation_font'])
        node.set('textWrap', 'IN_FRONT_OF_TEXT')
        node.find('hp:script', NS).text = script
        node.find('hp:sz', NS).set('width', str(m.hu(block.get('width', 100))))
        node.find('hp:sz', NS).set('height', str(m.hu(block.get('height', 25))))
        for name in ('hp:pos', 'hp:outMargin'):
            node.remove(node.find(name, NS))
        m.position(node, block.get('x', 0), block.get('y', 0))
        return node

    image_count = 0
    for page_no, page in enumerate(plan['pages']):
        p = deepcopy(scaffold)
        p.set('id', str(m.uid()))
        p.set('pageBreak', '0' if page_no == 0 else '1')
        # 양식의 첫 문단에 고정된 구조만 남기고 기존 문항은 가져오지 않습니다.
        keep = adapter.get('keep_children', [0, 1])
        for i, child in enumerate(list(p)):
            if i not in keep:
                p.remove(child)
        for node in p.findall('hp:linesegarray', NS):
            p.remove(node)
        if page_no:
            for node in p.findall('.//hp:secPr', NS):
                node.getparent().remove(node)
        col = p.find('.//hp:colPr', NS)
        col.set('colCount', '1')
        col.set('sameGap', '0')
        if page.get('background'):
            # 원본 PDF 프레임 모드에서는 양식 머리말과 마스터를 중복 표시하지 않습니다.
            for node in p.findall('.//hp:tbl', NS):
                node.getparent().remove(node)
            for node in p.findall('.//hp:masterPage', NS):
                node.getparent().remove(node)
        else:
            tables = p.findall('.//hp:tbl', NS)
            if tables:
                ts = tables[0].findall('.//hp:t', NS)
                for i, t in enumerate(ts):
                    t.text = page.get('heading', plan.get('title', '수학 문제지')) if i == 0 else ''
                if page.get('badge') and len(tables) > 1:
                    for i, t in enumerate(tables[1].findall('.//hp:t', NS)):
                        t.text = page['badge'] if i == 0 else ''
        for node in p.findall('.//hp:linesegarray', NS):
            node.getparent().remove(node)
        run = m.el('hp:run', p, charPrIDRef=0)
        m.el('hp:t', run)
        section.append(p)
        # 공개용 새 양식에는 기관 머리말이 없으므로 원고의 제목을 일반 글자로 표시합니다.
        if not page.get('background') and template == (PACKAGE / 'assets/forms/default_exam.hwpx').resolve():
            native_paragraphs.paragraph(run, {'type': 'text', 'text': page.get('heading', plan.get('title', '수학 문제지')), 'x': 85, 'y': 70, 'width': 670, 'height': 28, 'size': 20, 'bold': True}, para_id, border_id, style, equation)
        if page.get('background'):
            image_count += 1
            picture(run, {'path': page['background'], 'x': 0, 'y': 0, 'width': paper[0], 'height': paper[1]}, image_count)
        for block in page['blocks']:
            if block.get('review_required') or block.get('type') == 'unresolved':
                raise ValueError('원본 대조가 끝나지 않은 블록이 있습니다: ' + str(block.get('source_bbox')))
            x, y = block['x'], block['y']
            width, height = block.get('width', 300), block.get('height', 25)
            if x < 0 or y < 0 or x + width > paper[0] or y + height > paper[1]:
                raise ValueError('쪽 경계를 벗어난 블록: ' + str(block))
            if block['type'] in ('text', 'paragraph'):
                native_paragraphs.paragraph(run, block, para_id, border_id, style, equation)
            elif block['type'] == 'equation':
                run.append(equation(block))
            elif block['type'] == 'image':
                image_count += 1
                picture(run, block, image_count)
            else:
                raise ValueError('지원하지 않는 블록 유형: ' + block['type'])
    chars.set('itemCnt', str(len(chars)))
    for name, tree in [('Contents/section0.xml', section), ('Contents/header.xml', header), ('Contents/content.hpf', hpf)]:
        data[name] = serialize(tree)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x') as z:
        mime = zipfile.ZipInfo('mimetype', (2026, 10, 11, 0, 0, 0))
        z.writestr(mime, data.pop('mimetype'), compress_type=zipfile.ZIP_STORED)
        for name, payload in data.items():
            info = zipfile.ZipInfo(name, (2026, 10, 11, 0, 0, 0))
            z.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan')
    parser.add_argument('output')
    parser.add_argument('--template')
    args = parser.parse_args()
    print(build(args.plan, args.output, args.template))
