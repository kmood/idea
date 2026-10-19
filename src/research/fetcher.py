"""Robots-aware bounded fetch orchestration; persistence stays in records."""
import hashlib
import math
from email.utils import parsedate_to_datetime
import time
import uuid
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser
from records.contracts import Fault
from records.network_policy import NetworkPolicyStore
from .network import NetworkError,USER_AGENT,bounded_request,target
from .runner import value


def robot_rules(body):
    try:
        parser=RobotFileParser();parser.parse(body.splitlines())
        delay=max(3,float(parser.crawl_delay(USER_AGENT) or 0))
        rate=parser.request_rate(USER_AGENT)
        if rate and rate.requests>0:delay=max(delay,rate.seconds/rate.requests)
        if not math.isfinite(delay):raise ValueError()
        return parser,delay
    except (ValueError,OverflowError):
        raise NetworkError('parse') from None


def retry_delay(header,current):
    try:
        if header.isdecimal():delay=float(header)
        else:delay=parsedate_to_datetime(header).timestamp()-current
        return max(3,delay) if math.isfinite(delay) else 86400
    except (ValueError,TypeError,OverflowError,AttributeError):
        return 60


class Fetcher:
    def __init__(self,store,run_id,token,*,transport=bounded_request,sleep=time.sleep,monotonic=time.monotonic):
        self.store,self.run_id,self.token=store,run_id,token
        self.transport,self.sleep,self.monotonic=transport,sleep,monotonic
        self.policy=NetworkPolicyStore(store)

    def call(self,source,url,kind,identity,deadline,delay=3,limit=2*1024*1024):
        destination=target(url)
        for _ in range(2):
            permit=self.policy.permit(destination['origin'],source,self.run_id,self.token,delay)
            if permit['ok']:break
            if permit['error']['code']!='RATE_LIMIT':value(permit)
            wait=permit['error']['retryAt']-self.store.execution.clock()
            if wait>=deadline-self.monotonic():raise NetworkError('timeout')
            self.sleep(max(0,wait))
        else:
            raise NetworkError('restricted')
        left=deadline-self.monotonic()
        if left<=0:raise NetworkError('timeout')
        call_id=str(uuid.uuid4())
        grant=value(self.store.execution.reserve(self.run_id,self.token,call_id,kind,identity))
        left=min(left,grant['expiresAt']-self.store.execution.clock())
        if left<=0:raise NetworkError('timeout')
        response=self.transport(url,timeout=min(30,left),limit=limit)
        value(self.store.execution.finish(self.run_id,self.token,call_id,hashlib.sha256(response['body']).hexdigest()))
        if response['status'] in (429,503) or 'retry-after' in response['headers']:
            delay=retry_delay(response['headers'].get('retry-after'),self.store.execution.clock())
            value(self.policy.postpone(destination['origin'],source,self.run_id,self.token,delay))
        return response

    def robots(self,source,url,deadline):
        origin=target(url)['origin']
        cached=value(self.policy.cached(origin,source))
        if cached is None:
            response=self.call(source,origin+'/robots.txt','request',None,deadline,limit=65536)
            status=response['status'];body='';delay=3
            if status==200:
                try:body=response['body'].decode('utf-8-sig')
                except UnicodeError:raise NetworkError('parse') from None
                if ('html' in response['headers'].get('content-type','').lower() or '<html' in body.lower() or
                        '<!doctype' in body.lower()):raise NetworkError('restricted')
                _,delay=robot_rules(body)
            value(self.policy.remember(origin,source,self.run_id,self.token,status,body,delay,
                  ttl=86400 if status in (200,404,410) else 60))
            cached=dict(status=status,body=body,delay=delay)
        if cached['status'] in (404,410):return cached['delay']
        if cached['status']!=200:raise NetworkError('restricted')
        parser,_=robot_rules(cached['body'])
        if not parser.can_fetch(USER_AGENT,url):raise NetworkError('restricted')
        return cached['delay']

    def fetch(self,source,url,identity,*,auxiliary=False):
        deadline=self.monotonic()+30
        original=url
        try:
            for hop in range(4):
                destination=target(url)
                url=destination['origin']+destination['path']
                delay=self.robots(source,url,deadline)
                response=self.call(source,url,'auxiliary' if auxiliary else 'discussion',identity,deadline,delay)
                if response['status'] in (301,302,303,307,308):
                    if hop==3 or not response['headers'].get('location'):raise NetworkError('restricted')
                    url=urljoin(url,response['headers']['location'])
                    continue
                if response['status'] in (401,403,429):raise NetworkError('restricted')
                if response['status']!=200:raise NetworkError('network')
                return dict(ok=True,value=dict(originalUrl=original,finalUrl=url,**response))
        except NetworkError as exc:
            return dict(ok=False,error=dict(code=exc.code,message='Public reading was not completed'))
        except Fault as exc:
            return dict(ok=False,error=exc.error)
