# 양식과 원고 JSON

`build_exam.py`는 제공 양식의 글꼴·쪽 설정·첫 문단의 프레임/머리말을 재사용한다. 공개본의 기본 양식은 사용자가 지정하고 공개 배포를 허용한 `평가원 수학 양식.hwpx`다. 작성자·최종 저장자 메타데이터만 비웠다. 빌더는 양식의 기존 문제 본문 대신 새 원고를 배치한다.

사용자 양식이 주어지면 Python zipfile/lxml로 ZIP 안 각 section·표·마스터·폰트·secPr·colPr를 조사한다. 공개 패키지는 별도 양파고 스크립트에 의존하지 않는다. 다음 adapter는 기본 예시이며 다른 양식에 그대로 적용하지 않는다.

```json
{
  "title": "새 문제지",
  "adapter": {"scaffold_paragraph": 0, "keep_children": [0, 1], "char_seed": 23},
  "pages": [{
    "heading": "수학 영역",
    "blocks": [
      {"type":"paragraph", "x":60, "y":235, "width":300, "height":25, "size":11,
       "runs":[{"text":"1. 두 사건 "},{"equation":"A"},{"text":", "},{"equation":"B"},{"text":"에 대하여"}]},
      {"type":"image", "path":"graph.png", "x":60, "y":300, "width":290, "height":220}
    ]
  }]
}
```

좌표와 크기는 pagePr의 HWPUNIT을 100으로 나눈 내부 좌표이며 원점은 종이 왼쪽 위다. 기본 양식의 내부 좌표계는 771.02×1116.85이다. 실제 출력 PDF의 크기는 한글에서 출력하여 확인한다. 양식의 용지 처리에 따라 실제 PDF 좌표가 확대될 수 있으므로 둘을 동일하다고 추측하지 않는다. 이미지 경로는 원고 JSON 폴더 기준이다. 각 쪽은 명시적인 pageBreak를 가진다. 본문은 문장 또는 행 단위로 작성하고, 배점 `[3점]`은 하나의 문자열로 둔다. 문항 번호만 별도 굵게 개체로 만드는 것이 좋다. 자간 문제가 있는 위치만 개체 폭/ratio를 조정한다.

**직접 지원 범위:** 첫 문단을 scaffold로 재사용할 수 있는 HWPX. 첫 문단 안 secPr·colPr를 모두 보존해야 한다. 헤더가 표가 아니거나 고정 프레임이 다른 문단에 있거나 과목별 section 구조가 다른 양식은 별도 adapter/빌더 수정이 필요하다. 기본 빌더가 사용자 양식을 자동으로 모두 보존한다고 주장하지 않는다. 수정은 해당 작업의 work 복사본에서 수행하고 제공 패키지 원본은 보존한다.

PDF 원본 프레임을 보존할 때 페이지에 `"background":"page-clean.png"`를 넣는다. **본문·수식을 제거한** 배경만 사용하고 그 위에 본문·수식 개체를 원본 좌표에 배치한다. 종이 크기가 양식과 다르면 원본 좌표를 종이 너비/높이 비율로 일관되게 변환한다. 프레임의 masterPage 참조 및 양식 표가 중복되지 않는지 PDF에서 확인한다.

`review_required:true` 또는 `type:unresolved`인 블록은 빌더가 거부한다. 판독을 확인한 뒤 실제 내용으로 교체한다. 스크립트가 자동으로 이 표시를 삭제하지 않도록 한다.

ZIP 조립은 mimetype을 첫 항목·비압축으로 쓰고, 이미지의 BinData와 content.hpf manifest를 함께 갱신한다. 동일 환경·입력에 대해 조립 ZIP 시간값과 개체 ID는 고정된다. 한글 재저장 파일의 메타데이터와 압축 결과는 한글 버전에 따라 다를 수 있다.

## 1.2 보통 문단과 인라인 수식

`text` 블록은 보통 표 셀 문단이며 그리기 글상자를 만들지 않는다. 문장에 수식이 있으면 다음 `paragraph`를 사용한다. 쉼표·조사·공백은 명시적으로 text에 둔다.

```json
{"type":"paragraph","x":60,"y":235,"width":300,"height":25,"size":11,
 "runs":[{"text":"두 사건 "},{"equation":"A"},{"text":", "},{"equation":"B"},{"text":"에 대하여"}]}
```

위 예시는 측정 전 초안이다. `measure_equations.py draft.json work/measured.json`이 각 equation run에 width/height/baseline/equation_font와 measurement를 채운다. measurement에는 정규화된 script, 실제 size, font가 기록된다. 빌더는 치수 누락뿐 아니라 측정 대상과 현재 수식·글꼴·크기의 불일치도 거부한다. 수식을 바꾼 뒤 이 기록을 손으로 수정하지 말고 다시 측정한다. 원고와 그림 경로는 상대 경로로 유지한다. 한글이 없는 디바이스는 동봉 예제의 측정 치수로 재현할 수 있지만 새 수식의 조판은 실제 한글에서 추가 검증해야 한다.
