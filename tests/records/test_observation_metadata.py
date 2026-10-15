import json
from test_source import StoreCase, source
from test_evidence import evidence
from records.exchange import Exchange, digest
from records.backup import backup_local


def profile():
    return dict(domain='example.com', subentries=['https://example.com/forum'],
                industries=['教育'], sourceType='community', accessBoundary='仅公开正文',
                recheckReason='补近期案例')


def observation(precision='date'):
    return dict(receiptId='READ-ONE', blockIds=['body-1'], replyIds=[], independence=[],
                precision=precision, dateBasis=None if precision == 'unknown' else '原帖日期标注',
                paymentVerification=None)


class ObservationTests(StoreCase):
    def test_profile_and_day_precision_survive_export_import_and_backup(self):
        self.value(self.store.create_research(source() | {'profile': profile()}, 'source'))
        original = self.value(self.store.create_research(evidence() | {
            'publishedDate':'2026-10-16', 'observation':observation()}, 'evidence'))
        self.assertIsNone(original['publishedAt'])
        path = self.path.parent / 'public.json'
        self.value(Exchange(self.path).export_research(path))
        bundle = json.loads(path.read_text())
        other = Exchange(self.path.parent / 'other.sqlite3')
        self.value(other.import_research(bundle, 'import'))
        self.value(backup_local(self.path, self.path.parent / 'backup.sqlite3'))
        from records.service import ResearchStore
        self.assertEqual(self.value(ResearchStore(other.db.path).read_record('EV-TEST'))['record'], original)
        self.assertEqual(original['observation']['precision'], 'date')

    def test_unknown_and_exact_dates_do_not_gain_synthetic_precision(self):
        self.value(self.store.create_research(source(), 'source'))
        for precision, instant in [('unknown',None), ('instant','2026-10-16T02:03:04+08:00')]:
            record = evidence(precision) | {'publishedAt':instant, 'observation':observation(precision)}
            saved = self.value(self.store.create_research(record, precision))
            self.assertNotIn('publishedDate', saved)
            self.assertEqual(saved['publishedAt'], instant)

    def test_nested_fields_and_inconsistent_precision_are_rejected(self):
        for patch in ({'notes':'private'}, {'domain':'internal.test'}, {'sourceType':'buyer'},
                      {'subentries':['not-url']}):
            self.assertFalse(self.store.create_research(source() | {'profile':profile() | patch}, 'bad')['ok'])
        self.value(self.store.create_research(source(), 'source'))
        valid = evidence() | {'publishedDate':'2026-10-16', 'observation':observation()}
        for patch in ({'publishedDate':'2026-02-30'}, {'publishedAt':'2026-10-16T00:00:00Z'},
                      {'observation':observation() | {'notes':'private'}},
                      {'observation':observation() | {'blockIds':[]}},
                      {'observation':observation('unknown')},
                      {'observation':observation() | {'dateBasis':None}}):
            self.assertFalse(self.store.create_research(valid | patch, 'bad')['ok'])
        self.assertFalse(self.store.create_research(evidence() | {'publishedDate':'2026-10-16'}, 'bad')['ok'])

    def test_new_metadata_cannot_be_smuggled_in_a_v1_envelope(self):
        self.value(self.store.create_research(source() | {'profile':profile()}, 's'))
        target = self.path.parent / 'v2.json'
        self.value(Exchange(self.path).export_research(target))
        bundle = json.loads(target.read_text())
        bundle['schemaVersion'] = 1
        bundle['bundleId'] = digest({k:v for k,v in bundle.items() if k != 'bundleId'})
        self.assertFalse(Exchange(self.path.parent / 'other.sqlite3').import_research(bundle, 'bad')['ok'])

    def test_invalid_url_with_profile_returns_structured_error(self):
        result = self.store.create_research(source() | {'url':'https://[bad', 'profile':profile()}, 'bad-url')
        self.assertFalse(result['ok'])
