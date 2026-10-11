# math_exam_hwpx

수능형 수학 문항을 **본문은 일반 텍스트, 수식은 한글 수식 개체**로 작성하는 AI 에이전트용 스킬 패키지입니다. PDF·이미지의 문항 변환, 문제집 통합과 교정, 주제·예시 문항을 바탕으로 한 응용·변형 출제를 지원합니다. 응용·변형 출제의 기본 결과물은 HWPX입니다.

AI가 원문을 판독하고 수식을 대조하는 작업 절차와 Python 도구를 함께 제공합니다. 임의의 PDF를 한 번 실행하여 완전 자동 변환하는 프로그램은 아닙니다.

## 기능과 범위

- 본문·쉼표·조사·한글 조건은 보통 텍스트, 수학식은 네이티브 수식으로 분리합니다.
- 사용자 양식을 우선 사용하고, 없으면 사용자가 공개 배포를 허용한 평가원 수학 양식을 사용합니다.
- 원문 변환에서는 그림을 이미지 개체로 보존합니다. 그림 속 모든 글자·곡선이 개별 편집 개체로 바뀌지는 않습니다.
- 새 문제의 그래프를 조건에 맞게 생성하고, 원고와 결과물의 수식·본문·배점을 대조합니다.
- 한글에서 수식 치수 측정, PDF 출력, 본문 직접 편집 시험을 수행할 수 있습니다.
- 실제 출력 검토가 끝나지 않은 결과를 검증 완료로 표시하지 않습니다.

**공개본 `1.4-public.1`:** 저장소 소유자가 지정하고 배포를 허용한 `평가원 수학 양식.hwpx`를 기본으로 제공합니다. 배포 복사본은 작성자·최종 저장자 메타데이터만 비웠으며, 그 외 문서 구성은 원본과 동일합니다. 기본 양식 외 원본 시험지 PDF, 전체 변환본, 개인정보가 포함될 수 있는 작업 기록, 재배포 허가를 확인하지 못한 양파고 vendor 스크립트는 포함하지 않습니다. 별도 한글 스킬이나 특정 MCP 설치가 필요하지 않습니다.

## 실행 환경

Python 3.13을 기준으로 검사합니다. HWPX 조립·구조 검사와 PDF 추출은 Python으로 실행합니다. **수식 자동 측정과 실제 한글 출력·편집 시험에는 Windows와 설치된 한글이 필요합니다.** 한글 프로그램, 글꼴, 보안 모듈, Python 의존 라이브러리는 배포물에 포함하지 않습니다.

```bash
git clone https://github.com/roughkyo/math_exam_hwpx.git
cd math_exam_hwpx
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r math_exam/requirements.txt
.\.venv\Scripts\python.exe math_exam/scripts/doctor.py
```

macOS/Linux:

```bash
.venv/bin/python -m pip install -r math_exam/requirements.txt
.venv/bin/python math_exam/scripts/doctor.py
```

이하 `python`은 위 가상환경의 Python을 뜻합니다. `requirements-lock.txt`는 검증 환경의 버전 목록이며 모든 OS에서 같은 출력이 나온다는 보증은 아닙니다.

## 에이전트에서 사용

가장 간단하게는 에이전트에게 다음과 같이 요청합니다.

> `math_exam/SKILL.md`를 읽고 첨부한 수학 PDF를 HWPX로 변환해 줘. 본문은 일반 글자로, 수식만 수식 편집기로 수정 가능하게 만들고 원본과 출력본을 검증해 줘.

> 정적분으로 두 곡선 사이 넓이를 구하는 새로운 문제 3개를 만들어 줘. 새 그림, 정답과 해설을 포함해 HWPX로 작성해 줘.

프로젝트별 설치도 가능합니다. 기존 설치를 덮어쓰지 않으며 전역 설정은 수정하지 않습니다.

```bash
python math_exam/scripts/install_skill.py --engine codex --project <사용할-프로젝트>
python math_exam/scripts/install_skill.py --engine claude --project <사용할-프로젝트>
python math_exam/scripts/install_skill.py --engine antigravity --project <사용할-프로젝트>
```

