"""Explicit reversible relationships; no semantic deduplication guesses."""
from .contracts import boundary, now, require, text
from .storage import Database, expected, get, save


def canonical(conn, id: str) -> str:
    seen = set()
    while True:
        require(id not in seen, 'Merge cycle')
        seen.add(id)
        target = get(conn, id)['mergedInto']
        if target is None:
            return id
        id = target


class Relations:
    def __init__(self, path):
        self.db = Database(path)

    @boundary
    def merge_records(self, source_id: str, target_id: str, source_revision: int, target_revision: int, reason: str, operation_id: str) -> dict:
        return self._change('merge', source_id, target_id, source_revision, target_revision, reason, operation_id)

    @boundary
    def unmerge_records(self, source_id: str, target_id: str, source_revision: int, target_revision: int, reason: str, operation_id: str) -> dict:
        return self._change('unmerge', source_id, target_id, source_revision, target_revision, reason, operation_id)

    @boundary
    def link_derived_idea(self, trend_id: str, idea_id: str, trend_revision: int, idea_revision: int, operation_id: str) -> dict:
        return self._change('derive', trend_id, idea_id, trend_revision, idea_revision, 'Derived idea', operation_id)

    def _change(self, mode, source_id, target_id, source_revision, target_revision, reason, operation_id):
        require(text(reason) and source_id != target_id)
        def action(conn):
            source, target = get(conn, source_id), get(conn, target_id)
            expected(source, source_revision); expected(target, target_revision)
            left, right = dict(source), dict(target)
            if mode == 'derive':
                require(source['kind'] == 'Trend' and target['kind'] == 'Idea')
                left['derivedIdeas'] = sorted(set(source.get('derivedIdeas', []) + [target_id]))
                right['derivedFrom'] = sorted(set(target.get('derivedFrom', []) + [source_id]))
                if left == source and right == target:
                    return {'source': source, 'target': target}
            else:
                require(source['kind'] == target['kind'], 'Merge requires matching kinds')
                if mode == 'merge':
                    require(source['mergedInto'] is None, 'Unmerge before changing a merge target')
                    require(canonical(conn, target_id) != source_id, 'Merge cycle')
                    left['mergedInto'] = target_id
                else:
                    require(source['mergedInto'] == target_id, 'Merge relationship does not match')
                    left['mergedInto'] = None
            # Both revisions protect the relationship. Neither payload is deleted.
            for record, before in ((left, source), (right, target)):
                record.update(revision=before['revision']+1, updatedAt=now())
                save(conn, record, before, operation_id, mode, reason)
            return {'source': left, 'target': right}
        return self.db.run('research', operation_id, dict(action=mode, sourceId=source_id, targetId=target_id,
                           sourceRevision=source_revision, targetRevision=target_revision, reason=reason), action)
