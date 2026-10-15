"""Explicit public snapshots. Never serialize personal tables or raw SQL dumps."""
import hashlib
import json
import os
import tempfile
from contextlib import closing
from pathlib import Path
from .contracts import BASE, FIELDS, SYSTEM_LINKS, boundary, encoded, fields, validate_record
from .storage import Database

EVENT_FIELDS = {'eventId', 'recordId', 'scope', 'operationId', 'time', 'actor', 'eventType', 'before', 'after', 'reason', 'evidence'}


def digest(value: dict) -> str:
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def public_record(record: dict) -> dict:
    validate_record(record)
    allowed = BASE | FIELDS[record['kind']] | SYSTEM_LINKS
    return {key: record[key] for key in sorted(allowed) if key in record}


def public_result(result: dict) -> dict:
    if set(result) == {'source', 'target'}:
        return {key: public_record(result[key]) for key in ('source', 'target')}
    return public_record(result)


def snapshot(conn) -> dict:
    records = [public_record(json.loads(row[0])) for row in conn.execute('SELECT payload FROM research_records ORDER BY id')]
    versions = [public_record(json.loads(row[0])) for row in conn.execute('SELECT payload FROM record_versions ORDER BY record_id,revision')]
    events = []
    for row in conn.execute('SELECT payload FROM research_events ORDER BY seq'):
        event = json.loads(row[0])
        fields(event, EVENT_FIELDS, EVENT_FIELDS)
        events.append({key: event[key] for key in sorted(EVENT_FIELDS)})
    operations = [dict(operationId=row['key'], requestHash=row['request_hash'], result=public_result(json.loads(row['result'])))
                  for row in conn.execute("SELECT key,request_hash,result FROM operations WHERE scope='research' ORDER BY key")]
    return dict(records=records, versions=versions, events=events, operations=operations)


def checkpoint(conn) -> dict | None:
    row = conn.execute("SELECT value FROM metadata WHERE key='checkpoint'").fetchone()
    return json.loads(row[0]) if row else None


def mark_checkpoint(conn, bundle: dict) -> None:
    value = dict(bundleId=bundle['bundleId'], baseBundleId=bundle['baseBundleId'], contentHash=digest(bundle['data']))
    conn.execute("INSERT INTO metadata VALUES ('checkpoint',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (encoded(value),))


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as handle:
            name = handle.name
            handle.write(encoded(payload) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


class Exchange:
    def __init__(self, path):
        self.db = Database(path)

    @boundary
    def export_research(self, output: str | Path) -> dict:
        # Serialize local exports with writers, including checkpoint publication.
        with closing(self.db.connect()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            try:
                data = snapshot(conn)
                previous = checkpoint(conn)
                unchanged = previous and previous['contentHash'] == digest(data)
                base = (previous['baseBundleId'] if unchanged else previous['bundleId']) if previous else None
                bundle = dict(schemaVersion=1, baseBundleId=base, data=data)
                bundle['bundleId'] = digest(bundle)
                atomic_json(Path(output), bundle)
                mark_checkpoint(conn, bundle)
                conn.execute('COMMIT')
                return dict(bundleId=bundle['bundleId'], scope='research', records=len(data['records']))
            finally:
                if conn.in_transaction:
                    conn.execute('ROLLBACK')
