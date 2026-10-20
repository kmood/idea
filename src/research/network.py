"""One-hop public HTTP transport. No proxies, credentials, cookies or redirects."""
import http.client
import ipaddress
import json
import multiprocessing
import re
import socket
import ssl
import zlib
from urllib.parse import quote, urlsplit

MAX_BYTES = 2 * 1024 * 1024
USER_AGENT = 'IdeaResearchBot/1.0'
BENCHMARK = ipaddress.ip_network('198.18.0.0/15')
DOH_BOOTSTRAP = ('8.8.8.8','8.8.4.4')


class NetworkError(Exception):
    def __init__(self,code):
        self.code = code
        super().__init__(code)


def target(url):
    if not isinstance(url,str) or len(url)>8192 or any(ord(c)<33 or ord(c)==127 for c in url) or '\\' in url:
        raise NetworkError('restricted')
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError()
        if '%' in parsed.hostname or parsed.netloc.endswith(':'):
            raise ValueError()
        host = parsed.hostname.rstrip('.').encode('idna').decode('ascii').lower()
        if ':' not in host and not re.fullmatch(r'[a-z0-9.-]+',host):
            raise ValueError()
        port = 443 if parsed.scheme=='https' else 80
        if parsed.port is not None and parsed.port != port:
            raise ValueError()
        authority = '['+host+']' if ':' in host else host
        path = quote(parsed.path or '/',safe="/%:@!$&'()*+,;=-._~")
        if parsed.query:
            path += '?' + quote(parsed.query,safe="/%?:@!$&'()*+,;=-._~")
        return dict(scheme=parsed.scheme,host=host,port=port,authority=authority,path=path,
                    origin=parsed.scheme+'://'+authority)
    except (ValueError,UnicodeError):
        raise NetworkError('restricted') from None


def public_address(entry):
    family,_,_,_,address=entry
    ip=ipaddress.ip_address(address[0])
    underlying=ip.ipv4_mapped if isinstance(ip,ipaddress.IPv6Address) and ip.ipv4_mapped else ip
    return (family in (socket.AF_INET,socket.AF_INET6) and underlying.is_global and
            not underlying.is_multicast and not underlying.is_reserved and
            not (isinstance(ip,ipaddress.IPv6Address) and (ip.teredo or ip.sixtofour)))


def benchmark_address(entry):
    try:
        ip=ipaddress.ip_address(entry[4][0])
        underlying=(ip.ipv4_mapped if isinstance(ip,ipaddress.IPv6Address) and ip.ipv4_mapped
                    else ip)
        return isinstance(underlying,ipaddress.IPv4Address) and underlying in BENCHMARK
    except (ValueError,IndexError,TypeError):
        return False


def resolve_public(host,port,*,resolver=socket.getaddrinfo,fallback=None):
    addresses = resolver(host,port,type=socket.SOCK_STREAM)
    if not addresses or len(addresses)>128:
        raise NetworkError('restricted')
    if not all(public_address(entry) for entry in addresses):
        if fallback is None or not all(benchmark_address(entry) for entry in addresses):
            raise NetworkError('restricted')
        addresses=fallback(host,port)
        if not addresses or len(addresses)>128 or not all(public_address(entry) for entry in addresses):
            raise NetworkError('restricted')
    return addresses[0][0],addresses[0][4][0]


