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
INSERT OR IGNORE INTO metadata VALUES ('schemaVersion', '1');
CREATE TABLE IF NOT EXISTS research_records(id TEXT PRIMARY KEY, kind TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS record_versions(record_id TEXT NOT NULL REFERENCES research_records(id), revision INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(record_id, revision));
CREATE TABLE IF NOT EXISTS research_events(seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL, record_id TEXT NOT NULL REFERENCES research_records(id), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS operations(scope TEXT NOT NULL, key TEXT NOT NULL, request_hash TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(scope, key));
'''


class Database:
    def __init__(self, path: str | Path, timeout: float = 5):
        self.path = Path(path)
        self.timeout = timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as conn:
            conn.executescript(SCHEMA)
            require(conn.execute("SELECT value FROM metadata WHERE key='schemaVersion'").fetchone()[0] == '1', 'Unsupported database version')

    def connect(self) -> sqlite3.Connection:
        # Callers close connections explicitly; the context manager alone does not.
        conn = sqlite3.connect(self.path, timeout=self.timeout, autocommit=True)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        return conn

    def run(self, scope: str, operation_id: str, intent: dict, action: Callable) -> dict:
        require(text(operation_id), 'Operation ID is required')
        digest = hashlib.sha256(encoded(intent).encode()).hexdigest()
        conn = self.connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
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


def save(conn: sqlite3.Connection, record: dict, before: dict | None, operation: str, event_type: str, reason: str) -> dict:
    conn.execute('INSERT INTO research_records VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload',
                 (record['id'], record['kind'], record['revision'], encoded(record)))
    conn.execute('INSERT INTO record_versions VALUES (?,?,?)', (record['id'], record['revision'], encoded(record)))
    event = dict(eventId=str(uuid.uuid4()), recordId=record['id'], scope='research', operationId=operation,
                 time=now(), actor='research', eventType=event_type, reason=reason,
                 before=None if before is None else {'recordId': before['id'], 'revision': before['revision']},
                 after={'recordId': record['id'], 'revision': record['revision']}, evidence=record.get('evidenceIds', []))
    conn.execute('INSERT INTO research_events(event_id,record_id,payload) VALUES (?,?,?)', (event['eventId'], record['id'], encoded(event)))
    return record
