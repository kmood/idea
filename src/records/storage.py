"""Short SQLite transactions persist state, immutable history and replay together."""
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from contextlib import closing
from typing import Callable
from .contracts import Fault, encoded, now, require, text

SCHEMA = '''
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO metadata VALUES ('schemaVersion', '2');
CREATE TABLE IF NOT EXISTS research_records(id TEXT PRIMARY KEY, kind TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS record_versions(record_id TEXT NOT NULL REFERENCES research_records(id), revision INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(record_id, revision));
CREATE TABLE IF NOT EXISTS research_events(seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL, record_id TEXT NOT NULL REFERENCES research_records(id), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence_links(record_id TEXT NOT NULL REFERENCES research_records(id), evidence_id TEXT NOT NULL REFERENCES research_records(id), evidence_revision INTEGER NOT NULL, PRIMARY KEY(record_id, evidence_id), FOREIGN KEY(evidence_id,evidence_revision) REFERENCES record_versions(record_id,revision));
CREATE TABLE IF NOT EXISTS personal_states(record_id TEXT PRIMARY KEY REFERENCES research_records(id), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS personal_events(seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL, record_id TEXT NOT NULL REFERENCES research_records(id), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS operations(scope TEXT NOT NULL, key TEXT NOT NULL, request_hash TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(scope, key));
'''


def database_version(conn) -> str:
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata'").fetchone()
    require(exists is not None, 'Missing database metadata')
    row = conn.execute("SELECT value FROM metadata WHERE key='schemaVersion'").fetchone()
    require(row is not None and row[0] in ('1', '2'), 'Unsupported database version')
    return row[0]


class Database:
    def __init__(self, path: str | Path, timeout: float = 5):
        self.path = Path(path)
        self.timeout = timeout
        if self.path.exists():
            # Inspect before schema creation or any write, including future versions.
            with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)) as conn:
                require(database_version(conn) == '2', 'Database requires an explicit upgrade')
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(self.path, timeout=timeout, autocommit=True)) as conn:
                conn.execute('BEGIN IMMEDIATE')
                try:
                    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    if tables:
                        require(database_version(conn) == '2', 'Database requires an explicit upgrade')
                    else:
                        for statement in SCHEMA.split(';'):
                            if statement.strip():
                                conn.execute(statement)
                        conn.execute("INSERT INTO metadata VALUES ('dbInstanceId', ?)", (str(uuid.uuid4()),))
                    conn.execute('COMMIT')
                finally:
                    if conn.in_transaction:
                        conn.execute('ROLLBACK')

    def connect(self) -> sqlite3.Connection:
        # Every new connection rechecks the version before business writes.
        conn = sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True,
                               timeout=self.timeout, autocommit=True)
        try:
            require(database_version(conn) == '2', 'Database requires an explicit upgrade')
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys=ON')
            return conn
        except BaseException:
            conn.close()
            raise

    def run(self, scope: str, operation_id: str, intent: dict, action: Callable, *, guard: Callable | None = None) -> dict:
        require(text(operation_id), 'Operation ID is required')
        digest = hashlib.sha256(encoded(intent).encode()).hexdigest()
        conn = self.connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            if guard is not None:
                guard(conn)
            prior = conn.execute('SELECT * FROM operations WHERE scope=? AND key=?', (scope, operation_id)).fetchone()
            if prior:
                if prior['request_hash'] != digest:
                    raise Fault('IDEMPOTENCY_CONFLICT', 'Operation ID already used for a different request')
                result = json.loads(prior['result'])
            else:
                result = action(conn)
                conn.execute('INSERT INTO operations VALUES (?,?,?,?)', (scope, operation_id, digest, encoded(result)))
            conn.execute('COMMIT')
            return result
        finally:
            if conn.in_transaction:
                conn.execute('ROLLBACK')
            conn.close()


def get(conn: sqlite3.Connection, id: str) -> dict:
    require(text(id))
    row = conn.execute('SELECT payload FROM research_records WHERE id=?', (id,)).fetchone()
    if row is None:
        raise Fault('NOT_FOUND', 'Record not found', recordId=id)
    return json.loads(row[0])


def expected(record: dict, revision: int | None) -> None:
    if type(revision) is not int or revision != record['revision']:
        raise Fault('REVISION_CONFLICT', 'Record changed; read it again', recordId=record['id'], currentRevision=record['revision'])


def save(conn: sqlite3.Connection, record: dict, before: dict | None, operation: str, event_type: str, reason: str, *, authority=None) -> dict:
    if record['kind'] == 'ResearchArtifact' and record['artifactType'] == 'ReadReceipt':
        from .artifacts import _READER_AUTHORITY
        require(authority is _READER_AUTHORITY, 'Only Reader may publish reading receipts')
    if before and before['kind'] == 'ResearchArtifact':
        require(record['artifactType'] == before['artifactType'], 'Artifact type is immutable')
    conn.execute('INSERT INTO research_records VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload',
                 (record['id'], record['kind'], record['revision'], encoded(record)))
    conn.execute('INSERT INTO record_versions VALUES (?,?,?)', (record['id'], record['revision'], encoded(record)))
    conn.execute('DELETE FROM evidence_links WHERE record_id=?', (record['id'],))
    for ref in record.get('evidenceVersions', []):
        conn.execute('INSERT INTO evidence_links VALUES (?,?,?)', (record['id'], ref['recordId'], ref['revision']))
    event = dict(eventId=str(uuid.uuid4()), recordId=record['id'], scope='research', operationId=operation,
                 time=now(), actor='research', eventType=event_type, reason=reason,
                 before=None if before is None else {'recordId': before['id'], 'revision': before['revision']},
                 after={'recordId': record['id'], 'revision': record['revision']}, evidence=record.get('evidenceVersions', []))
    conn.execute('INSERT INTO research_events(event_id,record_id,payload) VALUES (?,?,?)', (event['eventId'], record['id'], encoded(event)))
    return record


def references(conn: sqlite3.Connection, record: dict) -> None:
    if record['kind'] == 'ResearchArtifact':
        from .artifacts import validate_references
        def lookup(id, revision):
            if revision is None:
                return get(conn, id)
            row = conn.execute('SELECT payload FROM record_versions WHERE record_id=? AND revision=?', (id, revision)).fetchone()
            require(row is not None, 'Missing artifact reference')
            return json.loads(row[0])
        validate_references(record, lookup)
    if record['kind'] == 'Evidence':
        require(get(conn, record['sourceId'])['kind'] == 'Source', 'Evidence requires a source')
    if record['kind'] == 'Assessment':
        require(get(conn, record['ideaId'])['kind'] == 'Idea', 'Assessment requires an idea')
    if record['kind'] in ('Idea', 'Trend', 'Assessment'):
        pinned = []
        for id in record['evidenceIds']:
            evidence = get(conn, id)
            require(evidence['kind'] == 'Evidence', 'Invalid evidence reference')
            pinned.append({'recordId': id, 'revision': evidence['revision']})
        record['evidenceVersions'] = pinned
