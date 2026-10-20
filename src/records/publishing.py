"""One fenced, idempotent research write and its local completion receipt."""
import json

from .contracts import Fault, PRIVATE, boundary, encoded, fields, require, text
from .exchange import digest
from .runtime import get_run
from .service import create_research_in, patch_research_in
from .storage import get


def validate_request(request):
    require(isinstance(request, dict))
    action = request.get('action')
    if action == 'create':
        fields(request, {'action', 'record', 'reason'}, {'action', 'record', 'reason'})
        require(isinstance(request['record'], dict) and text(request['reason']))
    elif action == 'patch':
        keys = {'action', 'recordId', 'expectedRevision', 'patch', 'reason'}
        fields(request, keys, keys)
        require(text(request['recordId']) and type(request['expectedRevision']) is int and
                request['expectedRevision'] > 0 and isinstance(request['patch'], dict) and text(request['reason']))
    else:
        raise Fault('VALIDATION_ERROR', 'Unknown publishing action')


def validate_plan(plan,run_id=None):
    """Keep the local request bodies identical to the public manifest commitments."""
    from .artifacts import hash_value,validate_artifact
    fields(plan,{'manifestId','draftHash','manifestRequest','steps'},
           {'manifestId','draftHash','manifestRequest','steps'})
    require(text(plan['manifestId']) and hash_value(plan['draftHash']))
    validate_request(plan['manifestRequest'])
    require(plan['manifestRequest']['action']=='create')
    manifest=plan['manifestRequest']['record']
    require(manifest.get('id')==plan['manifestId'] and manifest.get('kind')=='ResearchArtifact' and
            manifest.get('artifactType')=='PublicationManifest')
    validate_artifact(manifest)
    require(run_id is None or manifest['data']['runId']==run_id)
    require(isinstance(plan['steps'],list) and len(plan['steps'])==len(manifest['data']['steps']))
    seen=set()
    for local,public in zip(plan['steps'],manifest['data']['steps']):
        fields(local,{'stepId','request'},{'stepId','request'})
        require(text(local['stepId']) and local['stepId'] not in seen and local['stepId']==public['stepId'])
        validate_request(local['request'])
        request=local['request']
        target=request['record'].get('id') if request['action']=='create' else request['recordId']
        require(text(target))
        expected=None if request['action']=='create' else request['expectedRevision']
        require(public['targetId']==target and public['expectedRevision']==expected and
                public['requestHash']==digest(request))
        seen.add(local['stepId'])


def validate_manifest_progress(plan,record):
    """Allow result confirmations while keeping every prepared commitment fixed."""
    from .artifacts import validate_artifact
    validate_plan(plan)
    require(record.get('id')==plan['manifestId'] and record.get('kind')=='ResearchArtifact' and
            record.get('artifactType')=='PublicationManifest')
    validate_artifact(record)
    require(not record.get('archived') and record.get('mergedInto') is None)
    prepared=plan['manifestRequest']['record']['data'];current=record['data']
    require({key:value for key,value in current.items() if key!='steps'}==
            {key:value for key,value in prepared.items() if key!='steps'})
    require(len(current['steps'])==len(prepared['steps']))
    for actual,expected in zip(current['steps'],prepared['steps']):
        require({key:value for key,value in actual.items() if key!='result'}==
                {key:value for key,value in expected.items() if key!='result'})


def validate_observation(conn, record):
    """New Evidence must stay bound to the exact Reader output used by analysis."""
    if record['kind'] != 'Evidence':
        return
    require('observation' in record, 'Published research evidence requires a reading observation')
    observation = record['observation']
    receipt = get(conn, observation['receiptId'])
    require(receipt['kind'] == 'ResearchArtifact' and receipt['artifactType'] == 'ReadReceipt')
    data = receipt['data']
    require(data['status'] in ('readable', 'partial') and data['sourceId'] == record['sourceId'])
    require(record['url'] in (data['originalUrl'], data['finalUrl']))
    require(set(observation['blockIds']) <= {block['blockId'] for block in data['blocks']},
            'Evidence cites a block that Reader did not observe')
    require(set(observation['replyIds']) <= set(observation['blockIds']),
            'Reply locators must refer to observed blocks')
    require(record['accessedAt'] == data['fetchedAt'], 'Evidence access time must come from the receipt')
    require(observation['precision'] == data['precision'] and observation['dateBasis'] == data['dateBasis'])
    if data['precision'] == 'date':
        require(record.get('publishedDate') == data['publishedDate'] and record['publishedAt'] is None)
    elif data['precision'] == 'instant':
        require(record['publishedAt'] == data['publishedAt'] and 'publishedDate' not in record)
    else:
        require(record['publishedAt'] is None and 'publishedDate' not in record)


