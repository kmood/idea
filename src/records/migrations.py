"""Explicit version upgrades, validated in a new unpublished backup copy."""
import uuid
from pathlib import Path
from .backup import copy_validated
from .contracts import boundary, require
from .storage import database_version


def migrate_v1(conn) -> None:
    require(database_version(conn) == '1', 'Only v1 databases can be upgraded')
    conn.execute('BEGIN IMMEDIATE')
    try:
        conn.execute("UPDATE metadata SET value='2' WHERE key='schemaVersion'")
        conn.execute("INSERT OR REPLACE INTO metadata VALUES ('dbInstanceId', ?)", (str(uuid.uuid4()),))
        conn.execute('COMMIT')
    finally:
        if conn.in_transaction:
            conn.execute('ROLLBACK')


@boundary
def upgrade_database(source: str | Path, output: str | Path) -> dict:
    result = copy_validated(Path(source), Path(output), transform=migrate_v1)
    return result | {'schemaVersion': 2}
