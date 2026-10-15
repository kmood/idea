"""Local user choices and private history; never exported as research."""
import json
import uuid
from contextlib import closing
from pathlib import Path
from .contracts import PRIVATE, Fault, boundary, encoded, fields, now, require
from .storage import Database, get


def read(conn, id: str) -> dict:
    get(conn, id)
    row = conn.execute('SELECT payload FROM personal_states WHERE record_id=?', (id,)).fetchone()
    return json.loads(row[0]) if row else dict(schemaVersion=1, id=id, recordId=id, revision=None,
                                             createdAt=None, updatedAt=None, favorite=False, ignored=False,
                                             validationStage='未开始', notes='')


class PersonalStore:
    def __init__(self, path: str | Path, timeout: float = 5):
        self.db = Database(path, timeout)

    @boundary
    def read_record(self, id: str) -> dict:
        with closing(self.db.connect()) as conn:
            return read(conn, id)

    @boundary
    def set_personal_state(self, id: str, expected_revision: int | None, patch: dict, operation_id: str) -> dict:
        fields(patch, PRIVATE)
        for key in ('favorite', 'ignored'):
            if key in patch:
                require(type(patch[key]) is bool)
        if 'notes' in patch:
            require(isinstance(patch['notes'], str))
        if 'validationStage' in patch:
            require(patch['validationStage'] in ('未开始', '准备验证', '验证中', '结束'))
        def action(conn):
            before = read(conn, id)
            if (expected_revision is not None and type(expected_revision) is not int) or before['revision'] != expected_revision:
                raise Fault('REVISION_CONFLICT', 'Personal state changed', recordId=id, currentRevision=before['revision'])
            after = before | patch
            if before['revision'] is not None and after == before:
                return before
            timestamp = now()
            after.update(revision=(before['revision'] or 0) + 1, createdAt=before['createdAt'] or timestamp, updatedAt=timestamp)
            conn.execute('INSERT INTO personal_states VALUES (?,?) ON CONFLICT(record_id) DO UPDATE SET payload=excluded.payload', (id, encoded(after)))
            event = dict(eventId=str(uuid.uuid4()), recordId=id, scope='personal', operationId=operation_id,
                         time=timestamp, actor='user', eventType='personal_updated', before=before, after=after,
                         reason='User choice', evidence=[])
            conn.execute('INSERT INTO personal_events(event_id,record_id,payload) VALUES (?,?,?)', (event['eventId'], id, encoded(event)))
            return after
        return self.db.run('personal', operation_id, dict(action='personal', id=id, expectedRevision=expected_revision, patch=patch), action)

    @boundary
    def list_history(self, id: str, cursor: int = 0, limit: int = 20) -> dict:
        require(type(cursor) is int and cursor >= 0 and type(limit) is int and 1 <= limit <= 100)
        with closing(self.db.connect()) as conn:
            get(conn, id)
            rows = conn.execute('SELECT seq,payload FROM personal_events WHERE record_id=? AND seq>? ORDER BY seq LIMIT ?', (id, cursor, limit+1)).fetchall()
            return dict(items=[json.loads(row['payload']) | {'seq': row['seq']} for row in rows[:limit]],
                        nextCursor=rows[limit-1]['seq'] if len(rows) > limit else None)

    @boundary
    def related_states(self, id: str) -> dict:
        from .relations import canonical
        with closing(self.db.connect()) as conn:
            target = canonical(conn, id)
            rows = conn.execute('SELECT id FROM research_records').fetchall()
            states = {row['id']: read(conn, row['id']) for row in rows if canonical(conn, row['id']) == target}
            choices = {encoded({key: state[key] for key in PRIVATE}) for state in states.values()}
            return dict(canonicalId=target, states=states, conflict=len(choices)>1)


def validate_private_history(conn) -> None:
    """Recovery checks the private version chain as well as SQLite page integrity."""
    from .contracts import stamp, text
    state_fields = {'schemaVersion', 'id', 'recordId', 'revision', 'createdAt', 'updatedAt'} | PRIVATE
    latest, versions = {}, {}
    for row in conn.execute('SELECT payload FROM personal_events ORDER BY seq'):
        event = json.loads(row[0])
        require(isinstance(event, dict) and event.get('scope') == 'personal' and event.get('actor') == 'user')
        id = event.get('recordId')
        require(text(id) and stamp(event.get('time')) and text(event.get('operationId')))
        after, before = event.get('after'), event.get('before')
        fields(after, state_fields, state_fields)
        require(after['schemaVersion'] == 1 and after['id'] == id and after['recordId'] == id)
        require(type(after['revision']) is int and after['revision'] == (latest[id]['revision']+1 if id in latest else 1))
        require(stamp(after['createdAt']) and stamp(after['updatedAt']))
        require(type(after['favorite']) is bool and type(after['ignored']) is bool and isinstance(after['notes'], str))
        require(after['validationStage'] in ('未开始', '准备验证', '验证中', '结束'))
        if id in latest:
            require(before == latest[id] and after['createdAt'] == before['createdAt'], 'Broken private history')
        else:
            require(before == dict(schemaVersion=1, id=id, recordId=id, revision=None, createdAt=None,
                                   updatedAt=None, favorite=False, ignored=False, validationStage='未开始', notes=''))
        replay = conn.execute("SELECT result FROM operations WHERE scope='personal' AND key=?", (event['operationId'],)).fetchone()
        require(replay is not None and json.loads(replay[0]) == after, 'Missing private replay information')
        latest[id] = after
        versions[(id, after['revision'])] = after
    current = {row['record_id']: json.loads(row['payload']) for row in conn.execute('SELECT * FROM personal_states')}
    require(current == latest, 'Private state differs from its history')
    for row in conn.execute("SELECT result FROM operations WHERE scope='personal'"):
        result = json.loads(row[0])
        fields(result, state_fields, state_fields)
        require(text(result['id']) and type(result['revision']) is int)
        require(versions.get((result['id'], result['revision'])) == result, 'Private replay differs from history')
