"""Bounded SQL browsing; NULL cost stays distinct from a zero estimate."""
import json
from .contracts import FIELDS, fields, require, text


def list_records(conn, kind, query, filters, cursor, limit) -> dict:
    require(kind is None or (isinstance(kind, str) and kind in FIELDS))
    require(isinstance(query, str) and type(cursor) is int and cursor >= 0 and type(limit) is int and 1 <= limit <= 100)
    fields(filters, {'industry', 'market', 'sideHustleType', 'evidence', 'fit', 'costUnknown', 'maxCost', 'currency', 'archived', 'includeMerged', 'researchStatus'})
    where, args = [], []
    if kind:
        where.append('r.kind=?'); args.append(kind)
    # Unicode casefold, including user text; SQL paths below are constants.
    conn.create_function('casefold', 1, lambda value: str(value).casefold(), deterministic=True)
    if query:
        where.append("instr(casefold(COALESCE(json_extract(r.payload,'$.title'),json_extract(r.payload,'$.name'),json_extract(r.payload,'$.claim'),'')),?) > 0")
        args.append(query.casefold())
    if not filters.get('includeMerged', False):
        where.append("json_extract(r.payload,'$.mergedInto') IS NULL")
    for key in ('archived', 'includeMerged', 'costUnknown'):
        if key in filters:
            require(type(filters[key]) is bool)
    for key, path in [('industry', 'industry'), ('market', 'markets'), ('sideHustleType', 'sideHustleTypes')]:
        if key in filters:
            require(text(filters[key]))
            where.append(f"EXISTS (SELECT 1 FROM json_each(r.payload,'$.{path}') WHERE value=?)")
            args.append(filters[key])
    for key in ('archived', 'researchStatus'):
        if key in filters:
            where.append(f"json_extract(r.payload,'$.{key}')=?"); args.append(filters[key])
    if 'evidence' in filters:
        require(filters['evidence'] in ('E0', 'E1', 'E2', 'E3'))
        where.append("EXISTS (SELECT 1 FROM evidence_links l JOIN record_versions e ON e.record_id=l.evidence_id AND e.revision=l.evidence_revision WHERE l.record_id=r.id AND json_extract(e.payload,'$.level')=?)")
        args.append(filters['evidence'])
    if 'fit' in filters:
        require(filters['fit'] in ('较适合', '有条件适合', '暂不适合', '未知'))
        where.append("COALESCE(json_extract(a.payload,'$.fit'),'未知')=?"); args.append(filters['fit'])
    if 'costUnknown' in filters:
        where.append("json_extract(a.payload,'$.cost') IS " + ('NULL' if filters['costUnknown'] else 'NOT NULL'))
    if 'maxCost' in filters:
        require(type(filters['maxCost']) in (int, float) and filters['maxCost'] >= 0 and text(filters.get('currency')))
        where.append("json_extract(a.payload,'$.cost.currency')=? AND json_extract(a.payload,'$.cost.max')<=?")
        args.extend([filters['currency'], filters['maxCost']])
    sql = "SELECT r.payload FROM research_records r LEFT JOIN research_records a ON a.id='assessment:'||r.id AND a.kind='Assessment'"
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += " ORDER BY json_extract(r.payload,'$.updatedAt') DESC,r.id ASC LIMIT ? OFFSET ?"
    rows = conn.execute(sql, [*args, limit+1, cursor]).fetchall()
    return dict(items=[json.loads(row[0]) for row in rows[:limit]], nextCursor=cursor+limit if len(rows)>limit else None)
