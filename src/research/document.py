"""Non-executing extraction of visible, explicitly scoped article text."""
import hashlib
import re
from html.parser import HTMLParser
from email.message import Message
from records.contracts import date_valid,stamp
from .network import NetworkError,MAX_BYTES

VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
IGNORE={'script','style','nav','header','footer','aside','form','svg','template','noscript','h1','h2','h3','h4','h5','h6'}
BLOCK={'p','li','blockquote','pre','h1','h2','h3','h4','div','section','article','main','br'}
SCOPES={'post-content','message-body','comment-body','topic-body','cooked',
        'topic_content','reply_content'}


class VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[];self.skip=0;self.scope=0;self.chunks=[];self.blocks=[];self.dates=set()
        self.restricted=False;self.title=[]

    def flush(self):
        text=re.sub(r'\s+',' ',''.join(self.chunks)).strip();self.chunks=[]
        if text:self.blocks.append(text)
        if len(self.blocks)>500:raise NetworkError('size')

    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        if tag=='input' and (attributes.get('type') or '').lower()=='password':self.restricted=True
        if tag in BLOCK:self.flush()
        style=re.sub(r'\s+','',attributes.get('style','') or '').lower()
        hidden=(tag in IGNORE or 'hidden' in attributes or (attributes.get('aria-hidden') or '').lower()=='true' or
                'display:none' in style or 'visibility:hidden' in style)
        scoped=tag in ('article','main') or bool(set((attributes.get('class','') or '').split()) & SCOPES)
        if tag=='time' and self.scope and not self.skip and not hidden and attributes.get('datetime'):
            self.dates.add(attributes['datetime'])
        if tag not in VOID:
            if len(self.stack)>=256:raise NetworkError('parse')
            self.stack.append((tag,hidden,scoped));self.skip+=hidden;self.scope+=scoped

    def handle_endtag(self,tag):
        if tag in BLOCK:self.flush()
        for index in range(len(self.stack)-1,-1,-1):
            if self.stack[index][0]==tag:
                for _,hidden,scoped in self.stack[index:]:self.skip-=hidden;self.scope-=scoped
                del self.stack[index:]
                break

    def handle_data(self,data):
        if self.stack and self.stack[-1][0]=='title':self.title.append(data)
        if self.scope and not self.skip:self.chunks.append(data)


def parse_document(body,content_type):
    if not isinstance(body,bytes) or len(body)>MAX_BYTES:raise NetworkError('size')
    message=Message();message['content-type']=content_type
    kind=message.get_content_type()
    if kind not in ('text/plain','text/html','application/xhtml+xml'):raise NetworkError('unsupported')
    try:text=body.decode(message.get_content_charset() or 'utf-8')
    except (UnicodeError,LookupError):raise NetworkError('parse') from None
    dates=set()
    if kind=='text/plain':
        texts=[re.sub(r'\s+',' ',part).strip() for part in text.split('\n\n') if part.strip()]
    else:
        parser=VisibleHTML();parser.feed(text);parser.close();parser.flush()
        title=''.join(parser.title).lower()
        if parser.restricted or any(marker in title for marker in ('captcha','access denied','verify you are human','验证码','登录后查看')):
            raise NetworkError('restricted')
        texts=parser.blocks;dates=parser.dates
    if not texts:raise NetworkError('parse')
    if len(texts)>500:raise NetworkError('size')
    blocks=[];counts={}
    for text in texts:
        key=hashlib.sha256(text.encode()).hexdigest()[:20]
        counts[key]=counts.get(key,0)+1
        blocks.append(dict(blockId=f'b-{key}-{counts[key]}',text=text))
    result=dict(blocks=blocks,precision='unknown',publishedAt=None,publishedDate=None,dateBasis=None,
                visibleScope='plain text' if kind=='text/plain' else 'visible article/main or recognized discussion body',truncated=False)
    if len(dates)==1:
        date=next(iter(dates))
        if len(date)==10 and date_valid(date):result.update(precision='date',publishedDate=date,dateBasis='visible scoped time element datetime')
        elif stamp(date):result.update(precision='instant',publishedAt=date,dateBasis='visible scoped time element datetime')
    return result
