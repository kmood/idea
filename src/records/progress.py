"""Durable local sampling state; public checkpoints are published separately."""
import json
import math
from contextlib import closing

from .contracts import Fault,boundary,encoded,fields,require,string_list,text
from .exchange import digest
from .runtime import get_run,validate_replay
from .storage import get

TABLE='research_progress'
STATE_KEYS={'sourceId','order','positions','discovered','completed','gaps','processed',
            'overlapStrategy','attempts','cursorInvalid','lastReceipt'}
ATTEMPT_KEYS={'count','inFlight','retryable','retryAt','lastError'}


def validate_state(state):
    fields(state,STATE_KEYS,STATE_KEYS)
    require(text(state['sourceId']) and state['order'] in ('ordered','unordered'))
    require(string_list(state['positions']) and len(state['positions'])<=1000)
    require(all(len(item)<=500 for item in state['positions']))
    require(state['discovered'] is None or text(state['discovered']))
    require(state['completed'] is None or text(state['completed']))
    require(string_list(state['gaps']) and string_list(state['processed']))
    require(set(state['gaps'])<=set(state['positions']) and set(state['processed'])<=set(state['positions']))
    require(not set(state['gaps'])&set(state['processed']) and text(state['overlapStrategy']))
    require((state['discovered'] is None or len(state['discovered'])<=2000) and
            len(state['overlapStrategy'])<=2000)
    require(type(state['cursorInvalid']) is bool and isinstance(state['attempts'],dict))
    require(state['lastReceipt'] is None or
            (isinstance(state['lastReceipt'],dict) and set(state['lastReceipt'])=={'recordId','revision'} and
             text(state['lastReceipt']['recordId']) and type(state['lastReceipt']['revision']) is int and
             state['lastReceipt']['revision']>0))
    if state['order']=='unordered':require(state['completed'] is None)
    elif state['completed'] is not None:require(state['completed'] in state['processed'])
    for position,attempt in state['attempts'].items():
        require(position in state['positions']);fields(attempt,ATTEMPT_KEYS,ATTEMPT_KEYS)
        require(type(attempt['count']) is int and 0<=attempt['count']<=2)
        require(type(attempt['inFlight']) is bool and type(attempt['retryable']) is bool)
        require(attempt['retryAt'] is None or
                (type(attempt['retryAt']) in (int,float) and math.isfinite(attempt['retryAt'])))
        require(attempt['lastError'] is None or text(attempt['lastError']))


class ProgressStore:
    def __init__(self,runtime):
        self.runtime=runtime
        with closing(runtime.db.connect()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute(f'''CREATE TABLE IF NOT EXISTS {TABLE}(
                run_id TEXT NOT NULL REFERENCES research_runs(run_id),
                source_id TEXT NOT NULL,operation_id TEXT NOT NULL,payload TEXT NOT NULL,
                PRIMARY KEY(run_id,source_id))''')
            conn.execute('COMMIT')

    @boundary
    def load(self,run_id,source_id,*,token=None):
        require(text(run_id) and text(source_id))
        def action(conn):
            self.runtime.execution.guard(conn,run_id,token)
            row=conn.execute(f'SELECT payload FROM {TABLE} WHERE run_id=? AND source_id=?',
                             (run_id,source_id)).fetchone()
            if row is None:raise Fault('NOT_FOUND','Source progress has not been initialized')
            state=json.loads(row[0]);validate_state(state);return state
        return self.runtime.execution.transaction(action)

    @boundary
    def save(self,run_id,source_id,state,operation_id,*,token=None):
        require(text(run_id) and text(source_id) and text(operation_id))
        validate_state(state);require(state['sourceId']==source_id)
        require(len(encoded(state).encode())<=1024*1024,'Source progress is too large')
        def action(conn):
            get_run(conn,run_id)
            source=get(conn,source_id)
            require(source['kind']=='Source' and not source['archived'] and source['mergedInto'] is None)
            conn.execute(f'''INSERT INTO {TABLE} VALUES (?,?,?,?)
                ON CONFLICT(run_id,source_id) DO UPDATE SET
                    operation_id=excluded.operation_id,payload=excluded.payload''',
                (run_id,source_id,operation_id,encoded(state)))
            return state
        return self.runtime.db.run('runtime-progress:'+run_id,operation_id,state,action,
                                   guard=lambda conn:self.runtime.execution.guard(conn,run_id,token))


def validate_progress(conn):
    for row in conn.execute(f'SELECT * FROM {TABLE}'):
        get_run(conn,row['run_id']);state=json.loads(row['payload']);validate_state(state)
        require(state['sourceId']==row['source_id'])
        require(get(conn,row['source_id'])['kind']=='Source')
        require(text(row['operation_id']))
        validate_replay(conn,'runtime-progress:'+row['run_id'],row['operation_id'],digest(state),state)
