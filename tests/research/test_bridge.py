import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from research.runner import Runner


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'db.sqlite3';self.time=1000
        self.runner=Runner(self.path,clock=lambda:self.time)
        self.token=self.ok(self.runner.start('run','owner',[],['AI education']))['token']
        self.bridge=self.runner.bridge('run',self.token)
        self.source=dict(id='S',kind='Source',name='Forum',url='https://example.com',audience=['teachers'],languages=['en'],accessStatus='untried',lastAttempt=None,lastSuccess=None)
        self.result=dict(status='completed',reason=None,discoveries=[dict(sourceId='S',url='https://example.com/topic/1',title='Need help',snippet='Search snippet only')])

    def ok(self,result):
        self.assertTrue(result['ok'],result)
        return result['value']

    def request(self,call='search-1'):
        return self.ok(self.bridge.request(call,'AI education',tool='web.search'))

    def test_source_first_queue_replay_and_search_is_not_receipt(self):
        grant=self.request();self.assertEqual(grant['status'],'awaiting_agent')
        self.assertFalse(self.bridge.submit('search-1',self.result)['ok'])
        self.assertEqual(self.ok(self.bridge.inspect())['items'],[])
        self.ok(self.bridge.register_source(self.source,'source-1'))
        first=self.ok(self.bridge.submit('search-1',self.result))
        self.assertEqual(first,self.ok(self.bridge.submit('search-1',self.result)))
        self.assertEqual(self.request()['status'],'completed')
        items=self.ok(self.bridge.inspect())['items'];self.assertEqual(len(items),1)
        self.assertEqual(items[0]['status'],'discovered')
        self.assertEqual(items[0]['sourceId'],'S')
        with closing(self.runner.store.db.connect()) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM research_records WHERE kind='ResearchArtifact'").fetchone()[0],0)
        changed=dict(self.result,reason='Changed')
        self.assertFalse(self.bridge.submit('search-1',changed)['ok'])
        self.assertEqual(self.ok(self.runner.store.execution.inspect('run'))['used']['searches'],1)

    def test_unavailable_tool_does_not_spend_budget(self):
        result=self.ok(self.bridge.request('no-tool','AI education',tool=None))
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(self.ok(self.runner.store.execution.inspect('run'))['used']['total'],0)

    def test_expired_cancelled_and_old_owner_cannot_submit(self):
        self.ok(self.bridge.register_source(self.source,'source-1'));self.request()
        self.time+=31
        self.assertEqual(self.bridge.submit('search-1',self.result)['error']['code'],'CALL_EXPIRED')
        self.time+=60;self.ok(self.runner.resume('run','new-owner'))
        self.assertEqual(self.bridge.submit('search-1',self.result)['error']['code'],'LEASE_EXPIRED')
        self.assertEqual(self.ok(self.bridge.inspect())['items'],[])
        self.assertEqual(self.bridge.register_source(dict(self.source,id='S2'),'source-2')['error']['code'],'LEASE_EXPIRED')

    def test_strict_input_and_query_binding(self):
        self.request()
        self.assertEqual(self.bridge.request('search-1','Another query',tool='web.search')['error']['code'],'IDEMPOTENCY_CONFLICT')
        self.ok(self.bridge.register_source(self.source,'source-1'))
        for extra in ('receipt','body','favorite'):
            self.assertFalse(self.bridge.submit('search-1',dict(self.result,**{extra:'not permitted'}))['ok'])
        self.ok(self.runner.store.execution.cancel('run',self.token))
        self.assertFalse(self.bridge.submit('search-1',self.result)['ok'])

    def test_paging_duplicates_restart_and_backup(self):
        self.ok(self.bridge.register_source(self.source,'source-1'));self.request()
        results=[dict(self.result['discoveries'][0],url=f'https://example.com/topic/{n}') for n in range(3)]
        self.ok(self.bridge.submit('search-1',dict(self.result,discoveries=results)))
        self.request('search-2');self.ok(self.bridge.submit('search-2',self.result))
        page=self.ok(self.bridge.inspect(limit=2));self.assertEqual(len(page['items']),2)
        rest=self.ok(self.bridge.inspect(cursor=page['nextCursor'],limit=2));self.assertEqual(len(rest['items']),1)
        from records.exchange import Exchange
        export=self.path.parent/'public.json'
        self.ok(Exchange(self.path).export_research(export))
        self.assertNotIn('Search snippet only',export.read_text())
        self.assertNotIn('search-1',export.read_text())
        from records.backup import backup_local,restore_local
        from research.bridge import AgentBridge
        self.ok(backup_local(self.path,self.path.parent/'backup.sqlite3'))
        restored=self.path.parent/'restored.sqlite3';self.ok(restore_local(self.path.parent/'backup.sqlite3',restored))
        runner=Runner(restored,clock=lambda:self.time);token=self.ok(runner.resume('run','restored'))['token']
        bridge=AgentBridge(runner.store,'run',token)
        self.assertEqual(len(self.ok(bridge.inspect())['items']),3)
        self.assertEqual(len(self.ok(bridge.inspect_searches())['items']),2)

    def test_whole_submission_rolls_back_and_failure_consumes_one_call(self):
        self.ok(self.bridge.register_source(self.source,'source-1'));self.request()
        bad=dict(self.result,discoveries=self.result['discoveries']+[dict(self.result['discoveries'][0],sourceId='MISSING')])
        self.assertFalse(self.bridge.submit('search-1',bad)['ok'])
        self.assertEqual(self.ok(self.bridge.inspect())['items'],[])
        self.assertEqual(self.ok(self.runner.store.execution.inspect('run'))['calls'][0]['status'],'reserved')
        failure=dict(status='failed',reason='Search tool timed out',discoveries=[])
        self.ok(self.bridge.submit('search-1',failure))
        self.assertEqual(self.ok(self.bridge.inspect_searches())['items'][0]['result'],failure)
        self.assertEqual(self.ok(self.runner.store.execution.inspect('run'))['used']['total'],1)
        self.assertFalse(self.bridge.submit('search-1',self.result)['ok'])
