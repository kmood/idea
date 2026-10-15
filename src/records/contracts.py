"""Validated wire values and safe, structured errors."""
import functools
import json
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlsplit

Result = dict[str, Any]
PRIVATE = {'favorite', 'ignored', 'validationStage', 'notes'}
BASE = {'schemaVersion', 'id', 'kind', 'revision', 'createdAt', 'updatedAt', 'archived', 'mergedInto'}
FIELDS = {'Source': {'name', 'url', 'audience', 'languages', 'accessStatus', 'lastAttempt', 'lastSuccess'}}


class Fault(Exception):
    def __init__(self, code: str, message: str = 'Request rejected', **details: Any):
        self.error = dict(code=code, message=message, **details)


def require(condition: bool, message: str = 'Invalid input') -> None:
    if not condition:
        raise Fault('VALIDATION_ERROR', message)


def boundary(fn: Callable) -> Callable:
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        import sqlite3
        try:
            return {'ok': True, 'value': fn(*args, **kwargs)}
        except Fault as exc:
            return {'ok': False, 'error': exc.error}
        except (sqlite3.Error, OSError):
            return {'ok': False, 'error': {'code': 'STORAGE_ERROR', 'message': 'Storage unavailable; retry the same operation ID'}}
    return wrapped


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def stamp(value: Any, nullable: bool = False) -> bool:
    if value is None:
        return nullable
    try:
        return isinstance(value, str) and datetime.fromisoformat(value).utcoffset() is not None
    except ValueError:
        return False


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encoded(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError):
        raise Fault('VALIDATION_ERROR', 'Expected finite JSON data') from None


def fields(value: Any, allowed: set[str], required: set[str] = frozenset()) -> None:
    require(isinstance(value, dict))
    if PRIVATE & value.keys() and not PRIVATE <= allowed:
        raise Fault('SCOPE_VIOLATION', 'Personal fields require the personal interface')
    require(required <= value.keys() and value.keys() <= allowed, 'Missing or unknown fields')
    encoded(value)


def validate_record(record: dict) -> None:
    require(isinstance(record, dict))
    kind = record.get('kind')
    require(kind in FIELDS, 'Unknown record kind')
    fields(record, BASE | FIELDS[kind], BASE | FIELDS[kind])
    require(text(record['id']) and type(record['revision']) is int and record['revision'] > 0)
    require(type(record['schemaVersion']) is int and record['schemaVersion'] == 1)
    require(stamp(record['createdAt']) and stamp(record['updatedAt']))
    require(type(record['archived']) is bool and (record['mergedInto'] is None or text(record['mergedInto'])))
    if kind == 'Source':
        require(text(record['name']))
        require(text(record['url']) and urlsplit(record['url']).scheme in {'https', 'http'} and bool(urlsplit(record['url']).hostname))
        for key in ('audience', 'languages'):
            require(isinstance(record[key], list) and bool(record[key]) and all(text(x) for x in record[key]))
        require(record['accessStatus'] in ('untried', 'readable', 'restricted', 'failed'))
        require(stamp(record['lastAttempt'], True) and stamp(record['lastSuccess'], True))
