import json
from contextlib import closing
from test_source import StoreCase, source
from records.exchange import Exchange, digest, snapshot
from records.service import ResearchStore


class BundleVersionTests(StoreCase):
    def old_bundle(self):
        self.value(self.store.create_research(source(), 'create'))
        with closing(self.store.db.connect()) as conn:
            bundle = dict(schemaVersion=1, baseBundleId=None, data=snapshot(conn))
        bundle['bundleId'] = digest(bundle)
        return bundle

    def test_v1_import_converts_with_preserved_history_and_stable_v2_bytes(self):
        old = self.old_bundle()
        other = self.path.parent / 'other.sqlite3'
        exchange = Exchange(other)
        self.value(exchange.import_research(old, 'old-import'))
        target = self.path.parent / 'bundle.json'
        target.write_text(json.dumps(old))
        self.value(exchange.export_research(target))
        new = json.loads(target.read_text())
        self.assertEqual(new['schemaVersion'], 2)
        self.assertEqual(new['baseBundleId'], old['bundleId'])
        self.assertEqual(new['data'], old['data'])
        before = target.read_bytes()
        self.value(exchange.export_research(target))
        self.assertEqual(target.read_bytes(), before)
        rebuilt = Exchange(self.path.parent / 'rebuilt.sqlite3')
        self.value(rebuilt.import_research(new, 'new-import'))
        again = self.path.parent / 'again.json'
        self.value(rebuilt.export_research(again))
        self.assertEqual(again.read_bytes(), before)

    def test_pre_upgrade_checkpoint_without_format_preserves_baseline(self):
        old = self.old_bundle()
        with closing(self.store.db.connect()) as conn:
            value = dict(bundleId=old['bundleId'], baseBundleId=None, contentHash=digest(old['data']))
            conn.execute("INSERT INTO metadata VALUES ('checkpoint', ?)", (json.dumps(value),))
        path = self.path.parent / 'old.json'
        path.write_text(json.dumps(old))
        self.value(Exchange(self.path).export_research(path))
        self.assertEqual(json.loads(path.read_text())['baseBundleId'], old['bundleId'])

    def test_invalid_old_bundle_or_external_changes_are_not_accepted(self):
        old = self.old_bundle()
        exchange = Exchange(self.path.parent / 'receiver.sqlite3')
        bad = dict(old, schemaVersion=99)
        bad['bundleId'] = digest({k:v for k,v in bad.items() if k != 'bundleId'})
        self.assertFalse(exchange.import_research(bad, 'bad')['ok'])
        self.value(exchange.import_research(old, 'old'))
        external = dict(old, baseBundleId='a' * 64)
        external['bundleId'] = digest({k:v for k,v in external.items() if k != 'bundleId'})
        path = self.path.parent / 'external.json'
        path.write_text(json.dumps(external))
        before = path.read_bytes()
        self.assertFalse(exchange.export_research(path)['ok'])
        self.assertEqual(before, path.read_bytes())

    def test_first_v2_descendant_and_fork_checks(self):
        old = self.old_bundle()
        writer = Exchange(self.path)
        self.value(writer.import_research(old, 'baseline'))
        receiver = Exchange(self.path.parent / 'receiver.sqlite3')
        self.value(receiver.import_research(old, 'baseline'))
        self.value(self.store.create_research(source('NEW'), 'new'))
        path = self.path.parent / 'v2.json'
        self.value(writer.export_research(path))
        new = json.loads(path.read_text())
        self.assertEqual(new['baseBundleId'], old['bundleId'])
        self.value(receiver.import_research(new, 'advance'))
        fork = dict(new, baseBundleId=old['bundleId'])
        self.value(ResearchStore(receiver.db.path).create_research(source('LOCAL'), 'local'))
        self.assertFalse(receiver.import_research(fork, 'fork')['ok'])