Codex·Antigravity 대상은 `.agents/skills/math-exam/`, Claude Code 대상은 `.claude/skills/math-exam/`에 복사합니다. 호환 이름은 `math-exam`, 원본 폴더 이름은 `math_exam`입니다. 앱 버전에 따라 스킬 탐색 설정을 확인하세요. 세 앱에서 각각 실행을 검증했다는 의미는 아닙니다.

## 예제와 검증

```bash
python math_exam/scripts/check_examples.py
python math_exam/scripts/build_exam.py math_exam/examples/area-three.json work/example.hwpx
python math_exam/scripts/validate_exam.py work/example.hwpx work/example-check --plan math_exam/examples/area-three.json
python math_exam/scripts/render_hancom.py work/example.hwpx work/example.pdf
python math_exam/scripts/test_layout_guards.py
python math_exam/scripts/test_native_paragraphs.py --work work/native-check
python math_exam/scripts/test_release.py work/release-check
```

출력 경로는 기존 파일·검증 폴더와 겹치지 않게 지정합니다. 인라인 수식을 수정하면 이전 치수를 재사용하지 말고 `measure_equations.py`로 재측정합니다. 그림과 표기·정답은 별도로 대조합니다. 고정 지면의 본문은 행 단위 표 안에 있으므로 긴 문장 편집 후에는 폭과 줄바꿈 조정이 필요할 수 있습니다.

## 폴더 구성

```text
math_exam/
  SKILL.md                  에이전트 실행 지침
  agents/                   표시 정보
  assets/forms/             사용자 지정 평가원 수학 양식
  examples/                 새 문항 원고·그림·검증 예제
  scripts/                  조립·추출·측정·검사·설치 도구
  references/               변환·출제·조판·검증 규격
  requirements*.txt         Python 의존성
  manifest.json             배포 파일 해시
```

문항 자료는 `input/`, 사용자 양식은 `form/`, 중간 결과는 `work/`, 최종 산출물은 `output/`에 두면 Git에서 제외됩니다. `.gitignore`는 이미 추적된 파일이나 문서 내부 메타데이터까지 지워 주지는 않습니다.

## 개인정보·권리·재현 범위

공개 전 파일 내용과 HWPX ZIP 내부의 작성자·저장자·미리보기, PDF 메타데이터를 검사합니다. 공개 커밋은 GitHub의 noreply 주소를 사용합니다. 바닥글·벡터 수정은 [1.4 검증 기록](docs/2026-10-11-footer-vector-fix.md)을 참고하세요. 기본 양식과 검증 결과는 [기본 양식 변경 기록](docs/2026-10-11-template-update.md), 최초 공개 범위는 [공개 점검 기록](docs/2026-10-11-publication-audit.md)을 참고하세요.

제3자 문제·양식·폰트의 이용 및 공개 권한은 별도로 확인해야 합니다. 예제는 공식 시험기관의 자료가 아닙니다. 저장소 공개만으로 모든 구성 요소에 대한 포괄적 오픈소스 라이선스를 부여하지 않으며, 이 저장소에는 임의의 MIT 등 라이선스를 추가하지 않았습니다. Python 의존성은 각각의 라이선스를 따릅니다. 특히 PyMuPDF의 이용·배포 조건은 [프로젝트 라이선스 안내](https://pymupdf.readthedocs.io/en/latest/about.html#license)를 확인하세요.

같은 원고·양식·그림으로 HWPX 조립의 재현성을 검사할 수 있지만, AI 출제 내용과 서로 다른 한글·글꼴 환경의 출력이 항상 같다는 보증은 없습니다.

바닥글 배경 중복과 벡터 화살촉 잘림 방지 검사를 추가했습니다. Windows 한글에서 `python math_exam/scripts/test_footer_visibility.py --work work/visibility-check --render`로 실제 출력 회귀 검사를 실행할 수 있습니다.
