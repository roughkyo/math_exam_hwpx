"""파일 해시를 기록하고 math_exam 폴더 하나가 최상위인 ZIP을 만듭니다."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output')
    a = p.parse_args()
    root = Path(__file__).resolve().parent.parent
    out = Path(a.output).resolve()
    if out.exists() or root in out.parents:
        raise ValueError('압축 파일은 패키지 밖의 새 이름으로 지정하세요.')
    paths = sorted(x for x in root.rglob('*') if x.is_file() and not any(part in ('__pycache__', '.venv', 'work') for part in x.relative_to(root).parts) and x.name != 'manifest.json')
    manifest = {x.relative_to(root).as_posix(): hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for path in paths:
            z.write(path, 'math_exam/' + path.relative_to(root).as_posix())
        z.writestr('math_exam/manifest.json', manifest_bytes)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for name, expected in manifest.items():
            assert hashlib.sha256(z.read('math_exam/' + name)).hexdigest() == expected
    print(json.dumps({'archive': str(out), 'files': len(manifest) + 1, 'sha256': hashlib.sha256(out.read_bytes()).hexdigest()}, ensure_ascii=False))
