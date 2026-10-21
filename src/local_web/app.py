"""Read-only HTTP application and standard-library server adapter."""
import html
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .catalog import find_record, load_catalog, validate_catalog
from .markdown import render_markdown


STATIC=Path(__file__).with_name('static')
HEADERS={'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
         'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store'}


class LocalWebApp:
    def __init__(self,root):self.root=Path(root).resolve()

    def response(self,status,body,content_type):
        headers=dict(HEADERS);headers['Content-Type']=content_type
        return status,headers,body if isinstance(body,bytes) else body.encode('utf-8')

    def json(self,status,value):
        return self.response(status,json.dumps(value,ensure_ascii=False,separators=(',',':')),'application/json; charset=utf-8')

    def error(self,status,code,message):return self.json(status,{'error':{'code':code,'message':message}})

    def dispatch(self,method,target):
        try:return self._dispatch(method,target)
        except (OSError,UnicodeError,ValueError):
            return self.error(500,'REPOSITORY_ERROR','Repository data could not be read')

    def _dispatch(self,method,target):
        if method not in ('GET','HEAD'):return self.error(405,'METHOD_NOT_ALLOWED','Only GET and HEAD are supported')
        path=unquote(urlsplit(target).path)
        if path=='/api/catalog':return self.json(200,load_catalog(self.root))
        if path=='/api/consistency':return self.json(200,validate_catalog(self.root))
        if path.startswith('/api/documents/'):
            parts=path.strip('/').split('/')
            if len(parts)!=4 or parts[0:2]!=['api','documents'] or not parts[2] or not parts[3] or parts[3] in ('.','..'):
                return self.error(400,'INVALID_PATH','Document path is invalid')
            kind,record_id=parts[2],parts[3];record=find_record(self.root,kind,record_id)
            if record is None:return self.error(404,'NOT_FOUND','Document was not found')
            if kind=='source':
                fields=[('受众/类型',record['summary']),('观察信号',record['marketOrSource']),('访问状态',record['status']),('优先级',record.get('priority'))]
                body='<h1>'+html.escape(record['id']+' '+record['title'])+'</h1><dl>'+''.join(
                    '<dt>'+html.escape(name)+'</dt><dd>'+html.escape(value or '未知')+'</dd>' for name,value in fields)+'</dl>'
                if record.get('url'):body+='<p><a href="'+html.escape(record['url'],quote=True)+'" rel="noreferrer">打开来源</a></p>'
            else:
                document=(self.root/record['documentPath']).resolve()
                allowed=(self.root/kind.replace('idea','ideas').replace('trend','trends')).resolve()
                if allowed not in document.parents or not document.is_file():return self.error(404,'NOT_FOUND','Document was not found')
                body=render_markdown(document.read_text(encoding='utf-8'))
            return self.json(200,{'id':record['id'],'kind':kind,'title':record['title'],'html':body,'documentPath':record['documentPath']})
        static_name='index.html' if path in ('/','/index.html') else path.removeprefix('/assets/') if path.startswith('/assets/') else None
        if static_name not in ('index.html','app.css','app.js'):return self.error(404,'NOT_FOUND','Resource was not found')
        file=STATIC/static_name
        mime=mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
        if mime.startswith('text/') or mime=='application/javascript':mime+='; charset=utf-8'
        return self.response(200,file.read_bytes(),mime)


def handler_for(app):
    class Handler(BaseHTTPRequestHandler):
        def handle_request(self,method):
            status,headers,body=app.dispatch(method,self.path);self.send_response(status)
            for key,value in headers.items():self.send_header(key,value)
            self.send_header('Content-Length',str(len(body)));self.end_headers()
            if method!='HEAD':self.wfile.write(body)
        def do_GET(self):self.handle_request('GET')
        def do_HEAD(self):self.handle_request('HEAD')
        def do_POST(self):self.handle_request('POST')
        def log_message(self,format,*args):pass
    return Handler


def serve(root,host,port):
    server=ThreadingHTTPServer((host,port),handler_for(LocalWebApp(root)))
    print(f'Idea dashboard: http://{host}:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
