"""Disposable real stdio language server for protocol integration journeys."""
import json
import sys
root='';documents={}
def send(data):
 raw=json.dumps({'jsonrpc':'2.0',**data}).encode();sys.stdout.buffer.write(f'Content-Length: {len(raw)}\r\n\r\n'.encode()+raw);sys.stdout.buffer.flush()
while True:
 headers={}
 while True:
  line=sys.stdin.buffer.readline()
  if not line:sys.exit(0)
  if line==b'\r\n':break
  k,_,v=line.decode().partition(':');headers[k.lower()]=v.strip()
 data=json.loads(sys.stdin.buffer.read(int(headers['content-length'])))
 method=data.get('method');params=data.get('params',{})
 if method=='initialize':root=params['rootUri'];result={'capabilities':{'positionEncoding':'utf-16','textDocumentSync':1,'completionProvider':{},'definitionProvider':True,'renameProvider':True}}
 elif method=='textDocument/didOpen':
  uri=params['textDocument']['uri'];documents[uri]=params['textDocument']['text']
  send({'method':'textDocument/publishDiagnostics','params':{'uri':uri,'diagnostics':[{'range':{'start':{'line':0,'character':0},'end':{'line':0,'character':3}},'message':'fixture diagnostic','severity':2}]}});continue
 elif method=='textDocument/didChange':documents[params['textDocument']['uri']]=params['contentChanges'][0]['text'];continue
 elif method=='textDocument/completion':result=[{'label':'print','insertText':'print'}]
 elif method=='textDocument/definition':result=[{'uri':params['textDocument']['uri'],'range':{'start':{'line':0,'character':0},'end':{'line':0,'character':3}}}]
 elif method=='textDocument/rename':result={'changes':{params['textDocument']['uri']:[{'range':{'start':{'line':0,'character':0},'end':{'line':0,'character':3}},'newText':params['newName']}]}}
 else:result=None
 if 'id' in data:send({'id':data['id'],'result':result})
