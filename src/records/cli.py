"""File-based JSON requests with a deliberately small action allowlist."""
import argparse
import inspect
import json
import re
from pathlib import Path
from .backup import backup_local, restore_local
from .contracts import Fault, boundary, encoded, require
from .exchange import Exchange, atomic_json
from .legacy import apply_preview, preview_legacy
from .personal import PersonalStore
from .relations import Relations
from .service import ResearchStore

RESEARCH_ACTIONS = {'createResearch': 'create_research', 'patchResearch': 'patch_research',
                    'readRecord': 'read_record', 'listRecords': 'list_records', 'listHistory': 'list_history',
                    'saveAssessment': 'save_assessment'}
RELATION_ACTIONS = {'mergeRecords': 'merge_records', 'unmergeRecords': 'unmerge_records', 'linkDerivedIdea': 'link_derived_idea'}
PERSONAL_ACTIONS = {'readRecord': 'read_record', 'setPersonalState': 'set_personal_state',
                    'listHistory': 'list_history', 'relatedStates': 'related_states'}


def load_json(path: str) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON field')
            result[key] = value
        return result
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError):
        raise Fault('VALIDATION_ERROR', 'Invalid UTF-8 JSON input') from None
    require(isinstance(value, dict), 'JSON object required')
    return value


def unwrap(result: dict):
    if not result['ok']:
        error = dict(result['error'])
        raise Fault(error.pop('code'), error.pop('message'), **error)
    return result['value']


@boundary
def execute(args) -> dict:
    if args.command == 'restore':
        return unwrap(restore_local(args.input, args.output))
    if args.command == 'legacy-preview':
        preview = unwrap(preview_legacy(args.root, load_json(args.mapping) if args.mapping else None))
        require(Path(args.output).resolve() != Path(args.db).resolve(), 'Output cannot replace database')
        atomic_json(Path(args.output), preview)
        return dict(previewId=preview['previewId'], records=len(preview['records']), unresolved=preview['unresolved'])
    if args.command == 'legacy-apply':
        return unwrap(apply_preview(args.root, load_json(args.input), args.db, args.operation_id))
    if args.command == 'backup':
        return unwrap(backup_local(args.db, args.output))
    if args.command == 'export':
        return unwrap(Exchange(args.db).export_research(args.output))
    if args.command == 'import':
        return unwrap(Exchange(args.db).import_research(load_json(args.input), args.operation_id))
    if args.command == 'init':
        ResearchStore(args.db)
        return dict(schemaVersion=1, scope='local')
    request = load_json(args.input)
    action = request.get('action')
    require(isinstance(action, str), 'Action required')
    if args.scope == 'personal':
        actions, owner = PERSONAL_ACTIONS, PersonalStore
    elif action in RELATION_ACTIONS:
        actions, owner = RELATION_ACTIONS, Relations
    else:
        actions, owner = RESEARCH_ACTIONS, ResearchStore
    if action not in actions:
        raise Fault('SCOPE_VIOLATION', 'Action unavailable in selected scope')
    method = getattr(owner(args.db), actions[action])
    # Reject aliases such as expected_revision; the external contract is camelCase.
    names = {re.sub(r'_([a-z])', lambda m: m[1].upper(), key): key for key in inspect.signature(method).parameters}
    require(request.keys() <= names.keys() | {'action'}, 'Unknown request fields')
    kwargs = {names[key]: value for key, value in request.items() if key != 'action'}
    try:
        inspect.signature(method).bind(**kwargs)
    except TypeError:
        raise Fault('VALIDATION_ERROR', 'Missing request fields') from None
    return unwrap(method(**kwargs))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Fault('VALIDATION_ERROR', 'Invalid command arguments; see --help')


def main(argv=None) -> int:
    parser = Parser(description='Local research records; personal data stays in the local database.')
    parser.add_argument('--db', default='.local/records.sqlite3')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    request = sub.add_parser('request')
    request.add_argument('--scope', choices=('research', 'personal'), default='research')
    request.add_argument('--input', required=True)
    for command in ('export', 'backup'):
        sub.add_parser(command).add_argument('--output', required=True)
    restore = sub.add_parser('restore')
    restore.add_argument('--input', required=True); restore.add_argument('--output', required=True)
    imports = sub.add_parser('import')
    imports.add_argument('--input', required=True); imports.add_argument('--operation-id', required=True)
    preview = sub.add_parser('legacy-preview')
    preview.add_argument('--root', required=True); preview.add_argument('--mapping'); preview.add_argument('--output', required=True)
    apply = sub.add_parser('legacy-apply')
    apply.add_argument('--root', required=True); apply.add_argument('--input', required=True); apply.add_argument('--operation-id', required=True)
    try:
        result = execute(parser.parse_args(argv))
    except Fault as exc:
        result = {'ok': False, 'error': exc.error}
    print(encoded(result))
    return 0 if result['ok'] else 2
