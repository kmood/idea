"""Executable quality gate for ideas counted toward the cumulative target."""
import re
from pathlib import Path


ROW = re.compile(r'^\| \[([A-Z][A-Z0-9-]+)\]\(([^)]+\.md)\) \|', re.MULTILINE)
PROGRESS = re.compile(r'严格校验有效点子\s*(\d+)\s*/\s*(\d+)')
EVIDENCE = re.compile(r'\bE[1-3]\b')
SOURCE_LINK = re.compile(r'\[[^\]]+\]\(https?://[^)]+\)')
REQUIRED = (
    ('服务对象与问题', 'missing audience/problem'),
    ('可能赚钱方式', 'missing earning hypothesis'),
    ('个人匹配', 'missing personal fit'),
    ('未知', 'missing unknowns'),
    ('| 时间 | 事件与变化 | 原因/证据 | 执行者 |', 'missing history'),
)


def _evidence_section(document):
    match = re.search(r'^## 证据[^\n]*\n([\s\S]*?)(?=^## |\Z)', document, re.MULTILINE)
    return match.group(1) if match else ''


def validate_idea_library(root):
    root = Path(root)
    index = root / 'ideas' / 'INDEX.md'
    text = index.read_text(encoding='utf-8')
    violations = []
    rows = ROW.findall(text)
    ids = [record_id for record_id, _ in rows]
    if len(ids) != len(set(ids)):
        violations.append('duplicate idea id in index')
    progress = PROGRESS.search(text)
    if not progress:
        violations.append('missing cumulative progress')
        current, target = None, None
    else:
        current, target = map(int, progress.groups())
        if current != len(rows):
            violations.append('progress count differs from indexed ideas')
        if target < 200:
            violations.append('cumulative target is below 200')
    for record_id, relative in rows:
        path = (index.parent / relative).resolve()
        if index.parent.resolve() not in path.parents or not path.is_file():
            violations.append(f'{record_id}: missing or unsafe document')
            continue
        document = path.read_text(encoding='utf-8')
        if not document.startswith(f'# {record_id} '):
            violations.append(f'{record_id}: heading does not preserve id')
        for marker, message in REQUIRED:
            if marker not in document:
                violations.append(f'{record_id}: {message}')
        if not EVIDENCE.search(document):
            violations.append(f'{record_id}: missing E1-E3 evidence level')
        if not SOURCE_LINK.search(document):
            violations.append(f'{record_id}: missing concrete source link')
        evidence = _evidence_section(document)
        if not evidence or not SOURCE_LINK.search(evidence):
            violations.append(f'{record_id}: source link is not attached to evidence section')
        if '下一步' not in document:
            violations.append(f'{record_id}: missing next validation action')
        if not re.search(r'^\| 20\d{2}-\d{2}-\d{2}', document, re.MULTILINE):
            violations.append(f'{record_id}: missing dated history event')
        if not ('反证' in document or '替代' in document):
            violations.append(f'{record_id}: missing counterevidence or alternative')
    invalid_ids = {v.split(':', 1)[0] for v in violations if ':' in v}
    return {
        'validCount': len(rows) - len(invalid_ids),
        'indexedCount': len(rows),
        'target': target,
        'violations': violations,
    }
