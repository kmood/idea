"""Validated wire values and safe, structured errors."""
import functools
import json
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlsplit

Result = dict[str, Any]
PRIVATE = {'favorite', 'ignored', 'validationStage', 'notes'}
BASE = {'schemaVersion', 'id', 'kind', 'revision', 'createdAt', 'updatedAt', 'archived', 'mergedInto'}
SYSTEM_LINKS = {'evidenceVersions', 'derivedFrom', 'derivedIdeas'}
FIELDS = {'Source': {'name', 'url', 'audience', 'languages', 'accessStatus', 'lastAttempt', 'lastSuccess'}}

FIELDS.update({
    'Evidence': {'sourceId', 'url', 'claim', 'summary', 'publishedAt', 'accessedAt', 'nature', 'level', 'paymentSignal', 'rebutsClaim'},
    'Trend': {'title', 'summary', 'evidenceIds', 'impact', 'questions'},
    'Idea': {'title', 'audience', 'problem', 'earningHypothesis', 'industry', 'sideHustleTypes', 'markets', 'researchStatus', 'evidenceIds'},
})


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
    require(isinstance(kind, str) and kind in FIELDS, 'Unknown record kind')
    fields(record, BASE | FIELDS[kind] | SYSTEM_LINKS, BASE | FIELDS[kind])
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

    elif kind == 'Evidence':
        require(all(text(record[k]) for k in ('sourceId', 'url', 'claim', 'summary')))
        require(urlsplit(record['url']).scheme in ('https', 'http') and bool(urlsplit(record['url']).hostname))
        require(stamp(record['publishedAt'], True) and stamp(record['accessedAt']))
        require(record['nature'] in ('fact', 'author_claim', 'inference'))
        require(record['level'] in ('E0', 'E1', 'E2', 'E3'))
        require(record['paymentSignal'] in (None, 'intent', 'quote', 'paid'))
        require(record['rebutsClaim'] is None or text(record['rebutsClaim']))
    else:
        require(text(record['title']))
        require(string_list(record['evidenceIds']) and bool(record['evidenceIds']))
        if kind == 'Idea':
            require(all(text(record[k]) for k in ('audience', 'problem', 'earningHypothesis')))
            require(all(string_list(record[k]) and record[k] for k in ('industry', 'sideHustleTypes', 'markets')))
            require(record['researchStatus'] in ('待验证', '候选', '优先验证', '搁置', '淘汰'))
        else:
            require(text(record['summary']) and string_list(record['questions']))
            fields(record['impact'], {'nature', 'text'}, {'nature', 'text'})
            require(record['impact']['nature'] in ('fact', 'author_claim', 'inference') and text(record['impact']['text']))
    for key in ('derivedFrom', 'derivedIdeas'):
        if key in record:
            require(string_list(record[key]))
    if 'evidenceVersions' in record:
        require(isinstance(record['evidenceVersions'], list))
        for ref in record['evidenceVersions']:
            fields(ref, {'recordId', 'revision'}, {'recordId', 'revision'})
            require(text(ref['recordId']) and type(ref['revision']) is int and ref['revision'] > 0)


def string_list(value: Any) -> bool:
    return isinstance(value, list) and all(text(x) for x in value) and len(set(value)) == len(value)