class ResearchPublisher:
    def __init__(self, runtime, before_commit=None):
        self.runtime = runtime
        self.before_commit = before_commit

    @boundary
    def publish_step(self, run_id, token, intent_id, request):
        require(text(run_id) and text(intent_id))
        validate_request(request)
        request_hash = digest(request)

        def action(conn):
            self.runtime.execution.guard(conn, run_id, token)
            get_run(conn, run_id)
            row = conn.execute(
                'SELECT request_hash,payload FROM research_intents WHERE run_id=? AND intent_id=?',
                (run_id, intent_id)).fetchone()
            if row is None:
                raise Fault('NOT_FOUND', 'Publishing intent not found')
            item = json.loads(row['payload'])
            intent = item['intent']
            require(item['status'] in ('pending', 'completed'))
            if row['request_hash'] != digest(intent) or intent['requestHash'] != request_hash:
                raise Fault('IDEMPOTENCY_CONFLICT', 'Publishing request differs from saved intent')
            target_id = request['record']['id'] if request['action'] == 'create' else request['recordId']
            require(intent['recordId'] == target_id, 'Publishing target differs from saved intent')
            require(intent['expectedRevision'] ==
                    (None if request['action'] == 'create' else request['expectedRevision']))

            if item['status'] == 'completed':
                result = item['result']
                version = conn.execute(
                    'SELECT payload FROM record_versions WHERE record_id=? AND revision=?',
                    (result['recordId'], result['revision'])).fetchone()
                require(version is not None, 'Completed publishing receipt lost its record version')
                return {'record': json.loads(version[0]), 'result': result}

            operation = conn.execute('SELECT request_hash,result FROM operations WHERE scope=? AND key=?',
                                     ('research', intent['operationId'])).fetchone()
            if operation is not None:
                if operation['request_hash'] != request_hash:
                    raise Fault('IDEMPOTENCY_CONFLICT', 'Business operation ID has another request')
                record = json.loads(operation['result'])
                require(record['id'] == target_id, 'Business operation result has another target')
                version = conn.execute(
                    'SELECT 1 FROM record_versions WHERE record_id=? AND revision=?',
                    (record['id'], record['revision'])).fetchone()
                require(version is not None, 'Business operation lost its record version')
            elif request['action'] == 'create':
                record = request['record']
                require(record.get('kind') != 'Assessment' and not (PRIVATE & record.keys()))
                validate_observation(conn, record)
                record = create_research_in(conn, record, intent['operationId'], request['reason'])
                conn.execute('INSERT INTO operations VALUES (?,?,?,?)',
                             ('research', intent['operationId'], request_hash, encoded(record)))
            else:
                require(not (PRIVATE & request['patch'].keys()))
                before = get(conn, request['recordId'])
                require(before['kind'] != 'Assessment')
                if before['kind'] == 'Evidence':
                    validate_observation(conn, before | request['patch'])
                record = patch_research_in(conn, request['recordId'], request['expectedRevision'],
                                           request['patch'], request['reason'], intent['operationId'])
                conn.execute('INSERT INTO operations VALUES (?,?,?,?)',
                             ('research', intent['operationId'], request_hash, encoded(record)))

            result = {'recordId': record['id'], 'revision': record['revision']}
            item.update(status='completed', result=result)
            conn.execute('UPDATE research_intents SET payload=? WHERE run_id=? AND intent_id=?',
                         (encoded(item), run_id, intent_id))
            if self.before_commit is not None:
                self.before_commit(conn)
            return {'record': record, 'result': result}

        return self.runtime.execution.transaction(action)
