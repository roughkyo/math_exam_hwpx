# 기본 양식 변경 — 2026-10-11

버전: `1.3-public.2`

사용자가 `form/평가원 수학 양식.hwpx`를 반드시 기본 양식으로 지정하고 공개 배포해도 된다고 명시했습니다. 이에 따라 중립 양식을 사용자 지정 양식으로 교체했습니다. 이는 저장소 소유자의 배포 허용에 근거한 변경이며 제3자 권리에 대한 독립적인 법률 판단은 아닙니다.

## 보존과 개인정보

- 사용자 원본 파일은 수정하지 않았습니다.
- 배포 경로: `math_exam/assets/forms/default_exam.hwpx`
- 배포 복사본의 `Contents/content.hpf`에서 `creator`, `lastsaveby` 값만 비웠습니다.
- 그 외 ZIP 내부 파일은 전부 원본과 바이트 동일합니다. 본문·수식·이미지·미리보기·스타일·마스터 페이지를 보존했습니다.
- 원본 및 배포본 SHA-256은 `math_exam/references/provenance.json`에 기록했습니다.
- 문서 내부를 포함한 개인정보·비밀정보 패턴 재검사에서 발견 0건입니다.

## 기능과 검증

- 기본 글자 스타일을 지정 양식의 `char_seed=23`으로 복원했습니다.
- 중립 양식용 별도 제목 삽입을 제거하고, 원래 양식의 머리말·교시·구분선·쪽번호 구조를 사용합니다.
- 예제 4종의 HWPX/PDF를 재생성했습니다. 실제 한글 출력 성공(2쪽·1쪽·1쪽·1쪽).
- `doctor.py`, `smoke_test.py`, `test_release.py` 모두 통과했습니다. 긴 수식 높이 경고 1건은 이전과 동일하며 원고 내용은 유지했습니다.
- 정적분 예제 첫 쪽에서 지정 양식의 머리말·구분선·문항·그림 배치를 확인했습니다.
- 다른 컴퓨터에서 같은 글꼴·한글 버전 없이 픽셀 동일 출력을 보증한다는 뜻은 아닙니다.

## 변경 파일

- 루트 `README.md`, `math_exam/README.md`, `math_exam/SKILL.md`
- `math_exam/assets/forms/default_exam.hwpx`
- `math_exam/scripts/build_exam.py`
- `math_exam/references/layout.md`, `math_exam/references/provenance.json`
- `math_exam/examples/`의 예제 HWPX/PDF 4쌍
- `math_exam/manifest.json`
- `docs/2026-10-11-publication-audit.md`, 이 변경 기록, `docs/2026-10-11-file-list.txt`

기존 중립 양식 공개본은 Git 이력에 남아 있으며 로컬 작업 전 백업은 공개 저장소 밖의 work 폴더에 보관했습니다.
