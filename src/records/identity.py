"""Read identity from public records so imports retain deduplication evidence."""
import json
from contextlib import closing
from .contracts import boundary,require,text
from .storage import Database,get


class IdentityStore:
    def __init__(self,path):self.db=Database(path)

    @boundary
    def receipt(self,receipt_id):
        with closing(self.db.connect()) as conn:
            record=get(conn,receipt_id)
            require(record['kind']=='ResearchArtifact' and record['artifactType']=='ReadReceipt')
            return record

    @boundary
    def page(self,source_id,cursor='',limit=50):
        require(text(source_id) and isinstance(cursor,str) and type(limit) is int and 1<=limit<=100)
        with closing(self.db.connect()) as conn:
            conn.execute('BEGIN')
            require(get(conn,source_id)['kind']=='Source')
            rows=conn.execute("SELECT id,payload FROM research_records WHERE kind='ResearchArtifact' AND id>? AND json_extract(payload,'$.artifactType') IN ('ReadReceipt','CandidateOutcome') AND json_extract(payload,'$.data.sourceId')=? ORDER BY id LIMIT ?",(cursor,source_id,limit+1)).fetchall()
            return dict(items=[json.loads(row['payload']) for row in rows[:limit]],nextCursor=rows[limit-1]['id'] if len(rows)>limit else None)

    @boundary
    def linked(self,receipt_id,cursor='',limit=50):
        require(text(receipt_id) and isinstance(cursor,str) and type(limit) is int and 1<=limit<=100)
        with closing(self.db.connect()) as conn:
            conn.execute('BEGIN');get(conn,receipt_id)
            rows=conn.execute("""SELECT r.id,r.revision FROM research_records r WHERE r.id>? AND
                ((r.kind='Evidence' AND json_extract(r.payload,'$.observation.receiptId')=?) OR
                 (r.kind IN ('Trend','Idea') AND EXISTS (
                    SELECT 1 FROM evidence_links l JOIN record_versions v ON v.record_id=l.evidence_id AND v.revision=l.evidence_revision
                    WHERE l.record_id=r.id AND json_extract(v.payload,'$.observation.receiptId')=?)))
                ORDER BY r.id LIMIT ?""",(cursor,receipt_id,receipt_id,limit+1)).fetchall()
            return dict(items=[dict(recordId=row['id'],revision=row['revision']) for row in rows[:limit]],nextCursor=rows[limit-1]['id'] if len(rows)>limit else None)
