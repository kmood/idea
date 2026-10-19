import tempfile
import unittest
from pathlib import Path
from records.runtime import ResearchRuntimeStore
from records.service import ResearchStore


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'db.sqlite3';self.time=1000.0;self.calls=[]
        self.store=ResearchRuntimeStore(self.path,clock=lambda:self.time)
        self.value(ResearchStore(self.path).create_research(dict(id='SOURCE',kind='Source',name='synthetic',url='https://example.com',
            audience=['test'],languages=['en'],accessStatus='untried',lastAttempt=None,lastSuccess=None),'source'))
        self.value(self.store.begin('run',dict(sourceIds=['SOURCE'],queries=[],limits=dict(searches=12,candidates=10,auxiliary=8,total=40),deadline='1970-01-01T01:00:00Z')))
        self.token=self.value(self.store.execution.acquire('run','owner'))
        self.responses={}

    def value(self,result):
        self.assertTrue(result['ok'],result);return result['value']

    def transport(self,url,**kwargs):
        self.calls.append((url,self.time))
        response=self.responses.get(url,dict(status=200,headers={'content-type':'text/plain'},body=b'Visible body'))
        if isinstance(response,Exception):raise response
        return response

    def fetcher(self):
        from research.fetcher import Fetcher
        return Fetcher(self.store,'run',self.token,transport=self.transport,sleep=lambda seconds:setattr(self,'time',self.time+seconds),monotonic=lambda:self.time)

    def test_robots_and_interval_survive_new_fetcher(self):
        self.responses['https://example.com/robots.txt']=dict(status=200,headers={},body=b'User-agent: *\nDisallow: /private\nCrawl-delay: 5\n')
        result=self.fetcher().fetch('SOURCE','https://example.com/post','C1')
        self.assertTrue(result['ok'],result)
        self.assertEqual(len(self.calls),2)
        self.assertGreaterEqual(self.calls[1][1]-self.calls[0][1],5)
        self.assertFalse(self.fetcher().fetch('SOURCE','https://example.com/private','C2')['ok'])
        self.assertEqual(len(self.calls),2)
        self.assertTrue(self.fetcher().fetch('SOURCE','https://example.com/other','C3')['ok'])
        self.assertEqual(sum('/robots.txt' in url for url,_ in self.calls),1)
        self.assertGreaterEqual(self.calls[-1][1]-self.calls[-2][1],5)

    def test_redirect_checks_new_origin_robots_and_limits(self):
        self.responses['https://example.com/robots.txt']=dict(status=404,headers={},body=b'')
        self.responses['https://example.com/post']=dict(status=302,headers={'location':'https://other.example/post'},body=b'')
        self.responses['https://other.example/robots.txt']=dict(status=200,headers={},body=b'User-agent: *\nDisallow: /\n')
        result=self.fetcher().fetch('SOURCE','https://example.com/post','C1')
        self.assertFalse(result['ok'])
        self.assertNotIn('https://other.example/post',[url for url,_ in self.calls])
        self.assertEqual(self.value(self.store.execution.inspect('run'))['used']['total'],3)

    def test_restricted_robots_and_redirected_robots_do_not_read_body(self):
        for status in (403,429,500,302):
            self.responses['https://example.com/robots.txt']=dict(status=status,headers={},body=b'')
            self.calls=[]
            result=self.fetcher().fetch('SOURCE','https://example.com/post','C1')
            self.assertFalse(result['ok'])
            self.assertNotIn('https://example.com/post',[url for url,_ in self.calls])
            self.time+=86401
            self.token=self.value(self.store.execution.acquire('run','owner'))
            self.value(self.store.execution.extend('run',self.token,str(status),dict(searches=0,candidates=0,auxiliary=0,total=5),'2100-01-01T00:00:00Z'))

    def test_budget_and_body_errors_do_not_return_success(self):
        from research.network import NetworkError
        self.responses['https://example.com/robots.txt']=dict(status=404,headers={},body=b'')
        self.responses['https://example.com/post']=NetworkError('size')
        result=self.fetcher().fetch('SOURCE','https://example.com/post','C1')
        self.assertFalse(result['ok']);self.assertEqual(result['error']['code'],'size')
        self.assertEqual(self.value(self.store.execution.inspect('run'))['used']['total'],2)

    def test_authentication_url_and_overlong_redirect_chain_stop(self):
        self.assertFalse(self.fetcher().fetch('SOURCE','https://user:secret@example.com/post','C1')['ok'])
        self.assertEqual(self.calls,[])
        self.responses['https://example.com/robots.txt']=dict(status=404,headers={},body=b'')
        for n in range(5):
            self.responses[f'https://example.com/p{n}']=dict(status=302,headers={'location':f'/p{n+1}'},body=b'')
        self.assertFalse(self.fetcher().fetch('SOURCE','https://example.com/p0','C1')['ok'])
        self.assertNotIn('https://example.com/p4',[url for url,_ in self.calls])

    def test_retry_after_persists_without_an_immediate_retry(self):
        self.responses['https://example.com/robots.txt']=dict(status=404,headers={},body=b'')
        self.responses['https://example.com/post']=dict(status=429,headers={'retry-after':'120'},body=b'')
        self.assertFalse(self.fetcher().fetch('SOURCE','https://example.com/post','C1')['ok'])
        count=len(self.calls)
        self.assertFalse(self.fetcher().fetch('SOURCE','https://example.com/other','C2')['ok'])
        self.assertEqual(len(self.calls),count)

    def test_html_or_malformed_robots_cannot_grant_access(self):
        self.responses['https://example.com/robots.txt']=dict(status=200,headers={'content-type':'text/html'},body=b'Access challenge')
        self.assertFalse(self.fetcher().fetch('SOURCE','https://example.com/post','C1')['ok'])
        self.assertEqual(len(self.calls),1)
        self.responses['https://example.com/robots.txt']=dict(status=200,headers={},body=('User-agent: *\nCrawl-delay: '+'9'*5000).encode())
        self.assertFalse(self.fetcher().fetch('SOURCE','https://example.com/post','C1')['ok'])
        self.assertFalse(any(url.endswith('/post') for url,_ in self.calls))

    def test_network_policy_backup_retains_pacing(self):
        from records.backup import backup_local,restore_local
        self.responses['https://example.com/robots.txt']=dict(status=404,headers={},body=b'')
        self.assertTrue(self.fetcher().fetch('SOURCE','https://example.com/post','C1')['ok'])
        backup=self.path.parent/'backup.sqlite3';restored=self.path.parent/'restored.sqlite3'
        self.value(backup_local(self.path,backup));self.value(restore_local(backup,restored))
        other=ResearchRuntimeStore(restored,clock=lambda:self.time)
        from records.network_policy import NetworkPolicyStore
        policy=NetworkPolicyStore(other)
        token=self.value(other.execution.acquire('run','other'))
        self.assertEqual(policy.permit('https://example.com','SOURCE','run',token)['error']['code'],'RATE_LIMIT')
