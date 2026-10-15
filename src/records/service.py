"""Research-only operations. Personal writes live in a separate interface."""
import json
from contextlib import closing
from pathlib import Path
from .contracts import BASE, FIELDS, Fault, boundary, fields, now, require, text, validate_record
from .storage import Database, expected, get, references, save


class ResearchStore:
    def __init__(self, path: str | Path, timeout: float = 5):
        self.db = Database(path, timeout)

    @boundary
    def create_research(self, record: dict, operation_id: str) -> dict:
        require(isinstance(record, dict) and isinstance(record.get('kind'), str) and record['kind'] in FIELDS)
        require(record['kind'] != 'Assessment', 'Use saveAssessment')
        fields(record, {'id', 'kind'} | FIELDS[record['kind']], {'id', 'kind'} | FIELDS[record['kind']])
        def action(conn):
            if conn.execute('SELECT 1 FROM research_records WHERE id=?', (record['id'],)).fetchone():
                raise Fault('DUPLICATE_ID', 'Record ID already exists', recordId=record['id'])
            timestamp = now()
            full = record | dict(schemaVersion=1, revision=1, createdAt=timestamp, updatedAt=timestamp, archived=False, mergedInto=None)
            validate_record(full)
            references(conn, full)
            return save(conn, full, None, operation_id, 'created', 'Initial collection')
        return self.db.run('research', operation_id, {'action': 'create', 'record': record}, action)

    @boundary
    def read_record(self, id: str, revision: int | None = None) -> dict:
        with closing(self.db.connect()) as conn:
            record = get(conn, id)
            if revision is not None:
                row = conn.execute('SELECT payload FROM record_versions WHERE record_id=? AND revision=?', (id, revision)).fetchone()
                if not row:
                    raise Fault('NOT_FOUND', 'Version not found')
                record = json.loads(row[0])
            from .relations import canonical
            return {'record': record, 'canonicalId': canonical(conn, id)}

    @boundary
    def list_history(self, id: str, cursor: int = 0, limit: int = 20) -> dict:
        require(type(cursor) is int and cursor >= 0 and type(limit) is int and 1 <= limit <= 100)
        with closing(self.db.connect()) as conn:
            get(conn, id)
            rows = conn.execute('SELECT seq,payload FROM research_events WHERE record_id=? AND seq>? ORDER BY seq LIMIT ?', (id, cursor, limit + 1)).fetchall()
            return {'items': [json.loads(row['payload']) | {'seq': row['seq']} for row in rows[:limit]],
                    'nextCursor': rows[limit-1]['seq'] if len(rows) > limit else None}

    @boundary
    def patch_research(self, id: str, expected_revision: int, patch: dict, reason: str, operation_id: str) -> dict:
        require(text(reason))
        def action(conn):
            before = get(conn, id)
            require(before['kind'] != 'Assessment', 'Use saveAssessment')
            fields(patch, FIELDS[before['kind']] | {'archived'})
            expected(before, expected_revision)
            updated = before | patch
            validate_record(updated)
            if before['kind'] == 'Source' and updated['accessStatus'] != 'readable':
                require(updated['lastSuccess'] == before['lastSuccess'], 'Failed access cannot advance success')
            if updated == before:
                return before
            references(conn, updated)
            updated.update(revision=before['revision'] + 1, updatedAt=now())
            return save(conn, updated, before, operation_id, 'updated', reason)
        return self.db.run('research', operation_id, dict(action='patch', id=id, expectedRevision=expected_revision, patch=patch, reason=reason), action)

    @boundary
    def save_assessment(self, idea_id: str, assessment: dict, expected_revision: int | None, operation_id: str) -> dict:
        fields(assessment, FIELDS['Assessment'] - {'ideaId'}, FIELDS['Assessment'] - {'ideaId'})
        def action(conn):
            require(get(conn, idea_id)['kind'] == 'Idea')
            id = 'assessment:' + idea_id
            row = conn.execute('SELECT payload FROM research_records WHERE id=?', (id,)).fetchone()
            before = json.loads(row[0]) if row else None
            if before:
                expected(before, expected_revision)
            elif expected_revision is not None:
                raise Fault('REVISION_CONFLICT', 'Assessment does not yet exist', currentRevision=None)
            timestamp = now()
            updated = dict(id=id, kind='Assessment', ideaId=idea_id, schemaVersion=1, revision=1,
                           createdAt=timestamp, updatedAt=timestamp, archived=False, mergedInto=None) if before is None else dict(before)
            updated.update(assessment)
            validate_record(updated)
            references(conn, updated)
            if updated == before:
                return before
            if before:
                updated.update(revision=before['revision']+1, updatedAt=timestamp)
            return save(conn, updated, before, operation_id, 'assessment_saved', 'External assessment')
        return self.db.run('research', operation_id, dict(action='assessment', ideaId=idea_id, assessment=assessment, expectedRevision=expected_revision), action)

    @boundary
    def list_records(self, kind: str | None = None, query: str = '', filters: dict | None = None, cursor: int = 0, limit: int = 20) -> dict:
        from .queries import list_records
        with closing(self.db.connect()) as conn:
            return list_records(conn, kind, query, filters or {}, cursor, limit)
