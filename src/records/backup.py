"""Validated SQLite backup and restore, always to a new file."""
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from .bundles import validate_bundle
from .contracts import boundary, require
from .exchange import digest, snapshot

TABLES = ('research_records', 'record_versions', 'research_events', 'evidence_links',
          'personal_states', 'personal_events', 'operations', 'metadata')


def validate_database(conn) -> dict:
    require(conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Database integrity check failed')
    require(not conn.execute('PRAGMA foreign_key_check').fetchall(), 'Broken database references')
    require(conn.execute("SELECT value FROM metadata WHERE key='schemaVersion'").fetchone()[0] == '1', 'Unsupported database version')
    bundle = dict(schemaVersion=1, baseBundleId=None, data=snapshot(conn))
    bundle['bundleId'] = digest(bundle)
    validate_bundle(bundle)
    # Full local rows are compared inside this process, never returned or exported.
    counts, hashes = {}, {}
    for table in TABLES:
        rows = [tuple(row) for row in conn.execute(f'SELECT * FROM {table} ORDER BY 1,2')]
        counts[table] = len(rows)
        hashes[table] = digest(rows)
    return dict(counts=counts, hashes=hashes)


def copy_validated(source: Path, target: Path) -> dict:
    require(source.is_file(), 'Source database does not exist')
    require(not target.exists() and not target.is_symlink(), 'Destination already exists; use a new path')
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=target.parent, prefix='.records-backup-')
    os.close(fd)
    try:
        with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro', uri=True, autocommit=True)) as src:
            src.row_factory = sqlite3.Row
            src.execute('PRAGMA foreign_keys=ON')
            src.execute('BEGIN')
            expected = validate_database(src)
            with closing(sqlite3.connect(name, autocommit=True)) as dst:
                dst.row_factory = sqlite3.Row
                src.backup(dst)
                actual = validate_database(dst)
                require(actual == expected, 'Backup verification differs')
            src.execute('ROLLBACK')
        with open(name, 'rb') as handle:
            os.fsync(handle.fileno())
        # Hard-link publication is atomic and cannot replace a racing target.
        os.link(name, target)
        directory = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return dict(counts=actual['counts'], scope='local-including-personal')
    finally:
        os.unlink(name)


@boundary
def backup_local(source: str | Path, output: str | Path) -> dict:
    return copy_validated(Path(source), Path(output))


@boundary
def restore_local(source: str | Path, output: str | Path) -> dict:
    return copy_validated(Path(source), Path(output))
