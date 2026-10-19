"""Fixed public research metadata; local queues and raw bodies do not belong here."""
from .contracts import fields, require, text, string_list, stamp, date_valid, valid_url

_READER_AUTHORITY = object()  # In-process capability; never accepted from JSON.
SHAPES = {
    'ReadReceipt': 'runId sourceId originalUrl finalUrl fetchedAt status executor visibleScope truncated fingerprint blocks publishedAt publishedDate precision dateBasis error',
    'CandidateOutcome': 'runId candidateId sourceId locator status reason nextCondition recordRefs',
    'PublicationManifest': 'runId candidateId sourceId steps supersedes',
    'SourceCheckpoint': 'sourceId order discovered completed gaps processed overlapStrategy lastReceipt',
    'CoverageReview': 'runIds sourceRefs evidenceRefs gaps qualityReasons recommendation reason',
}


def ref(value):
    fields(value, {'recordId', 'revision'}, {'recordId', 'revision'})
    require(text(value['recordId']) and type(value['revision']) is int and value['revision'] > 0)


def refs(values):
    require(isinstance(values, list))
    for value in values:
        ref(value)
    require(len({(v['recordId'], v['revision']) for v in values}) == len(values))


def hash_value(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_artifact(record):
    kind, data = record['artifactType'], record['data']
    require(isinstance(kind, str) and kind in SHAPES, 'Unknown artifact type')
    keys = set(SHAPES[kind].split())
    fields(data, keys, keys)
    require(not ({'legacy', 'derivedFrom', 'derivedIdeas', 'evidenceVersions'} & record.keys()))
    for key in ('sourceId', 'runId', 'candidateId', 'reason'):
        if key in data:
            require(text(data[key]))
    if kind == 'ReadReceipt':
        validate_receipt(data)
    elif kind == 'CandidateOutcome':
        require(text(data['locator']))
        require(data['status'] in ('deferred', 'rejected', 'unchanged', 'duplicate', 'trend', 'idea', 'update'))
        require(data['nextCondition'] is None or text(data['nextCondition']))
        refs(data['recordRefs'])
        if data['status'] == 'deferred':
            require(text(data['nextCondition']))
        if data['status'] in ('duplicate', 'trend', 'idea', 'update'):
            require(bool(data['recordRefs']))
    elif kind == 'PublicationManifest':
        validate_manifest(data)
    elif kind == 'SourceCheckpoint':
        require(data['order'] in ('ordered', 'unordered'))
        require(all(data[key] is None or text(data[key]) for key in ('discovered', 'completed')))
        require(string_list(data['gaps']) and string_list(data['processed']) and text(data['overlapStrategy']))
        require(not set(data['gaps']) & set(data['processed']))
        if data['order'] == 'unordered':
            require(data['completed'] is None, 'Unordered sources have no completion watermark')
        if data['lastReceipt'] is not None:
            ref(data['lastReceipt'])
    else:
        require(string_list(data['runIds']) and bool(data['runIds']))
        refs(data['sourceRefs']); refs(data['evidenceRefs'])
        require(bool(data['sourceRefs']) and string_list(data['gaps']))
        require(string_list(data['qualityReasons']) and bool(data['qualityReasons']))
        require(data['recommendation'] in ('concentrate', 'incremental', 'adjust'))


def validate_manifest(data):
    require(isinstance(data['steps'], list) and bool(data['steps']))
    seen, operations = set(), set()
    for step in data['steps']:
        keys = set('stepId targetId operationId requestHash expectedRevision dependsOn result'.split())
        fields(step, keys, keys)
        require(all(text(step[k]) for k in ('stepId', 'targetId', 'operationId')))
        require(step['stepId'] not in seen and step['operationId'] not in operations)
        require(hash_value(step['requestHash']))
        require(step['expectedRevision'] is None or (type(step['expectedRevision']) is int and step['expectedRevision'] > 0))
        require(string_list(step['dependsOn']) and set(step['dependsOn']) <= seen, 'Steps must be in dependency order')
        if step['result'] is not None:
            ref(step['result'])
            require(step['result']['recordId'] == step['targetId'])
        seen.add(step['stepId']); operations.add(step['operationId'])
    if data['supersedes'] is not None:
        ref(data['supersedes'])


def validate_receipt(data):
    require(valid_url(data['originalUrl']) and valid_url(data['finalUrl']))
    require(stamp(data['fetchedAt']) and data['executor'] == 'public-reader')
    require(data['status'] in ('readable', 'partial', 'restricted', 'failed'))
    require(text(data['visibleScope']) and type(data['truncated']) is bool)
    require(data['fingerprint'] is None or hash_value(data['fingerprint']))
    require(isinstance(data['blocks'], list))
    seen = set()
    for block in data['blocks']:
        fields(block, {'blockId', 'summary'}, {'blockId', 'summary'})
        require(text(block['blockId']) and block['blockId'] not in seen)
        require(text(block['summary']) and len(block['summary']) <= 500)
        seen.add(block['blockId'])
    if data['status'] in ('readable', 'partial'):
        require(bool(seen) and hash_value(data['fingerprint']))
    else:
        require(not seen)
    if data['status'] == 'readable':
        require(not data['truncated'] and data['error'] is None)
    precision = data['precision']
    require(precision in ('unknown', 'date', 'instant'))
    if precision == 'unknown':
        require(data['publishedAt'] is None and data['publishedDate'] is None and data['dateBasis'] is None)
    elif precision == 'date':
        require(isinstance(data['publishedDate'], str) and len(data['publishedDate']) == 10 and date_valid(data['publishedDate']))
        require(data['publishedAt'] is None and text(data['dateBasis']))
    else:
        require(stamp(data['publishedAt']) and data['publishedDate'] is None and text(data['dateBasis']))
    if data['error'] is not None:
        fields(data['error'], {'code', 'retryable', 'condition'}, {'code', 'retryable', 'condition'})
        require(data['error']['code'] in ('timeout', 'network', 'restricted', 'unsupported', 'size', 'parse', 'budget'))
        require(type(data['error']['retryable']) is bool and text(data['error']['condition']))


def validate_references(record, lookup):
    """Use the same graph checks for a live transaction and a complete import."""
    data, kind = record['data'], record['artifactType']
    if 'sourceId' in data:
        require(lookup(data['sourceId'], None)['kind'] == 'Source', 'Artifact requires source')
    pins = []
    if kind == 'CandidateOutcome':
        pins = [(value, None) for value in data['recordRefs']]
    elif kind == 'PublicationManifest':
        pins = [(step['result'], None) for step in data['steps'] if step['result'] is not None]
        if data['supersedes'] is not None:
            pins.append((data['supersedes'], 'PublicationManifest'))
    elif kind == 'SourceCheckpoint' and data['lastReceipt'] is not None:
        pins = [(data['lastReceipt'], 'ReadReceipt')]
    elif kind == 'CoverageReview':
        pins = [(value, 'Source') for value in data['sourceRefs']] + [(value, 'Evidence') for value in data['evidenceRefs']]
    for pin, expected_kind in pins:
        target = lookup(pin['recordId'], pin['revision'])
        if expected_kind:
            require(target['kind'] == expected_kind or
                    (target['kind'] == 'ResearchArtifact' and target['artifactType'] == expected_kind), 'Wrong referenced type')
        if expected_kind == 'ReadReceipt':
            require(target['data']['sourceId'] == data['sourceId'], 'Receipt belongs to another source')
