import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ResearchCliTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.db=self.root/'research.sqlite3';self.index=0

    def cli(self,*args,success=True):
        result=subprocess.run([sys.executable,'-m','research','--db',str(self.db),*args],
                              capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0 if success else 2,result.stderr+result.stdout)
        return json.loads(result.stdout)

    def input(self,value):
        self.index+=1;path=self.root/f'input-{self.index}.json'
        path.write_text(json.dumps(value),encoding='utf-8');return path

    def request(self,value,success=True):
        return self.cli('request','--input',str(self.input(value)),success=success)

    def test_real_process_search_handoff_resume_and_inspection(self):
        started=self.cli('run','--input',str(self.input(dict(
            runId='run',ownerId='agent',sourceIds=[],queries=['AI workflow']))))['value']
        token=started['token']
        source=dict(id='S',kind='Source',name='Forum',url='https://example.com',
                    audience=['builders'],languages=['en'],accessStatus='untried',
                    lastAttempt=None,lastSuccess=None)
        self.request(dict(action='registerSource',runId='run',token=token,
                          source=source,operationId='source'))
        awaiting=self.request(dict(action='reserveSearch',runId='run',token=token,
                                   callId='search-1',query='AI workflow',tool='web.search'))['value']
        self.assertEqual(awaiting['status'],'awaiting_agent')
        discovery=dict(status='completed',reason=None,discoveries=[dict(
            sourceId='S',url='https://example.com/thread',title='Need automation',
            snippet='Search result only')])
        self.request(dict(action='submitDiscovery',runId='run',token=token,
                          callId='search-1',result=discovery))
        candidates=self.cli('inspect','--run-id','run','--view','candidates')['value']
        self.assertEqual(candidates['items'][0]['sourceId'],'S')
        resumed=self.cli('resume','--input',str(self.input(dict(
            runId='run',ownerId='agent'))))['value']
        self.assertEqual(resumed['state']['used']['searches'],1)

    def test_help_and_structured_errors_do_not_echo_input(self):
        help_result=subprocess.run([sys.executable,'-m','research','--help'],
                                   capture_output=True,text=True,timeout=10)
        self.assertEqual(help_result.returncode,0,help_result.stderr)
        for command in ('run','resume','request','inspect'):
            self.assertIn(command,help_result.stdout)
        sentinel='PRIVATE-SENTINEL'
        rejected=self.request(dict(action='unknown',payload=sentinel),success=False)
        self.assertEqual(rejected['error']['code'],'SCOPE_VIOLATION')
        self.assertNotIn(sentinel,json.dumps(rejected))
        self.assertFalse(self.db.exists())
        malformed=self.root/'malformed.json';malformed.write_text('{'+sentinel,encoding='utf-8')
        rejected=self.cli('request','--input',str(malformed),success=False)
        self.assertEqual(rejected['error']['code'],'VALIDATION_ERROR')
        self.assertNotIn(sentinel,json.dumps(rejected))
        self.assertFalse(self.db.exists())


if __name__=='__main__':unittest.main()
