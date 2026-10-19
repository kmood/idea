import gzip
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
