"""Deterministic previews plus explicit mappings for free-form legacy Markdown."""
import hashlib
import json
import re
from contextlib import closing
from pathlib import Path
from .contracts import Fault, boundary, encoded, fields, now, require, validate_record
from .exchange import digest
from .storage import Database, references, save


def inventory(root: Path) -> dict:
    files = {}
    for directory in ('sources', 'ideas', 'trends', 'research/runs'):
        for path in sorted((root/directory).rglob('*.md')):
            require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), 'Legacy path escapes root')
            relative = path.relative_to(root).as_posix()
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def build_preview(root: Path, mappings: dict) -> dict:
    files = inventory(root)
    require(isinstance(mappings, dict) and mappings.keys() <= files.keys(), 'Mapping path not in legacy inventory')
    records, unresolved = [], []
    for relative, fingerprint in files.items():
        original = (root/relative).read_text(encoding='utf-8')
        if relative not in mappings and (relative in ('ideas/INDEX.md', 'trends/INDEX.md') or relative.startswith('research/runs/')):
            continue  # Supporting documents remain in the hashed inventory.
        matched = re.search(r'```records-json\s*\n(.*?)\n```', original, re.S)
        if relative in mappings:
            entries = mappings[relative]
            require(isinstance(entries, list) and bool(entries), 'Mapping needs records')
        elif matched:
            try:
                entry = json.loads(matched[1])
            except ValueError:
                raise Fault('VALIDATION_ERROR', 'Invalid records-json block') from None
            entries = entry if isinstance(entry, list) else [entry]
        else:
            unresolved.append(dict(path=relative, reason='Explicit field/evidence mapping required'))
            continue
        date_match = re.search(r'首次收录[：:]\s*(\d{4}-\d{2}-\d{2})', original)
        for entry in entries:
            require(isinstance(entry, dict))
            entry = dict(entry)
            first = entry.pop('firstCollectedAt', date_match[1] if date_match else None)
            entry['legacy'] = dict(path=relative, sha256=fingerprint, originalText=original, firstCollectedAt=first)
            records.append(entry)
    order = {'Source': 0, 'Evidence': 1, 'Trend': 2, 'Idea': 3}
    records.sort(key=lambda r: (order.get(r.get('kind'), 9), r.get('id', '')))
    value = dict(schemaVersion=1, files=files, mappings=mappings, records=records, unresolved=unresolved)
    value['previewId'] = digest(value)
    return value


@boundary
def preview_legacy(root: str | Path, mappings: dict | None = None) -> dict:
    return build_preview(Path(root), mappings or {})


@boundary
def apply_preview(root: str | Path, preview: dict, database: str | Path, operation_id: str) -> dict:
    fields(preview, {'schemaVersion', 'files', 'mappings', 'records', 'unresolved', 'previewId'},
           {'schemaVersion', 'files', 'mappings', 'records', 'unresolved', 'previewId'})
    root = Path(root)
    fresh = build_preview(root, preview['mappings'])
    if fresh != preview:
        raise Fault('REVISION_CONFLICT', 'Legacy content changed; regenerate preview')
    require(not preview['unresolved'], 'Resolve all legacy mappings before applying')
    db = Database(database)
    def action(conn):
        results = []
        for entry in preview['records']:
            require(not conn.execute('SELECT 1 FROM research_records WHERE id=?', (entry.get('id'),)).fetchone(), 'Legacy ID already exists')
            timestamp = now()
            record = entry | dict(schemaVersion=1, revision=1, createdAt=timestamp, updatedAt=timestamp, archived=False, mergedInto=None)
            validate_record(record)
            references(conn, record)
            op = 'legacy:' + preview['previewId'] + ':' + record['id']
            result = save(conn, record, None, op, 'created', 'Reviewed legacy mapping; original retained')
            request = dict(action='create', record=entry)
            conn.execute('INSERT INTO operations VALUES (?,?,?,?)', ('research', op, digest(request), encoded(result)))
            results.append(record['id'])
        if inventory(root) != preview['files']:
            raise Fault('REVISION_CONFLICT', 'Legacy content changed during migration')
        return dict(previewId=preview['previewId'], recordIds=results)
    return db.run('migration', operation_id, dict(action='legacy', previewId=preview['previewId']), action)
