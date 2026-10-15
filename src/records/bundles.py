"""Validate complete research graphs before any import writes."""
from .contracts import fields, require, stamp, text, validate_record


def hash_string(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_bundle(bundle: dict) -> None:
    from .exchange import EVENT_FIELDS, digest
    fields(bundle, {'schemaVersion', 'baseBundleId', 'bundleId', 'data'}, {'schemaVersion', 'baseBundleId', 'bundleId', 'data'})
    require(type(bundle['schemaVersion']) is int and bundle['schemaVersion'] == 1)
    require(bundle['baseBundleId'] is None or hash_string(bundle['baseBundleId']))
    require(bundle['bundleId'] == digest({key: value for key, value in bundle.items() if key != 'bundleId'}), 'Bundle digest mismatch')
    data = bundle['data']
    fields(data, {'records', 'versions', 'events', 'operations'}, {'records', 'versions', 'events', 'operations'})
    require(all(isinstance(items, list) for items in data.values()))
    records, versions = {}, {}
    for record in data['records']:
        validate_record(record)
        require(record['id'] not in records, 'Duplicate ID')
        records[record['id']] = record
    for record in data['versions']:
        validate_record(record)
        key = (record['id'], record['revision'])
        require(key not in versions and record['id'] in records, 'Duplicate or orphan version')
        versions[key] = record
    for id, record in records.items():
        history = sorted(rev for rid, rev in versions if rid == id)
        require(history == list(range(1, record['revision']+1)), 'Version gap')
        require(versions.get((id, record['revision'])) == record, 'Current record differs from latest version')
        for rev in history:
            old = versions[(id, rev)]
            require(old['kind'] == record['kind'] and old['createdAt'] == record['createdAt'], 'Identity changed')
    for record in versions.values():
        kind = record['kind']
        if kind == 'Evidence':
            require(record['sourceId'] in records and records[record['sourceId']]['kind'] == 'Source', 'Bad source')
        if kind == 'Assessment':
            require(record['ideaId'] in records and records[record['ideaId']]['kind'] == 'Idea', 'Bad assessment target')
            require(record['id'] == 'assessment:' + record['ideaId'])
        if kind in ('Trend', 'Idea', 'Assessment'):
            pins = record.get('evidenceVersions', [])
            require([ref['recordId'] for ref in pins] == record['evidenceIds'], 'Evidence pins differ')
            for ref in pins:
                evidence = versions.get((ref['recordId'], ref['revision']))
                require(evidence is not None and evidence['kind'] == 'Evidence', 'Missing evidence version')
        else:
            require('evidenceVersions' not in record)
        for key, target_kind in [('derivedFrom', 'Trend'), ('derivedIdeas', 'Idea')]:
            for target in record.get(key, []):
                require(target in records and records[target]['kind'] == target_kind, 'Bad derivation')
        target = record['mergedInto']
        if target is not None:
            require(target in records and target != record['id'] and records[target]['kind'] == kind, 'Bad merge')
    for id in records:
        seen, current = set(), id
        while current is not None:
            require(current not in seen, 'Merge cycle')
            seen.add(current)
            current = records[current]['mergedInto']
    operations = {}
    for operation in data['operations']:
        fields(operation, {'operationId', 'requestHash', 'result'}, {'operationId', 'requestHash', 'result'})
        require(text(operation['operationId']) and operation['operationId'] not in operations)
        require(hash_string(operation['requestHash']))
        result = operation['result']
        require(isinstance(result, dict))
        results = list(result.values()) if set(result) == {'source', 'target'} else [result]
        for record in results:
            validate_record(record)
            require(versions.get((record['id'], record['revision'])) == record, 'Operation result differs from version')
        operations[operation['operationId']] = operation
    event_ids, covered = set(), set()
    for event in data['events']:
        fields(event, EVENT_FIELDS, EVENT_FIELDS)
        require(text(event['eventId']) and event['eventId'] not in event_ids)
        event_ids.add(event['eventId'])
        require(text(event['recordId']) and text(event['operationId']))
        require(event['recordId'] in records and event['operationId'] in operations)
        require(event['scope'] == 'research' and event['actor'] == 'research' and stamp(event['time']))
        require(event['eventType'] in ('created', 'updated', 'assessment_saved', 'merge', 'unmerge', 'derive'))
        require(text(event['reason']))
        ref = event['after']
        fields(ref, {'recordId', 'revision'}, {'recordId', 'revision'})
        require(text(ref['recordId']) and type(ref['revision']) is int)
        key = (ref['recordId'], ref['revision'])
        require(ref['recordId'] == event['recordId'] and key in versions and key not in covered)
        if ref['revision'] == 1:
            require(event['before'] is None)
        else:
            require(event['before'] == {'recordId': ref['recordId'], 'revision': ref['revision']-1})
            require((ref['recordId'], ref['revision']-1) in covered, 'Events out of order')
        require(event['evidence'] == versions[key].get('evidenceVersions', []))
        covered.add(key)
    require(covered == versions.keys(), 'Missing version events')


def extends(local: dict, incoming: dict) -> bool:
    """A remote descendant must preserve every local immutable value."""
    if not {r['id'] for r in local['records']} <= {r['id'] for r in incoming['records']}:
        return False
    if incoming['events'][:len(local['events'])] != local['events']:
        return False
    versions = {(r['id'], r['revision']): r for r in incoming['versions']}
    operations = {r['operationId']: r for r in incoming['operations']}
    return (all(versions.get((r['id'], r['revision'])) == r for r in local['versions']) and
            all(operations.get(r['operationId']) == r for r in local['operations']))
