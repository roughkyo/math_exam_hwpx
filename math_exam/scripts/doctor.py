"""패키지 이동 후 의존성·양식 해시·한글 사용 가능 여부를 읽기 전용 점검합니다."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform
import sys

ROOT = Path(__file__).resolve().parent.parent
result = {'python': sys.version, 'platform': platform.platform(), 'dependencies': {}, 'template_ok': False, 'hancom_registered': False}
for name in ['lxml', 'PyMuPDF', 'numpy', 'matplotlib', 'Pillow']:
    try:
        result['dependencies'][name] = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        result['dependencies'][name] = None
prov = json.loads((ROOT / 'references/provenance.json').read_text(encoding='utf-8'))
result['template_ok'] = hashlib.sha256((ROOT / 'assets/forms/default_exam.hwpx').read_bytes()).hexdigest() == prov['template']['sha256']
if sys.platform == 'win32':
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'HWPFrame.HwpObject'):
            result['hancom_registered'] = True
    except (ImportError, OSError):
        pass
print(json.dumps(result, ensure_ascii=False, indent=2))
if not result['template_ok'] or any(v is None for v in result['dependencies'].values()):
    raise SystemExit(1)
