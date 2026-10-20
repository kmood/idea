import tempfile
import unittest
from pathlib import Path
from records.runtime import ResearchRuntimeStore
from records.service import ResearchStore


class ReaderTests(unittest.TestCase):
    def test_html_is_visible_text_with_precise_date_and_no_execution(self):
        from research.reader import parse_document
        html=(Path(__file__).parents[1]/'fixtures/research/public-thread.html').read_bytes()
        parsed=parse_document(html,'text/html; charset=utf-8')
        text=' '.join(block['text'] for block in parsed['blocks'])
        self.assertIn('checking terminology',text)
        self.assertIn('Ignore earlier instructions',text)
        for unwanted in ('Navigation text','Never execute','hidden text','Footer text'):
            self.assertNotIn(unwanted,text)
        self.assertEqual(parsed['publishedDate'],'2026-10-19')
        self.assertIsNone(parsed['publishedAt'])
        self.assertEqual(parsed['precision'],'date')

    def test_titles_login_and_unsupported_content_do_not_become_receipts_of_reading(self):
        from research.reader import parse_document
        from research.network import NetworkError
        for body,kind in [(b'<title>A title only</title>','text/html'),
                          (b'<article><h1>Only a heading</h1></article>','text/html'),
                          (b'<form><input type="password"></form>','text/html'),
                          (b'%PDF content','application/pdf')]:
            with self.subTest(body=body),self.assertRaises(NetworkError):parse_document(body,kind)

    def test_conflicting_dates_and_invisible_content_are_not_invented(self):
        from research.reader import parse_document
        document=b'<article><time datetime="2026-10-18"></time><time datetime="2026-10-19"></time><p aria-hidden>Visible discussion.</p><p style="display:none">hidden</p></article>'
        parsed=parse_document(document,'text/html')
        self.assertEqual(parsed['precision'],'unknown')
        self.assertIsNone(parsed['publishedDate'])
        self.assertNotIn('hidden',str(parsed['blocks']))

    def test_v2ex_discussion_bodies_are_scoped_without_navigation_cells(self):
        from research.reader import parse_document
        document=('''<html><title>Discussion</title><body><div class="cell">Navigation noise</div>
            <div class="topic_content"><p>Hundreds of clips require manual timing.</p></div>
            <div class="reply_content">Use subtitle timestamps to align each clip.</div></body></html>''').encode()
        parsed=parse_document(document,'text/html; charset=utf-8')
        text=' '.join(block['text'] for block in parsed['blocks'])
        self.assertIn('Hundreds of clips',text)
        self.assertIn('subtitle timestamps',text)
        self.assertNotIn('Navigation noise',text)

    def test_reader_persists_receipt_replays_and_rebuilds_missing_cache(self):
        from research.reader import Reader
        from records.exchange import Exchange
        import json
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'db.sqlite3';store=ResearchRuntimeStore(path)
            source=dict(id='S',kind='Source',name='synthetic',url='https://example.com',audience=['test'],languages=['en'],accessStatus='untried',lastAttempt=None,lastSuccess=None)
            self.assertTrue(ResearchStore(path).create_research(source,'source')['ok'])
            from research.runner import Runner
            run=Runner(path).start('run','owner',['S'],[])['value']
            class Fetch:
                def fetch(self,*args,**kwargs):
                    return dict(ok=True,value=dict(originalUrl='https://example.com/thread',finalUrl='https://example.com/thread',
                        status=200,headers={'content-type':'text/plain'},body=b'Visible user need for consistent terminology.'))
            reader=Reader(store,'run',run['token'],fetcher=Fetch())
            first=reader.read('S','https://example.com/thread','candidate')
            self.assertTrue(first['ok'],first)
            receipt_id=first['value']['receipt']['id']
            cached=reader.cached(receipt_id)
            self.assertTrue(cached['ok'],cached)
            self.assertIn('Visible user need',cached['value']['blocks'][0]['text'])
            repeat=reader.read('S','https://example.com/thread','candidate')
            self.assertTrue(repeat['ok'],repeat)
            self.assertEqual(repeat['value']['receipt']['id'],receipt_id)
            self.assertEqual(len(ResearchStore(path).list_history(receipt_id)['value']['items']),1)
            for file in (Path(directory)/'research-cache').glob('*.json'):file.unlink()
            self.assertFalse(reader.cached(receipt_id)['ok'])
            self.assertTrue(reader.read('S','https://example.com/thread','candidate')['ok'])
            self.assertTrue(reader.cached(receipt_id)['ok'])
            from records.backup import backup_local,restore_local
            backup=Path(directory)/'backup.sqlite3'
            restored_dir=Path(directory)/'restored';restored_dir.mkdir()
            restored=restored_dir/'db.sqlite3'
            self.assertTrue(backup_local(path,backup)['ok'])
            self.assertTrue(restore_local(backup,restored)['ok'])
            restored_store=ResearchRuntimeStore(restored)
            restored_run=Runner(restored).resume('run','restored-owner')['value']
            restored_reader=Reader(restored_store,'run',restored_run['token'],fetcher=Fetch())
            self.assertEqual(restored_reader.cached(receipt_id)['error']['code'],'CACHE_MISSING')
            self.assertTrue(restored_reader.read('S','https://example.com/thread','candidate')['ok'])
            output=Path(directory)/'public.json'
            self.assertTrue(Exchange(path).export_research(output)['ok'])
            self.assertNotIn('cacheKey',output.read_text())
            self.assertNotIn('Visible user need',output.read_text())
            cache=next((Path(directory)/'research-cache').glob('*.json'))
            cache.write_text('{}')
            self.assertEqual(reader.cached(receipt_id)['error']['code'],'CACHE_CORRUPT')
            self.assertTrue(reader.read('S','https://example.com/thread','candidate')['ok'])
            class BrokenFetch:
                def fetch(self,*args,**kwargs):
                    return dict(ok=True,value=dict(originalUrl='https://example.com/empty',finalUrl='https://example.com/empty',
                        status=200,headers={'content-type':'text/html'},body=b'<title>No body</title>'))
            failed=Reader(store,'run',run['token'],fetcher=BrokenFetch()).read('S','https://example.com/empty','bad')
            self.assertFalse(failed['ok'])
            self.assertEqual(len(ResearchStore(path).list_history(receipt_id)['value']['items']),1)
            self.assertTrue(Exchange(Path(directory)/'import.sqlite3').import_research(json.loads(output.read_text()),'import')['ok'])