def open_connection(destination,address,timeout):
    family,ip = address
    sock = socket.socket(family,socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        sock.connect((ip,destination['port']))
        if destination['scheme']=='https':
            context = ssl.create_default_context()
            context.set_alpn_protocols(['http/1.1'])
            sock = context.wrap_socket(sock,server_hostname=destination['host'])
        conn = http.client.HTTPConnection(destination['host'],destination['port'],timeout=timeout)
        conn.sock = sock
        conn.auto_open = False  # Never fall back to a second DNS lookup.
        return conn
    except BaseException:
        sock.close()
        raise


def doh_query(host,record_type,bootstrap,timeout=5):
    """Query the configured HTTPS resolver through a pinned public bootstrap IP."""
    # RFC 8484 requires authenticated HTTPS transport: https://www.rfc-editor.org/rfc/rfc8484.html
    # Google JSON response contract and privacy parameter:
    # https://developers.google.com/speed/public-dns/docs/doh/json
    destination=target('https://dns.google/resolve?name='+quote(host,safe='')+
                       '&type='+str(record_type)+'&edns_client_subnet=0.0.0.0%2F0')
    conn=open_connection(destination,(socket.AF_INET,bootstrap),timeout)
    try:
        conn.request('GET',destination['path'],headers={'Host':destination['authority'],
                     'User-Agent':USER_AGENT,'Accept':'application/json','Connection':'close'})
        response=conn.getresponse()
        length=response.getheader('Content-Length')
        if response.status!=200 or (length is not None and (not length.isdecimal() or int(length)>65536)):
            raise NetworkError('network')
        body=response.read(65537)
        if len(body)>65536 or not response.getheader('Content-Type','').lower().startswith('application/json'):
            raise NetworkError('parse')
        data=json.loads(body)
        question=data.get('Question')
        if (data.get('Status')!=0 or data.get('TC') is not False or data.get('CD') is not False or
                not isinstance(question,list) or len(question)!=1 or
                question[0].get('name','').rstrip('.').lower()!=host or question[0].get('type')!=record_type):
            raise NetworkError('restricted')
        return data.get('Answer',[])
    except (OSError,http.client.HTTPException,ValueError,UnicodeError,AttributeError):
        raise NetworkError('network') from None
    finally:
        conn.close()


def resolve_doh(host,port):
    addresses=[]
    for record_type,family in ((1,socket.AF_INET),(28,socket.AF_INET6)):
        answers=None
        for bootstrap in DOH_BOOTSTRAP:
            try:
                answers=doh_query(host,record_type,bootstrap);break
            except NetworkError:
                continue
        if answers is None:continue
        if not isinstance(answers,list) or len(answers)>128:raise NetworkError('restricted')
        for answer in answers:
            if isinstance(answer,dict) and answer.get('type')==record_type:
                value=answer.get('data')
                try:
                    ip=ipaddress.ip_address(value)
                except ValueError:
                    raise NetworkError('restricted') from None
                if (family==socket.AF_INET and isinstance(ip,ipaddress.IPv4Address)) or (
                        family==socket.AF_INET6 and isinstance(ip,ipaddress.IPv6Address)):
                    addresses.append((family,socket.SOCK_STREAM,6,'',(value,port)))
                else:raise NetworkError('restricted')
    if not addresses:raise NetworkError('restricted')
    return addresses


def decode_body(body,encoding,limit):
    if len(body)>limit:
        raise NetworkError('size')
    if encoding in ('','identity'):
        return body
    if encoding != 'gzip':
        raise NetworkError('unsupported')
    try:
        decoder = zlib.decompressobj(16+zlib.MAX_WBITS)
        result = decoder.decompress(body,limit+1)
        if len(result)>limit or decoder.unconsumed_tail:
            raise NetworkError('size')
        if not decoder.eof or decoder.unused_data:
            raise NetworkError('parse')
        return result
    except zlib.error:
        raise NetworkError('parse') from None


def request_once(url,timeout,limit):
    destination = target(url)
    address = resolve_public(destination['host'],destination['port'],fallback=resolve_doh)
    conn = open_connection(destination,address,timeout)
    try:
        conn.request('GET',destination['path'],headers={'Host':destination['authority'],
                     'User-Agent':USER_AGENT,'Accept-Encoding':'gzip','Connection':'close'})
        response = conn.getresponse()
        pairs = response.getheaders()
        if sum(len(k)+len(v) for k,v in pairs)>65536:
            raise NetworkError('size')
        for name in ('Content-Length','Content-Encoding','Location'):
            if len(response.headers.get_all(name,[]))>1:
                raise NetworkError('parse')
        length = response.getheader('Content-Length')
        if length is not None and (not length.isdecimal() or int(length)>limit):
            raise NetworkError('size')
        body = response.read(limit+1)
        body = decode_body(body,response.getheader('Content-Encoding','identity').lower(),limit)
        allowed = {'content-type','location','retry-after'}
        headers = {k.lower():v for k,v in pairs if k.lower() in allowed}
        return dict(status=response.status,headers=headers,body=body)
    finally:
        conn.close()


def _worker(pipe,url,timeout,limit):
    try:
        pipe.send(('ok',request_once(url,timeout,limit)))
    except NetworkError as exc:
        pipe.send(('error',exc.code))
    except (OSError,http.client.HTTPException,ValueError,UnicodeError):
        pipe.send(('error','network'))
    finally:
        pipe.close()


def bounded_request(url,*,timeout=30,limit=MAX_BYTES,worker=_worker):
    """The parent can terminate DNS, TLS and slow body reads at one deadline."""
    import time
    if not isinstance(timeout,(int,float)) or not 0<timeout<=30 or type(limit) is not int or not 0<limit<=MAX_BYTES:
        raise NetworkError('restricted')
    target(url)
    context = multiprocessing.get_context('spawn')
    reader,writer = context.Pipe(duplex=False)
    process = context.Process(target=worker,args=(writer,url,timeout,limit),daemon=True)
    deadline = time.monotonic()+timeout
    started = False
    try:
        process.start(); started = True; writer.close()
        if not reader.poll(max(0,deadline-time.monotonic())):
            raise NetworkError('timeout')
        status,result = reader.recv()
        if time.monotonic()>=deadline:
            raise NetworkError('timeout')
        if status != 'ok':
            raise NetworkError(result)
        return result
    except EOFError:
        raise NetworkError('network') from None
    finally:
        reader.close(); writer.close()
        if started:
            process.join(.1)
            if process.is_alive():
                process.terminate(); process.join(.1)
            if process.is_alive():
                process.kill(); process.join(.1)
            process.close()
