"""One-hop public HTTP transport. No proxies, credentials, cookies or redirects."""
import http.client
import ipaddress
import multiprocessing
import re
import socket
import ssl
import zlib
from urllib.parse import quote, urlsplit

MAX_BYTES = 2 * 1024 * 1024
USER_AGENT = 'IdeaResearchBot/1.0'


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


def resolve_public(host,port,*,resolver=socket.getaddrinfo):
    addresses = resolver(host,port,type=socket.SOCK_STREAM)
    if not addresses or len(addresses)>128:
        raise NetworkError('restricted')
    for family,_,_,_,address in addresses:
        ip = ipaddress.ip_address(address[0])
        underlying = ip.ipv4_mapped if isinstance(ip,ipaddress.IPv6Address) and ip.ipv4_mapped else ip
        if (family not in (socket.AF_INET,socket.AF_INET6) or not underlying.is_global or
                underlying.is_multicast or underlying.is_reserved or
                (isinstance(ip,ipaddress.IPv6Address) and (ip.teredo or ip.sixtofour))):
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
    address = resolve_public(destination['host'],destination['port'])
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
