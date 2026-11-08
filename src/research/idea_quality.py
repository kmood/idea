"""Executable quality gate for ideas counted toward the cumulative target."""
import re
from pathlib import Path


ROW = re.compile(r'^\| \[([A-Z][A-Z0-9-]+)\]\(([^)]+\.md)\) \|', re.MULTILINE)
PROGRESS = re.compile(r'严格校验有效点子\s*(\d+)\s*/\s*(\d+)')
EVIDENCE = re.compile(r'(?<![A-Za-z0-9])E[1-3](?![A-Za-z0-9])')
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


def _index_rows(text):
    records = []
    for line in text.splitlines():
        if not line.startswith('| ['):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) < 2:
            continue
        match = re.match(r'^\[([^\]]+)\]\(([^)]+\.md)\)$', cells[0])
        if not match:
            continue
        values = cells[1:] + [''] * 6
        records.append(dict(id=match.group(1), relative=match.group(2), title=values[0],
                            market=values[1], evidence=values[2], fit=values[3],
                            status=values[4], updated=values[5]))
    return records


def _has_any(text, markers):
    return any(marker in text for marker in markers)


# 否定或待定语境：命中这些词的句子只是在陈述“缺少/待核验/不写入公开包”，
# 不能当作该字段已经具备的正面证据。
NEGATION_MARKERS = (
    '缺少', '缺失', '缺', '未', '无', '没有', '尚未', '未知', '不明确',
    '待补', '待核验', '需补', '不写入', '不进入', '留在私人', '核验',
)

# 文档显式研究状态到审计档位的保守映射。
DECLARED_STATUS = (
    ('暂不适合', '暂不适合'),
    ('搁置', '仅观察'),
    ('需补证', '需补证'),
    ('待验证', '需补证'),
)
READINESS_RANK = {'可行动': 0, '需补证': 1, '仅观察': 2, '暂不适合': 3}


def _has_positive_mention(document, markers):
    """关键词只有出现在非否定句中才算字段已具备。"""
    for sentence in re.split(r'[。；;\n]', document):
        if not any(marker in sentence for marker in markers):
            continue
        if not any(negation in sentence for negation in NEGATION_MARKERS):
            return True
    return False


def _declared_status(document):
    """读取文档头部人工守门声明的研究状态，作为不可突破的保守上限。"""
    match = re.search(r'^- (?:研究状态|当前状态)：([^\n]+)', document, re.MULTILINE)
    if not match:
        return None
    declaration = match.group(1)
    for keyword, status in DECLARED_STATUS:
        if keyword in declaration:
            return status
    return None


def _audit_entry(record, document):
    evidence = record['evidence'] + '\n' + _evidence_section(document)
    missing = []
    if not _has_positive_mention(document, ('获客路径', '获客渠道', '如何获客', '可触达', '首个动作', '项目平台', '专业社区', '合作伙伴', '转介绍', '客户渠道', '触达客户')):
        missing.append('acquisitionPath')
    if not _has_positive_mention(document, ('最小交付', '交付边界', '固定小包', '固定范围', '交付包', '服务包')):
        missing.append('minimumDelivery')
    if not _has_positive_mention(document, ('探索周期', '建议周期', '阶段目标', '主动工时', '继续条件', '延长条件', '暂停条件')):
        missing.append('explorationCycle')
    if not _has_positive_mention(document, ('付款', '成交', '上线', '交付结果', '复购')):
        missing.append('commercialOutcome')
    if not _has_any(document, ('当前', '近期', '本月', '本周', '开放')) and _has_any(document, ('历史', '已关闭', '期限已过')):
        recency = '历史或已关闭'
    elif _has_any(document, ('当前', '近期', '本月', '本周', '开放')):
        recency = '当前信号'
    else:
        recency = '未知'
    declared = _declared_status(document)
    if '暂不适合' in record['fit'] or '暂不适合' in document:
        readiness = '暂不适合'
    elif recency == '历史或已关闭' and '当前' not in evidence:
        readiness = '仅观察'
    elif missing:
        readiness = '需补证'
    else:
        readiness = '可行动'
    # 人工守门声明只能压低档位，不能被关键词推断调高。
    if declared and READINESS_RANK[readiness] < READINESS_RANK[declared]:
        readiness = declared
    signals = [signal for signal in ('需求', '意向', '报价', '选人', '交付', '上线', '付款', '复购')
               if signal in evidence]
    level = EVIDENCE.search(record['evidence'])
    return dict(id=record['id'], readinessStatus=readiness,
                indexEvidenceLevel=level.group(0) if level else None,
                recencyStatus=recency, evidenceSignals=signals, missing=missing)


def audit_idea_record(record, document):
    """Return read-only quality metadata for a parsed idea document."""
    return _audit_entry({
        'id': record.get('id', ''),
        'evidence': record.get('evidence', ''),
        'fit': record.get('fit', ''),
    }, document)


def validate_idea_library(root):
    root = Path(root)
    index = root / 'ideas' / 'INDEX.md'
    text = index.read_text(encoding='utf-8')
    violations = []
    records = _index_rows(text)
    rows = [(record['id'], record['relative']) for record in records]
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
    audit = []
    for record in records:
        record_id, relative = record['id'], record['relative']
        path = (index.parent / relative).resolve()
        if index.parent.resolve() not in path.parents or not path.is_file():
            violations.append(f'{record_id}: missing or unsafe document')
            continue
        document = path.read_text(encoding='utf-8')
        audit.append(_audit_entry(record, document))
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
        'audit': audit,
        'qualitySummary': {status: sum(item['readinessStatus'] == status for item in audit)
                           for status in ('可行动', '需补证', '仅观察', '暂不适合')},
    }
