"""Translate the current Markdown indexes into a stable display contract."""
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


INDEXES={'source':Path('sources/INDEX.md'),'trend':Path('trends/INDEX.md'),'idea':Path('ideas/INDEX.md')}
LINK=re.compile(r'^\[([^\]]+)\]\(([^)]+)\)$')
ID=re.compile(r'^[A-Z][A-Z0-9-]{1,79}$')
EVIDENCE=re.compile(r'\b(E[0-3])\b')


def tables(text):
    rows=[]
    for line in text.splitlines():
        if line.startswith('|') and line.endswith('|'):
            cells=[cell.strip() for cell in line[1:-1].split('|')]
            if not all(set(cell)<=set('-: ') for cell in cells):rows.append(cells)
    return rows


def link(value):
    match=LINK.match(value)
    return (match.group(1),match.group(2)) if match else (value,None)


def public_url(value):
    if not value:return None
    parsed=urlsplit(value)
    return value if parsed.scheme in ('http','https') and parsed.netloc else None


def access_status(value):
    """Reduce source prose to a conservative, exact display filter."""
    if not value:
        return '未知'
    if '受限' in value:
        return '受限'
    if '可读' in value:
        return '可读'
    return '未知'


def evidence_level(value):
    match=EVIDENCE.search(value or '')
    return match.group(1) if match else None


def ordered_options(values, preferred):
    present=set(values)
    return [value for value in preferred if value in present] + sorted(present-set(preferred))


def document_path(index_path,target):
    if not target:return index_path.as_posix()
    candidate=PurePosixPath(index_path.parent.as_posix())/target
    if candidate.is_absolute() or '..' in candidate.parts or candidate.suffix.lower()!='.md':raise ValueError('Unsafe document path')
    return candidate.as_posix()


def load_rows(root,kind,index_path):
    path=root/index_path
    if not path.is_file():return []
    rows=tables(path.read_text(encoding='utf-8'))
    if len(rows)<2:return []
    records=[]
    for cells in rows[1:]:
        if kind=='idea' and len(cells)>=7:
            record_id,target=link(cells[0]);title,_=link(cells[1])
            record=dict(id=record_id,kind=kind,title=title,summary=cells[4],marketOrSource=cells[2],
                        evidence=cells[3],evidenceNote=('存在采购/报价/付款信号，具体类型见详情。' if cells[3].startswith('E3') else None),
                        fit=cells[4],evidenceLevel=evidence_level(cells[3]),
                        status=cells[5],researchStatus=cells[5],updatedAt=cells[6],url=None,
                        documentPath=document_path(index_path,target))
        elif kind=='trend' and len(cells)>=5:
            record_id,target=link(cells[0]);title,_=link(cells[1])
            record=dict(id=record_id,kind=kind,title=title,summary=cells[3],marketOrSource=cells[2],
                        evidence=cells[3].split('，',1)[0] or None,evidenceLevel=evidence_level(cells[3]),status=cells[3],researchStatus=cells[3],updatedAt=cells[4],url=None,
                        documentPath=document_path(index_path,target))
        elif kind=='source' and len(cells)>=6:
            record_id=cells[0];title,url=link(cells[1])
            record=dict(id=record_id,kind=kind,title=title,summary=cells[2],marketOrSource=cells[3],
                        evidence=None,status=cells[4],accessStatus=access_status(cells[4]),updatedAt=None,url=public_url(url),
                        documentPath=index_path.as_posix(),priority=cells[5])
        else:continue
        if not ID.fullmatch(record['id']):raise ValueError('Unsafe record id')
        records.append(record)
    return records


def load_catalog(root):
    root=Path(root).resolve();records=[]
    for kind,index_path in INDEXES.items():records.extend(load_rows(root,kind,index_path))
    state=root/'research/STATE.md';phase=None
    if state.is_file():
        match=re.search(r'^- 阶段：([^；。\n]+)',state.read_text(encoding='utf-8'),re.MULTILINE)
        if match:phase=match.group(1).strip()
    counts={kind:sum(item['kind']==kind for item in records) for kind in INDEXES}
    status_counts={
        'source':dict(Counter(item.get('accessStatus','未知') for item in records if item['kind']=='source')),
        'trend':dict(Counter(item['status'] for item in records if item['kind']=='trend')),
        'idea':dict(Counter(item['researchStatus'] for item in records if item['kind']=='idea')),
    }
    idea_statuses=[item['researchStatus'] for item in records if item['kind']=='idea']
    idea_fits=[item['fit'] for item in records if item['kind']=='idea' and item.get('fit')]
    source_access=[item.get('accessStatus','未知') for item in records if item['kind']=='source']
    hostnames={urlsplit(item['url']).hostname.lower() for item in records if item['kind']=='source' and item.get('url') and urlsplit(item['url']).hostname}
    meta={
        'phase':phase,
        'counts':counts,
        'statusCounts':status_counts,
        'selectedCount':status_counts['idea'].get('精选',0),
        'filters':{
            'ideaResearchStatus':ordered_options(idea_statuses,('待验证','候选','搁置','精选')),
            'ideaFit':ordered_options(idea_fits,('较适合','有条件适合','暂不适合')),
            'sourceAccessStatus':ordered_options(source_access,('可读','受限','未知')),
        },
        'sourceMetrics':{'entryCount':counts['source'],'hostnameCount':len(hostnames)},
    }
    return {'meta':meta,'records':records}


def validate_catalog(root):
    """Check stable, public Markdown references without inspecting private records."""
    root=Path(root).resolve();errors=[];warnings=[]
    try:
        catalog=load_catalog(root)
        records=catalog['records']
    except (OSError,UnicodeError,ValueError) as exc:
        return {'ok':False,'errors':['目录无法读取：'+type(exc).__name__],'warnings':[]}
    for kind in INDEXES:
        ids=[record['id'] for record in records if record['kind']==kind]
        duplicates=sorted({record_id for record_id in ids if ids.count(record_id)>1})
        if duplicates:errors.append(f'{kind} ID 重复：'+', '.join(duplicates))
    for record in records:
        if record['kind'] in ('idea','trend'):
            path=root/record['documentPath']
            if not path.is_file():errors.append(f"{record['id']} 正文不存在")
        if record['kind']=='idea' and record['researchStatus'] not in {'待验证','候选','精选','搁置'}:
            errors.append(f"{record['id']} 研究状态非法")
        if record['kind']=='source' and record.get('accessStatus')=='未知':
            warnings.append(f"{record['id']} 访问状态未知")
    counts=catalog['meta']['counts']
    if counts['idea']==0:warnings.append('当前没有点子记录')
    return {'ok':not errors,'errors':errors,'warnings':warnings}


def find_record(root,kind,record_id):
    if kind not in INDEXES or not ID.fullmatch(record_id):return None
    return next((item for item in load_catalog(root)['records'] if item['kind']==kind and item['id']==record_id),None)
