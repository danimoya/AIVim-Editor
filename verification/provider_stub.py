"""Loopback HTTP fixture for real OpenAI/Anthropic SDKs, never live credentials."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import threading
import time


class ProviderStub:
    def __init__(self,ssl_context=None):
        self.models=['fixture-model'];self.required_token=None
        self.text='plain response';self.finish='stop';self.status=200;self.delay=0;self.calls=[]
        outer=self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if outer.required_token and self.headers.get('Authorization')!='Bearer '+outer.required_token:
                    self.send_response(401);self.end_headers();return
                data={'object':'list','data':[{'id':name,'object':'model'} for name in outer.models]}
                raw=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def do_POST(self):
                if outer.required_token and self.headers.get('Authorization')!='Bearer '+outer.required_token:
                    raw=b'{"error":{"message":"Unauthorized","type":"authentication_error"}}'
                    self.send_response(401);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return

                body=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))));outer.calls.append((self.path,body));time.sleep(outer.delay)
                if outer.status!=200:
                    data={'error':{'type':'rate_limit_error','message':'synthetic provider failure'}}
                elif self.path.endswith('/messages'):
                    data={'id':'msg_fixture','type':'message','role':'assistant','model':body['model'],'content':[{'type':'text','text':outer.text}],'stop_reason':'end_turn' if outer.finish=='stop' else outer.finish,'stop_sequence':None,'usage':{'input_tokens':1,'output_tokens':1}}
                else:
                    data={'id':'fixture','object':'chat.completion','created':0,'model':body['model'],'choices':[{'index':0,'message':{'role':'assistant','content':outer.text},'finish_reason':outer.finish}],'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}
                if body.get('stream') and outer.status==200:
                    self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                    def emit(event):
                        prefix=('event: '+event['type']+'\n') if self.path.endswith('/messages') else ''
                        self.wfile.write((prefix+'data: '+json.dumps(event)+'\n\n').encode());self.wfile.flush()
                    try:
                        if self.path.endswith('/messages'):
                            emit({'type':'message_start','message':{'id':'msg_fixture','type':'message','role':'assistant','model':body['model'],'content':[],'stop_reason':None,'stop_sequence':None,'usage':{'input_tokens':1,'output_tokens':0}}})
                            emit({'type':'content_block_start','index':0,'content_block':{'type':'text','text':''}})
                        for chunk in [outer.text[i:i+7] for i in range(0,len(outer.text),7)]:
                            if self.path.endswith('/messages'):emit({'type':'content_block_delta','index':0,'delta':{'type':'text_delta','text':chunk}})
                            else:emit({'id':'fixture','object':'chat.completion.chunk','created':0,'model':body['model'],'choices':[{'index':0,'delta':{'content':chunk},'finish_reason':None}]})
                            time.sleep(getattr(outer,'chunk_delay',0))
                        if self.path.endswith('/messages'):
                            emit({'type':'content_block_stop','index':0})
                            emit({'type':'message_delta','delta':{'stop_reason':'end_turn' if outer.finish=='stop' else outer.finish,'stop_sequence':None},'usage':{'output_tokens':1}})
                            emit({'type':'message_stop'})
                        else:
                            emit({'id':'fixture','object':'chat.completion.chunk','created':0,'model':body['model'],'choices':[{'index':0,'delta':{},'finish_reason':outer.finish}]})
                            self.wfile.write(b'data: [DONE]\n\n')
                    except (BrokenPipeError,ConnectionResetError):pass
                    return
                raw=json.dumps(data).encode();self.send_response(outer.status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
                try:self.wfile.write(raw)
                except (BrokenPipeError,ConnectionResetError):pass
            def log_message(self,*args):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True
        if ssl_context:self.server.socket=ssl_context.wrap_socket(self.server.socket,server_side=True)
        self.url=f'{"https" if ssl_context else "http"}://127.0.0.1:{self.server.server_port}'
    def __enter__(self):
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.server.shutdown();self.server.server_close();self.thread.join()
