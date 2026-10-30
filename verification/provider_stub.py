"""Loopback HTTP fixture for real OpenAI/Anthropic SDKs, never live credentials."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import threading
import time


class ProviderStub:
    def __init__(self):
        self.text='plain response';self.finish='stop';self.status=200;self.delay=0;self.calls=[]
        outer=self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))));outer.calls.append((self.path,body));time.sleep(outer.delay)
                if outer.status!=200:
                    data={'error':{'type':'rate_limit_error','message':'synthetic provider failure'}}
                elif self.path.endswith('/messages'):
                    data={'id':'msg_fixture','type':'message','role':'assistant','model':body['model'],'content':[{'type':'text','text':outer.text}],'stop_reason':'end_turn' if outer.finish=='stop' else outer.finish,'stop_sequence':None,'usage':{'input_tokens':1,'output_tokens':1}}
                else:
                    data={'id':'fixture','object':'chat.completion','created':0,'model':body['model'],'choices':[{'index':0,'message':{'role':'assistant','content':outer.text},'finish_reason':outer.finish}],'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}
                raw=json.dumps(data).encode();self.send_response(outer.status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
                try:self.wfile.write(raw)
                except (BrokenPipeError,ConnectionResetError):pass
            def log_message(self,*args):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def __enter__(self):
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.server.shutdown();self.server.server_close();self.thread.join()
