"""Public Reader orchestration; network text remains data, never instructions."""
import hashlib
import json
import os
import stat
import tempfile
from records.contracts import Fault,boundary,encoded,now
from records.readings import ReadingStore
from .document import parse_document
from .fetcher import Fetcher
from .network import NetworkError
from .runner import value

CACHE_LIMIT=16*1024*1024


class Reader:
    def __init__(self,runtime,run_id,token,*,fetcher=None):
        self.runtime=runtime;self.run_id=run_id;self.token=token
        self.fetcher=fetcher or Fetcher(runtime,run_id,token)
        self.readings=ReadingStore(runtime)
        self.directory=runtime.db.path.parent/'research-cache'

    def cache_directory(self):
        self.directory.mkdir(mode=0o700,exist_ok=True)
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise Fault('CACHE_UNSAFE','Cache must be a local directory')

    def store_cache(self,document):
        self.cache_directory()
        payload=encoded(document).encode();key=hashlib.sha256(payload).hexdigest()
        if len(payload)>CACHE_LIMIT:raise Fault('SIZE_LIMIT','Visible text exceeds cache limit')
        descriptor,path=tempfile.mkstemp(dir=self.directory,prefix='.pending-')
        try:
            with os.fdopen(descriptor,'wb') as stream:
                stream.write(payload);stream.flush();os.fsync(stream.fileno())
            os.replace(path,self.directory/(key+'.json'))
        finally:
            if os.path.exists(path):os.unlink(path)
        return key

    @boundary
    def read(self,source_id,url,candidate_id,*,auxiliary=False):
        response=value(self.fetcher.fetch(source_id,url,candidate_id,auxiliary=auxiliary))
        try:document=parse_document(response['body'],response['headers'].get('content-type',''))
        except NetworkError as exc:raise Fault(exc.code,'Public document could not be read') from None
        key=self.store_cache(document)
        # Public receipts identify blocks without copying entire discussions into Git.
        blocks=[dict(blockId=block['blockId'],summary=f'已读取正文块 {index+1}；正文仅保存在本机缓存。')
                for index,block in enumerate(document['blocks'])]
        data=dict(runId=self.run_id,sourceId=source_id,originalUrl=response['originalUrl'],finalUrl=response['finalUrl'],
                  fetchedAt=now(),status='readable',executor='public-reader',fingerprint=key,blocks=blocks,error=None,
                  **{field:document[field] for field in ('visibleScope','truncated','precision','publishedAt','publishedDate','dateBasis')})
        return value(self.readings.capture(self.run_id,self.token,data,key))

    @boundary
    def cached(self,receipt_id):
        pointer=value(self.readings.pointer(receipt_id));self.cache_directory()
        path=self.directory/(pointer['cacheKey']+'.json')
        try:descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        except FileNotFoundError:raise Fault('CACHE_MISSING','Read the original public page again') from None
        with os.fdopen(descriptor,'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise Fault('CACHE_UNSAFE')
            payload=stream.read(CACHE_LIMIT+1)
        if len(payload)>CACHE_LIMIT or hashlib.sha256(payload).hexdigest()!=pointer['cacheKey']:
            raise Fault('CACHE_CORRUPT','Read the original public page again')
        return json.loads(payload)
