# math_exam 공개용 휴대 패키지

버전 `1.3-public.2`. `SKILL.md`가 실행 지침입니다. 일반 본문과 네이티브 한글 수식을 분리하여 수학 문항을 HWPX로 작성합니다.

이 폴더에서 `python -m pip install -r requirements.txt`, `python scripts/doctor.py`를 실행합니다. 예제 조립은 `python scripts/build_exam.py examples/area-three.json <작업폴더>/work/example.hwpx`입니다. 출력은 새 경로를 사용합니다.

Windows 한글은 실제 수식 측정·PDF 출력·편집 시험에 필요합니다. 한글 스킬·MCP·API 키는 필수가 아닙니다. Codex·Claude Code·Antigravity 프로젝트 설치는 `scripts/install_skill.py --help`를 확인하세요. 설치 대상 폴더는 이 패키지 바깥에 둡니다.

기본 양식은 사용자가 공개 배포를 허용한 `평가원 수학 양식.hwpx`입니다. 배포 복사본에서는 작성자·최종 저장자 메타데이터만 비웠습니다. 사용자 양식을 받으면 우선 적용하되 adapter를 검사합니다. 기본 양식 외 원본 시험지 PDF·전체 변환본·개인 작업 기록·양파고 vendor 코드는 포함하지 않습니다. 이 패키지 공개가 제3자 자료나 의존성의 이용 권한을 부여하지는 않습니다.

변환 절차는 `references/conversion.md`, 출제는 `references/authoring.md`, 원고 규격은 `references/layout.md`, 검증은 `references/verification.md`를 읽습니다. 전체 설치·사용 설명은 저장소 루트의 README.md를 참고하세요.
