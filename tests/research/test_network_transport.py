import gzip
import json
import socket
import time
import unittest
from unittest.mock import patch


def stalled_worker(pipe, url, timeout, limit):
    time.sleep(10)


class TransportTests(unittest.TestCase):
    def test_url_boundary_rejects_auth_ports_controls_and_non_http(self):
        from research.network import target, NetworkError
        for url in ['file:///etc/passwd','http://user:pass@example.com','https://example.com:444/',
                    'https://example.com\n/header','http://[::1%25lo]/','http://example.com\\@other.com/',
                    'http://example.com:','http://%31%32%37.0.0.1/']:
            with self.subTest(url=url), self.assertRaises(NetworkError):
                target(url)
        self.assertEqual(target('https://EXAMPLE.com/a?q=1#ignored')['path'],'/a?q=1')

    def test_all_resolved_addresses_must_be_public(self):
        from research.network import resolve_public, NetworkError
        def entries(ips):
            return [(socket.AF_INET6 if ':' in ip else socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in ips]
        for ips in [['127.0.0.1'],['169.254.169.254'],['10.0.0.1'],['::1'],['::ffff:127.0.0.1'],
                    ['93.184.216.34','192.168.1.1'],['224.0.0.1'],['0.0.0.0'],['198.18.0.135']]:
            with self.subTest(ips=ips), self.assertRaises(NetworkError):
                resolve_public('example.com',443,resolver=lambda *a,**k:entries(ips))
        self.assertEqual(resolve_public('example.com',443,resolver=lambda *a,**k:entries(['93.184.216.34']))[1], '93.184.216.34')

    def test_benchmark_dns_can_use_pinned_doh_without_weakening_private_rejection(self):
        from research.network import resolve_public, NetworkError
        def entries(ips):
            return [(socket.AF_INET6 if ':' in ip else socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in ips]
        fallback=lambda host,port:entries(['93.184.216.34','2606:2800:220:1:248:1893:25c8:1946'])
        result=resolve_public('example.com',443,resolver=lambda *a,**k:entries(['198.18.0.135']),fallback=fallback)
        self.assertEqual(result,(socket.AF_INET,'93.184.216.34'))
        for system in (['10.0.0.1'],['198.18.0.1','10.0.0.1'],['93.184.216.34','198.18.0.1']):
            with self.subTest(system=system),self.assertRaises(NetworkError):
                resolve_public('example.com',443,resolver=lambda *a,ips=system,**k:entries(ips),fallback=fallback)
        with self.assertRaises(NetworkError):
            resolve_public('example.com',443,resolver=lambda *a,**k:entries(['198.18.0.2']),
                           fallback=lambda *a:entries(['127.0.0.1']))

    def test_pinned_socket_keeps_original_tls_hostname(self):
        from research.network import open_connection, target
        from unittest.mock import Mock
        sock, tls = Mock(), Mock()
        context = Mock(); context.wrap_socket.return_value = tls
        with patch('research.network.socket.socket',return_value=sock), patch('research.network.ssl.create_default_context',return_value=context):
            conn = open_connection(target('https://example.com/a'),(socket.AF_INET,'93.184.216.34'),2)
            sock.connect.assert_called_once_with(('93.184.216.34',443))
            context.wrap_socket.assert_called_once_with(sock,server_hostname='example.com')
            self.assertEqual(conn.host,'example.com')
            self.assertIs(conn.sock,tls)
            context.set_alpn_protocols.assert_called_once_with(['http/1.1'])

    def test_pinned_doh_validates_question_and_disables_client_subnet(self):
        from research.network import doh_query
        from unittest.mock import Mock
        answer={'Status':0,'TC':False,'CD':False,'Question':[{'name':'example.com.','type':1}],
                'Answer':[{'name':'example.com.','type':1,'TTL':60,'data':'93.184.216.34'}]}
        response=Mock(status=200)
        response.getheader.side_effect=lambda name,default=None: {
            'Content-Length':None,'Content-Type':'application/json; charset=UTF-8'}.get(name,default)
        response.read.return_value=json.dumps(answer).encode()
        conn=Mock();conn.getresponse.return_value=response
        with patch('research.network.open_connection',return_value=conn) as opened:
            self.assertEqual(doh_query('example.com',1,'8.8.8.8'),answer['Answer'])
        destination=opened.call_args.args[0]
        self.assertEqual((destination['host'],opened.call_args.args[1]),('dns.google',(socket.AF_INET,'8.8.8.8')))
        request=conn.request.call_args
        self.assertEqual(request.args[0],'GET')
        self.assertIn('edns_client_subnet=0.0.0.0%2F0',request.args[1])
        self.assertEqual(request.kwargs['headers']['Host'],'dns.google')

    def test_compressed_and_uncompressed_bodies_are_bounded(self):
        from research.network import decode_body, NetworkError
        self.assertEqual(decode_body(gzip.compress(b'hello'),'gzip',100),b'hello')
        for body,encoding in [(b'x'*101,'identity'),(gzip.compress(b'x'*10000),'gzip'),(b'broken','gzip'),(b'hello','br')]:
            with self.subTest(encoding=encoding), self.assertRaises(NetworkError):
                decode_body(body,encoding,100)

    def test_parent_terminates_blocked_worker(self):
        from research.network import bounded_request, NetworkError
        started = time.monotonic()
        with self.assertRaises(NetworkError) as error:
            bounded_request('https://example.com',timeout=.2,worker=stalled_worker)
        self.assertEqual(error.exception.code,'timeout')
        self.assertLess(time.monotonic()-started,3)
