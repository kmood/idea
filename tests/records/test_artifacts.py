"""Synthetic artifact graphs exercise storage and import trust boundaries."""
import json
from test_source import StoreCase, source
from records.exchange import Exchange, digest


def checkpoint():
    return dict(id='CHECK-1', kind='ResearchArtifact', artifactType='SourceCheckpoint',
                data=dict(sourceId='CN-TEST', order='unordered', discovered=None, completed=None,
                          gaps=['unread'], processed=[], overlapStrategy='revisit latest page', lastReceipt=None))


def receipt():
    return dict(id='READ-1', kind='ResearchArtifact', artifactType='ReadReceipt', data=dict(
        runId='RUN-1', sourceId='CN-TEST', originalUrl='https://example.com/thread',
        finalUrl='https://example.com/thread', fetchedAt='2026-10-19T00:00:00Z', status='readable',
        executor='public-reader', visibleScope='article body', truncated=False, fingerprint='a'*64,
        blocks=[dict(blockId='b1', summary='Synthetic visible excerpt')],
        publishedAt=None, publishedDate=None, precision='unknown', dateBasis=None, error=None))


class ArtifactTests(StoreCase):
    def test_checkpoint_history_roundtrip_and_no_private_fields(self):
        self.value(self.store.create_research(source(), 'source'))
        saved = self.value(self.store.create_research(checkpoint(), 'checkpoint'))
        new_data = dict(saved['data'], processed=['thread-1'])
        self.value(self.store.patch_research('CHECK-1', 1, {'data':new_data}, 'Read another thread', 'advance'))
        self.assertEqual(self.value(self.store.read_record('CHECK-1', 1))['record'], saved)
        path = self.path.parent / 'bundle.json'
        self.value(Exchange(self.path).export_research(path))
        bundle = json.loads(path.read_text())
        other = Exchange(self.path.parent / 'other.sqlite3')
        self.value(other.import_research(bundle, 'import'))
        self.value(other.export_research(self.path.parent / 'again.json'))
        self.assertEqual(path.read_bytes(), (self.path.parent / 'again.json').read_bytes())
        self.assertFalse(self.store.patch_research('CHECK-1', 2, {'data':new_data | {'notes':'PRIVATE'}}, 'bad', 'bad')['ok'])

    def test_bad_reference_rejects_creation_and_whole_import(self):
        self.assertFalse(self.store.create_research(checkpoint(), 'missing')['ok'])
        self.value(self.store.create_research(source(), 's'))
        self.value(self.store.create_research(checkpoint(), 'c'))
        path = self.path.parent / 'bundle.json'
        self.value(Exchange(self.path).export_research(path))
        bundle = json.loads(path.read_text())
        for record in bundle['data']['records'] + bundle['data']['versions']:
            if record['kind'] == 'ResearchArtifact':
                record['data']['sourceId'] = 'MISSING'
        for operation in bundle['data']['operations']:
            if operation['result']['kind'] == 'ResearchArtifact':
                operation['result']['data']['sourceId'] = 'MISSING'
        bundle['bundleId'] = digest({k:v for k,v in bundle.items() if k != 'bundleId'})
        other = Exchange(self.path.parent / 'other.sqlite3')
        self.assertFalse(other.import_research(bundle, 'bad')['ok'])
        self.assertEqual(self.value(other.status())['researchRecords'], 0)

    def test_ordinary_create_cannot_mint_read_receipt(self):
        self.value(self.store.create_research(source(), 's'))
        result = self.store.create_research(receipt(), 'forged')
        self.assertFalse(result['ok'])
        self.assertEqual(result['error']['message'], 'Only Reader may publish reading receipts')
        self.assertEqual(self.store.read_record('READ-1')['error']['code'], 'NOT_FOUND')

    def test_manifest_target_ids_are_future_identities_but_results_are_real(self):
        self.value(self.store.create_research(source(), 's'))
        step = dict(stepId='create', targetId='FUTURE', operationId='future-op', requestHash='b'*64,
                    expectedRevision=None, dependsOn=[], result=None)
        manifest = dict(id='MAN-1',kind='ResearchArtifact',artifactType='PublicationManifest',
                        data=dict(runId='RUN-1',candidateId='C1',sourceId='CN-TEST',steps=[step],supersedes=None))
        self.value(self.store.create_research(manifest, 'manifest'))
        bad = dict(manifest['data'], steps=[step | {'result':dict(recordId='FUTURE',revision=1)}])
        self.assertFalse(self.store.patch_research('MAN-1',1,{'data':bad},'false success','bad')['ok'])
        bad = dict(manifest['data'], steps=[step | {'dependsOn':['create']}])
        self.assertFalse(self.store.patch_research('MAN-1',1,{'data':bad},'cycle','cycle')['ok'])

    def test_disposition_and_coverage_have_fixed_shapes(self):
        self.value(self.store.create_research(source(), 's'))
        outcome = dict(id='OUT-1',kind='ResearchArtifact',artifactType='CandidateOutcome',data=dict(
            runId='RUN-1',candidateId='C1',sourceId='CN-TEST',locator='https://example.com/thread',
            status='deferred',reason='Not read',nextCondition='Retry later',recordRefs=[]))
        self.value(self.store.create_research(outcome, 'outcome'))
        coverage = dict(id='COV-1',kind='ResearchArtifact',artifactType='CoverageReview',data=dict(
            runIds=['RUN-1'],sourceRefs=[dict(recordId='CN-TEST',revision=1)],evidenceRefs=[],
            gaps=['education'],qualityReasons=['Only one community covered'],recommendation='concentrate',reason='Broaden sources'))
        self.value(self.store.create_research(coverage, 'coverage'))
        for patch in ({'artifactType':'Unknown'}, {'data':{'arbitrary':'text'}}):
            self.assertFalse(self.store.create_research(coverage | {'id':'BAD'} | patch, 'bad')['ok'])

    def test_reader_capability_and_receipt_history_survive_restore(self):
        from records.artifacts import _READER_AUTHORITY
        from records.contracts import now, validate_record
        from records.storage import references, save
        from records.backup import backup_local, restore_local
        from records.service import ResearchStore
        self.value(self.store.create_research(source(), 's'))
        record = receipt() | dict(schemaVersion=1, revision=1, createdAt=now(), updatedAt=now(), archived=False, mergedInto=None)
        validate_record(record)
        def publish(conn):
            references(conn, record)
            return save(conn, record, None, 'reader', 'created', 'Synthetic Reader test', authority=_READER_AUTHORITY)
        self.store.db.run('research','reader',{'fixture':'receipt'},publish)
        self.assertFalse(self.store.patch_research('READ-1',1,{'data':record['data'] | {'visibleScope':'Invented comments'}},'forged','bad')['ok'])
        self.assertFalse(self.store.patch_research('READ-1',1,{'artifactType':'SourceCheckpoint','data':checkpoint()['data']},'change type','type')['ok'])
        path = self.path.parent / 'receipt.json'
        self.value(Exchange(self.path).export_research(path))
        self.value(Exchange(self.path.parent / 'import.sqlite3').import_research(json.loads(path.read_text()), 'receipt-import'))
        backup = self.path.parent / 'backup.sqlite3'
        restored = self.path.parent / 'restored.sqlite3'
        self.value(backup_local(self.path, backup)); self.value(restore_local(backup,restored))
        self.assertEqual(self.value(ResearchStore(restored).read_record('READ-1'))['record'], record)

    def test_receipt_invalid_nested_data_is_rejected(self):
        self.value(self.store.create_research(source(), 's'))
        for patch in ({'blocks':[{'blockId':'b1','summary':'x','notes':'PRIVATE'}]},
                      {'truncated':True}, {'precision':'date'}, {'fingerprint':'bad'}):
            result = self.store.create_research(receipt() | {'data':receipt()['data'] | patch}, 'bad')
            self.assertFalse(result['ok'])
            self.assertNotEqual(result['error']['message'], 'Only Reader may publish reading receipts')
