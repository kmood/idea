from test_source import StoreCase, source


def evidence(id='EV-TEST'):
    return dict(id=id, kind='Evidence', sourceId='CN-TEST', url='https://example.com/thread',
                claim='合成需求主张', summary='用户描述痛点', publishedAt=None,
                accessedAt='2026-10-15T00:00:00Z', nature='author_claim', level='E1', paymentSignal=None, rebutsClaim=None)


def idea(id='IDEA-TEST'):
    return dict(id=id, kind='Idea', title='合成点子', audience='小商家', problem='重复整理术语',
                earningHypothesis='假设按项目收费', industry=['电商'], sideHustleTypes=['服务'], markets=['国内'],
                researchStatus='待验证', evidenceIds=['EV-TEST'])


def trend(id='TREND-TEST'):
    return dict(id=id, kind='Trend', title='合成趋势', summary='流程正在变化', evidenceIds=['EV-TEST'],
                impact={'nature': 'inference', 'text': '可能产生校验需求'}, questions=['是否愿意付费'])


class EvidenceTests(StoreCase):
    def seed(self):
        self.value(self.store.create_research(source(), 's'))
        self.value(self.store.create_research(evidence(), 'e'))

    def test_minimal_idea_with_unknown_cost_and_payment(self):
        self.seed()
        saved = self.value(self.store.create_research(idea(), 'i'))
        self.assertNotIn('cost', saved)
        self.value(self.store.create_research(trend(), 't'))
        for key in ('audience', 'problem', 'earningHypothesis'):
            self.assertFalse(self.store.create_research(idea(key) | {key: ''}, key)['ok'])

    def test_invalid_references_and_nested_fields(self):
        self.assertFalse(self.store.create_research(evidence(), 'missing')['ok'])
        self.seed()
        for record in (idea() | {'evidenceIds': ['MISSING']}, idea() | {'evidenceIds': ['CN-TEST']},
                       trend() | {'impact': {'nature': 'inference', 'text': 'x', 'notes': 'private'}},
                       evidence('bad') | {'nature': 'promotion', 'paymentSignal': 'paid'}):
            self.assertFalse(self.store.create_research(record, 'bad')['ok'])

    def test_correction_preserves_pinned_evidence_revision(self):
        self.seed()
        self.value(self.store.create_research(idea(), 'i'))
        self.value(self.store.patch_research('EV-TEST', 1, {'claim': '更正主张', 'rebutsClaim': '旧主张'}, '发现反证', 'fix'))
        old = self.value(self.store.read_record('EV-TEST', 1))['record']
        self.assertEqual(old['claim'], '合成需求主张')
        self.assertIsNone(old['publishedAt'])
        event = self.value(self.store.list_history('IDEA-TEST'))['items'][0]
        self.assertEqual(event['evidence'], [{'recordId': 'EV-TEST', 'revision': 1}])
