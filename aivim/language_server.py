"""Opt-in stdio LSP client: bounded JSON-RPC, UTF-16 positions, no server-driven execution."""
from __future__ import annotations
import itertools
import json
from pathlib import Path
import queue
import subprocess
import threading


def utf16_position(text, location):
    row,col=location;lines=text.split('\n');row=min(row,len(lines)-1)
    return {'line':row,'character':len(lines[row][:col].encode('utf-16-le'))//2}


def character_location(text, position):
    lines=text.split('\n');row=max(0,min(position['line'],len(lines)-1))
    units=position['character'];col=0;used=0
    for char in lines[row]:
        width=len(char.encode('utf-16-le'))//2
        if used+width>units:break
        used+=width;col+=1
    return row,col


class LanguageClient:
    def __init__(self, argv, root):
        self.root=Path(root).resolve();self.pending={};self.ids=itertools.count(1)
        self.notifications=queue.Queue(maxsize=256);self.lock=threading.Lock();self.closed=False
        self.process=subprocess.Popen(argv,cwd=self.root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        threading.Thread(target=self._read,daemon=True).start()
        try:
            self.capabilities=self.request('initialize',{'processId':None,'rootUri':self.root.as_uri(),
                'capabilities':{'general':{'positionEncodings':['utf-16']},'textDocument':{'completion':{'completionItem':{'snippetSupport':False}}}},
                'workspaceFolders':[{'uri':self.root.as_uri(),'name':self.root.name}]})
            self.notify('initialized',{})
        except Exception:self.close();raise
        if not isinstance(self.capabilities,dict) or not isinstance(self.capabilities.get('capabilities',{}),dict):
            self.close();raise ValueError('Invalid language-server initialize response.')
        encoding=self.capabilities.get('capabilities',{}).get('positionEncoding','utf-16')
        if encoding!='utf-16':self.close();raise ValueError('Server must support UTF-16 positions.')

    def _send(self, data):
        raw=json.dumps({'jsonrpc':'2.0',**data}).encode()
        if len(raw)>2*1024*1024:raise ValueError('LSP message exceeds 2 MiB.')
        with self.lock:
            if self.closed:raise ValueError('Language server disconnected.')
            self.process.stdin.write(f'Content-Length: {len(raw)}\r\n\r\n'.encode()+raw);self.process.stdin.flush()

    def _read(self):
        try:
            while True:
                headers={}
                for _ in range(20):
                    line=self.process.stdout.readline(4096)
                    if not line:return
                    if line==b'\r\n':break
                    key,_,value=line.decode('ascii').partition(':');headers[key.lower()]=value.strip()
                length=int(headers.get('content-length','0'))
                if not 0<length<=2*1024*1024:raise ValueError('Invalid LSP frame size.')
                raw=self.process.stdout.read(length)
                if len(raw)!=length:return
                data=json.loads(raw)
                if 'id' in data and 'method' not in data:
                    waiting=self.pending.get(data['id'])
                    if waiting:
                        try:waiting.put_nowait(data)
                        except queue.Full:pass
                elif 'id' in data:
                    # Never apply a server workspace edit or execute its commands implicitly.
                    method=data['method'];result=None
                    if method=='workspace/configuration':result=[{} for _ in data.get('params',{}).get('items',[])]
                    elif method=='workspace/applyEdit':result={'applied':False,'failureReason':'Use reviewed rename/change sets.'}
                    self._send({'id':data['id'],'result':result})
                else:
                    try:self.notifications.put_nowait(data)
                    except queue.Full:pass
        except (OSError,ValueError,TypeError,KeyError):pass
        finally:
            self.closed=True
            for waiting in list(self.pending.values()):
                try:waiting.put_nowait({'error':{'message':'Language server disconnected.'}})
                except queue.Full:pass

    def notify(self, method, params):self._send({'method':method,'params':params})
    def request(self, method, params, timeout=10):
        rid=next(self.ids);waiting=queue.Queue(maxsize=1);self.pending[rid]=waiting
        try:
            self._send({'id':rid,'method':method,'params':params})
            try:result=waiting.get(timeout=timeout)
            except queue.Empty:raise ValueError('Language server request timed out.') from None
            if 'error' in result:raise ValueError(result['error'].get('message','Language server request failed.'))
            return result.get('result')
        finally:self.pending.pop(rid,None)

    def open_document(self,path,text,language,version=1):
        uri=Path(path).resolve().as_uri()
        self.notify('textDocument/didOpen',{'textDocument':{'uri':uri,'languageId':language or 'plaintext','version':version,'text':text}})
        return uri

    def change_document(self,uri,text,version):
        self.notify('textDocument/didChange',{'textDocument':{'uri':uri,'version':version},'contentChanges':[{'text':text}]})

    def close(self):
        if getattr(self,'process',None) is None:return
        self.closed=True
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2)
