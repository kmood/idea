"""Small JSON-file CLI for bounded Agent research handoffs."""
import argparse

from records.cli import load_json
from records.contracts import Fault,boundary,encoded,fields,require,text
from records.migrations import inspect_recovery

from .analysis import Analyzer
from .coverage import Coverage
from .reader import Reader
from .runner import Runner

ACTIONS={'registerSource','reserveSearch','submitDiscovery','readCandidate','submitAnalysis',
         'publish','reviewCoverage','cancel'}


def unwrap(result):
    if not result['ok']:
        error=dict(result['error'])
        raise Fault(error.pop('code'),error.pop('message'),**error)
    return result['value']


def exact(request,allowed,required=None):
    fields(request,{'action'}|set(allowed),{'action'}|set(required if required is not None else allowed))


@boundary
def execute(args):
    if args.command=='run':
        request=load_json(args.input)
        fields(request,{'runId','ownerId','sourceIds','queries','limits'},
               {'runId','ownerId','sourceIds','queries'})
        runner=Runner(args.db)
        return unwrap(runner.start(request['runId'],request['ownerId'],request['sourceIds'],
                                   request['queries'],request.get('limits')))
    if args.command=='resume':
        request=load_json(args.input)
        fields(request,{'runId','ownerId'},{'runId','ownerId'})
        runner=Runner(args.db)
        return unwrap(runner.resume(request['runId'],request['ownerId']))
    if args.command=='inspect':
        require(text(args.run_id))
        runner=Runner(args.db)
        if args.view=='state':
            return dict(run=unwrap(runner.store.inspect_run(args.run_id,args.cursor,args.limit)),
                        execution=unwrap(runner.store.execution.inspect(args.run_id,args.cursor,args.limit)))
        if args.view=='recovery':
            return unwrap(inspect_recovery(args.db))
        bridge=runner.bridge(args.run_id,None)
        result=bridge.inspect_searches(args.cursor,args.limit) if args.view=='searches' else bridge.inspect(args.cursor,args.limit)
        return unwrap(result)
    request=load_json(args.input)
    action=request.get('action')
    require(isinstance(action,str),'Action required')
    if action not in ACTIONS:
        raise Fault('SCOPE_VIOLATION','Action unavailable in research CLI')
    return dispatch(Runner(args.db),request)


def dispatch(runner,request):
    action=request.get('action')
    require(isinstance(action,str),'Action required')
    common={'runId','token'}
    if action=='registerSource':
        exact(request,common|{'source','operationId'})
        return unwrap(runner.bridge(request['runId'],request['token']).register_source(
            request['source'],request['operationId']))
    if action=='reserveSearch':
        exact(request,common|{'callId','query','tool'},common|{'callId','query'})
        return unwrap(runner.bridge(request['runId'],request['token']).request(
            request['callId'],request['query'],tool=request.get('tool')))
    if action=='submitDiscovery':
        exact(request,common|{'callId','result'})
        return unwrap(runner.bridge(request['runId'],request['token']).submit(
            request['callId'],request['result']))
    if action=='readCandidate':
        exact(request,common|{'sourceId','url','candidateId','auxiliary'},
              common|{'sourceId','url','candidateId'})
        return unwrap(Reader(runner.store,request['runId'],request['token']).read(
            request['sourceId'],request['url'],request['candidateId'],
            auxiliary=request.get('auxiliary',False)))
    if action=='submitAnalysis':
        exact(request,common|{'draft'})
        return unwrap(Analyzer(runner.store,request['runId'],request['token']).validate(request['draft']))
    if action=='publish':
        exact(request,common|{'phase','validated','locator','manifestId','maxSteps'},common|{'phase'})
        publication=runner.publication(request['runId'],request['token'])
        if request['phase']=='prepare':
            require(request.keys()=={'action','runId','token','phase','validated','locator'},
                    'Prepare requires validated analysis and locator')
            return unwrap(publication.prepare(request['validated'],request['locator']))
        require(request['phase']=='resume','Unknown publication phase')
        require(request.keys()<={'action','runId','token','phase','manifestId','maxSteps'} and
                'manifestId' in request,'Resume requires manifestId')
        return unwrap(publication.resume(request['manifestId'],request.get('maxSteps')))
    if action=='reviewCoverage':
        exact(request,common|{'draft'})
        return unwrap(Coverage(runner.store,request['runId'],request['token']).publish(request['draft']))
    if action=='cancel':
        exact(request,common)
        return unwrap(runner.store.execution.cancel(request['runId'],request['token']))
    raise Fault('SCOPE_VIOLATION','Action unavailable in research CLI')


class Parser(argparse.ArgumentParser):
    def error(self,message):
        raise Fault('VALIDATION_ERROR','Invalid command arguments; see --help')


def main(argv=None):
    parser=Parser(description='Bounded local Agent research; search tools remain an explicit handoff.')
    parser.add_argument('--db',default='.local/records.sqlite3')
    sub=parser.add_subparsers(dest='command',required=True)
    for command in ('run','resume','request'):
        sub.add_parser(command).add_argument('--input',required=True)
    inspect=sub.add_parser('inspect')
    inspect.add_argument('--run-id',required=True)
    inspect.add_argument('--view',choices=('state','candidates','searches','recovery'),default='state')
    inspect.add_argument('--cursor',default='')
    inspect.add_argument('--limit',type=int,default=20)
    try:
        result=execute(parser.parse_args(argv))
    except Fault as exc:
        result={'ok':False,'error':exc.error}
    print(encoded(result))
    return 0 if result['ok'] else 2
