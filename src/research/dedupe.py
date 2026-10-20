"""Conservative exact locations; similarity never authorizes a merge."""
from urllib.parse import urlsplit,urlunsplit,unquote
from records.contracts import boundary,require,text,valid_url
from records.exchange import digest
from records.identity import IdentityStore
from .runner import value

TRACKING={'utm_source','utm_medium','utm_campaign','utm_term','utm_content','utm_id','gclid','fbclid','msclkid'}


def normalize_url(url):
    require(valid_url(url) and len(url)<=8192)
    parsed=urlsplit(url)
    require(parsed.username is None and parsed.password is None,'Credential URLs are not public locators')
    # Preserve query order, duplicates, encoding, unknown keys and reply anchors.
    query='&'.join(part for part in parsed.query.split('&') if unquote(part.split('=',1)[0]) not in TRACKING)
    return urlunsplit((parsed.scheme.lower(),parsed.netloc.lower(),parsed.path,query,parsed.fragment))


def locator(source_id,url,*,post_id=None,reply_id=None):
    require(text(source_id))
    require(post_id is None or text(post_id));require(reply_id is None or (text(reply_id) and post_id is not None))
    identity=dict(sourceId=source_id,postId=post_id,replyId=reply_id) if post_id is not None else dict(sourceId=source_id,url=normalize_url(url))
    return 'location:'+digest(identity)


class Deduplicator:
    def __init__(self,path):self.store=IdentityStore(path)

    @boundary
    def inspect(self,receipt_id,*,post_id=None,reply_id=None,cursor='',limit=50):
        current=value(self.store.receipt(receipt_id));data=current['data']
        require(data['status'] in ('readable','partial'))
        key=locator(data['sourceId'],data['originalUrl'],post_id=post_id,reply_id=reply_id)
        # Stable source IDs may be supplied by a verified site parser; outcomes
        # retain that key publicly. Never infer them from titles or URL guesses.
        urls={normalize_url(data[k]) for k in ('originalUrl','finalUrl')}
        page=value(self.store.page(data['sourceId'],cursor,limit));matches=[];outcomes=[]
        for record in page['items']:
            if record['id']==receipt_id or record['archived']:continue
            other=record['data']
            if record['artifactType']=='CandidateOutcome':
                if other['locator']==key:
                    outcomes.append(dict(outcomeId=record['id'],status=other['status'],recordRefs=other['recordRefs']))
                continue
            if other['status'] not in ('readable','partial'):continue
            if not urls & {normalize_url(other[k]) for k in ('originalUrl','finalUrl')}:continue
            same=[b['blockId'] for b in data['blocks']]==[b['blockId'] for b in other['blocks']]
            matches.append(dict(receiptId=record['id'],relation='same_content' if same else 'changed_content',
                                needsClaimReview=True,partial=data['truncated'] or other['truncated']))
        return dict(locator=key,matches=matches,outcomes=outcomes,nextCursor=page['nextCursor'],complete=page['nextCursor'] is None)

    def linked_records(self,receipt_id,cursor='',limit=50):
        return self.store.linked(receipt_id,cursor,limit)

    @boundary
    def possible_duplicate(self,receipt_id,other_receipt_id,reason):
        require(text(reason) and receipt_id!=other_receipt_id)
        value(self.store.receipt(receipt_id));value(self.store.receipt(other_receipt_id))
        return dict(status='possibleDuplicate',receiptIds=[receipt_id,other_receipt_id],reason=reason,merge=False)
