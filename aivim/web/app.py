"""Single-user loopback companion, or explicit authenticated deployment mode."""
import hashlib
import hmac
import ipaddress
import json
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit
from flask import Flask, jsonify, request, render_template, session
from werkzeug.exceptions import HTTPException
from ..ai_service import AIService, AIError
from ..ai_jobs import AIJob
from ..proposals import parse_proposal


class SharedQuota:
    def __init__(self,path,limit=20,window=60):
        self.path=str(path);self.limit=limit;self.window=window
        with sqlite3.connect(self.path) as db:db.execute('CREATE TABLE IF NOT EXISTS quota (principal TEXT, bucket INTEGER, count INTEGER, PRIMARY KEY(principal,bucket))')
    def consume(self,principal):
        bucket=int(time.time())//self.window
        with sqlite3.connect(self.path,timeout=2) as db:
            db.execute('BEGIN IMMEDIATE');db.execute('DELETE FROM quota WHERE bucket < ?', (bucket-1,))
            count=db.execute('SELECT count FROM quota WHERE principal=? AND bucket=?',(principal,bucket)).fetchone()
            if count and count[0]>=self.limit:return False
            db.execute('INSERT INTO quota VALUES (?,?,1) ON CONFLICT(principal,bucket) DO UPDATE SET count=count+1',(principal,bucket));return True


