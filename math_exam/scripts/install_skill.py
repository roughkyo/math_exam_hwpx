"""명시적으로 지정한 프로젝트에 패키지를 복사합니다. 기존 설치는 덮어쓰지 않습니다."""
from pathlib import Path
import argparse
import shutil
import hashlib
import json


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine', required=True, choices=['codex', 'claude', 'antigravity'])
    p.add_argument('--project', required=True)
    p.add_argument('--name', choices=['math_exam', 'math-exam'], default='math-exam', help='엄격한 Agent Skills 이름 규격에는 math-exam을 사용합니다.')
    a = p.parse_args()
    base = '.claude/skills' if a.engine == 'claude' else '.agents/skills'
    target = Path(a.project).resolve() / base / a.name
    if target.exists():
        raise FileExistsError('기존 설치를 보존합니다: ' + str(target))
    source = Path(__file__).resolve().parent.parent
    if target == source or source in target.parents:
        raise ValueError('패키지 자신의 하위 폴더에는 설치하지 않습니다.')
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '.venv', 'work'))
    if a.name == 'math-exam':
        skill = target / 'SKILL.md'
        skill.write_text(skill.read_text(encoding='utf-8').replace('name: math_exam\n', 'name: math-exam\n', 1), encoding='utf-8')
    # 설치 별칭으로 바뀐 SKILL.md도 실제 설치본의 해시 목록에 반영합니다.
    files = sorted(path for path in target.rglob('*') if path.is_file() and path.name != 'manifest.json')
    manifest = {path.relative_to(target).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    (target / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(target)