def create_app(service=None, *, mode='loopback', allowed_hosts=None, principals=None, quota_path=None, quota_limit=20, secret_key=None):
    if mode not in ('loopback','authenticated'):raise ValueError('Invalid web mode')
    if mode=='authenticated' and (not principals or not quota_path or not secret_key or not allowed_hosts):raise ValueError('Authenticated mode requires explicit principals, shared quota database, signing key and allowed hosts')
    app=Flask(__name__);app.config.update(MAX_CONTENT_LENGTH=128*1024,SECRET_KEY=secret_key or secrets.token_hex(32),SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',SESSION_COOKIE_SECURE=mode=='authenticated')
    service=service if service is not None else AIService();app.extensions['ai_service']=service
    hosts=set(allowed_hosts or ['localhost','127.0.0.1','::1'])
    quotas=SharedQuota(quota_path,quota_limit) if quota_path else None
    local_calls=[];lock=threading.Lock();requests={}
    tokens={hashlib.sha256(token.encode()).hexdigest():value for token,value in (principals or {}).items()}
    def error(code,message,status,rid=None,retryable=False):
        response=jsonify({'request_id':rid,'error':{'code':code,'message':message,'retryable':retryable}})
        if status==429:response.headers['Retry-After']='60'
        return response,status
    @app.before_request
    def boundary():
        if urlsplit('http://'+request.host).hostname not in hosts:return error('FORBIDDEN_HOST','Host is not allowed',403)
        if mode=='loopback':
            try:local=ipaddress.ip_address(request.remote_addr or '').is_loopback
            except ValueError:local=False
            if not local:return error('FORBIDDEN','This companion accepts loopback clients only',403)
            request.principal={'id':'local','providers':list(service.models())}
        else:
            token=request.headers.get('Authorization','').removeprefix('Bearer ')
            request.principal=tokens.get(hashlib.sha256(token.encode()).hexdigest())
            if not request.principal:return error('UNAUTHORIZED','Authentication required',401)
        origin=request.headers.get('Origin')
        if origin and origin != request.host_url.rstrip('/'):return error('FORBIDDEN_ORIGIN','Origin is not allowed',403)
        if request.method=='POST':
            supplied=request.headers.get('X-CSRF-Token','');expected=session.get('csrf','')
            if not expected or not hmac.compare_digest(supplied,expected):return error('CSRF','Refresh this page before submitting',403)
    @app.after_request
    def headers(response):
        response.headers.update({'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store'})
        return response
    @app.errorhandler(HTTPException)
    def http_error(exc):return error('BODY_TOO_LARGE' if exc.code==413 else 'INVALID_REQUEST',exc.description,exc.code)
    def body():
        if not request.is_json:raise AIError('CONTENT_TYPE','Expected application/json')
        data=request.get_json()
        if not isinstance(data,dict):raise AIError('VALIDATION','Expected a JSON object')
        return data
    def limited(principal):
        if quotas:return quotas.consume(principal)
        with lock:
            now=time.monotonic();local_calls[:]=[x for x in local_calls if x>now-60]
            if len(local_calls)>=quota_limit:return False
            local_calls.append(now);return True
    @app.get('/')
    def index():return render_template('index.html')
    @app.get('/health')
    def health():return jsonify({'status':'ok'})
    @app.get('/api/capabilities')
    @app.get('/api/model-info')
    def capabilities():
        if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(32)
        available={p:v for p,v in service.capabilities().items() if p in request.principal['providers']}
        return jsonify({'providers':available,'selection':session.get('selection',{'provider':service.current_model,'model':service.models()[service.current_model]}),'csrf_token':session['csrf']})
    @app.post('/api/set-model')
    def select():
        try:
            data=body();p=data.get('provider',data.get('model'))
            if not isinstance(p,str):return error('VALIDATION','Provider must be a string',422)
            m=data.get('submodel') or service.models().get(p)
            if not isinstance(p,str) or p not in request.principal['providers'] or m!=service.models().get(p):return error('VALIDATION','Invalid provider/model',422)
            if not service.is_model_configured(p):return error('NOT_CONFIGURED','Provider is not configured',503)
            session['selection']={'provider':p,'model':m};return jsonify({'success':True,**session['selection']})
        except AIError as exc:return error(exc.code,str(exc),415 if exc.code=='CONTENT_TYPE' else 422)
    @app.post('/api/cancel')
    def cancel():
        try:data=body()
        except AIError as exc:return error(exc.code,str(exc),415 if exc.code=='CONTENT_TYPE' else 422)
        rid=data.get('request_id')
        if not isinstance(rid,str):return error('VALIDATION','Invalid request ID',422)
        with lock:
            entry=requests.get((request.principal['id'],rid))
            if entry:entry.set()
        return jsonify({'request_id':rid,'status':'cancelled'})
    @app.post('/api/ai-assist')
    def assist():
        rid=None;event=None;principal=request.principal['id']
        try:
            data=body()
            allowed={'request_id','action','provider','model','language','code','context','specification','query'}
            if set(data)-allowed:raise AIError('VALIDATION','Unknown request fields')
            for field in allowed:
                if field in data and not isinstance(data[field],str):raise AIError('VALIDATION',field+' must be a string')
            rid=data.get('request_id','')
            if not rid or len(rid)>128 or not all(c.isalnum() or c in '-_' for c in rid):raise AIError('VALIDATION','Invalid request ID')
            action=data.get('action');p=data.get('provider');m=data.get('model');code=data.get('code','');context=data.get('context','')
            if action not in ('explain','improve','generate','query','analyze'):raise AIError('VALIDATION','Invalid action')
            for field in ('code','context','specification','query'):
                if len(data.get(field,'').encode())>(50*1024 if field in ('code','context') else 8*1024):return error('BODY_TOO_LARGE',field+' exceeds byte limit',413,rid)
            instruction=data.get('specification' if action=='generate' else 'query','')
            if (action in ('generate','query') and not instruction.strip()) or (action not in ('generate','query') and not code.strip()):raise AIError('VALIDATION','Required action input is empty')
            if p not in request.principal['providers']:return error('FORBIDDEN_PROVIDER','Provider access denied',403,rid)
            if m!=service.models().get(p):raise AIError('INVALID_MODEL','Model is not configured')
            if not service.is_model_configured(p):raise AIError('NOT_CONFIGURED','Provider is not configured')
            if not limited(principal):return error('RATE_LIMITED','Request quota reached',429,rid,True)
            event=threading.Event()
            with lock:
                if (principal,rid) in requests:return error('DUPLICATE_REQUEST','Request ID is already running',409,rid)
                requests[(principal,rid)]=event
            result=service.request(action,code,context,instruction,provider=p,model=m,request_id=rid,cancel=event)
            response={'request_id':rid,'provider':result.provider,'model':result.model}
            if action in ('improve','generate'):
                ranges=((len(code),len(code)),) if action=='generate' else ((0,len(code)),)
                job=AIJob('browser',0,code,action,p,m,ranges,context,instruction,time.monotonic()+service.settings.ai.timeout,request_id=rid)
                proposal=parse_proposal(job,result)
                response.update({'type':'proposal','proposal':{'base_content':code,'content':proposal.content(),'diff':'\n'.join(proposal.diff()),'explanation':proposal.explanation}})
            else:response.update({'type':'text','result':result.text})
            return jsonify(response)
        except AIError as exc:
            status={'CONTENT_TYPE':415,'VALIDATION':422,'INVALID_MODEL':422,'NOT_CONFIGURED':503,'TIMEOUT':504,'RATE_LIMITED':429,'CANCELLED':409,'BUSY':429}.get(exc.code,502)
            return error(exc.code,str(exc),status,rid,exc.retryable)
        finally:
            if event:
                with lock:requests.pop((principal,rid),None)
    return app


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=5000);args=parser.parse_args()
    create_app().run(host='127.0.0.1',port=args.port,debug=False)
