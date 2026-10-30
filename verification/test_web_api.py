import json
import pytest
from aivim.web import create_app
from test_ai_jobs import service
from provider_stub import ProviderStub


def client(app):
    c=app.test_client();csrf=c.get('/api/capabilities').json['csrf_token'];return c,{'X-CSRF-Token':csrf}

def payload(**kw):
    data={'request_id':'synthetic-id','action':'explain','provider':'openai','model':'gpt-4.1-mini','code':'print(1)'};data.update(kw);return data


def test_request_local_provider_session_and_generation(settings):
    with ProviderStub() as stub:
        app=create_app(service(settings,stub));a,ha=client(app);b,hb=client(app)
        assert a.post('/api/set-model',json={'provider':'claude'},headers=ha).status_code==200
        assert a.get('/api/model-info').json['selection']['provider']=='claude'
        assert b.get('/api/model-info').json['selection']['provider']=='openai'
        stub.text=json.dumps({'code':'print(2)','explanation':'new'})
        result=a.post('/api/ai-assist',json=payload(action='generate',code='',specification='print two',provider='claude',model=settings.ai.anthropic_model),headers=ha)
        assert result.status_code==200 and result.json['provider']=='claude' and result.json['proposal']['content']=='print(2)'
        assert app.extensions['ai_service'].current_model=='openai'

@pytest.mark.parametrize('body,status',[(None,422),(['action'],422),({'code':None},422),({'action':12},422),({'request_id':None},422),({'query':[]},422)])
def test_invalid_shapes_are_json(settings,body,status):
    app=create_app();c,h=client(app)
    data=body if body is None or isinstance(body,list) else payload(**body)
    response=c.post('/api/ai-assist',data=json.dumps(data),content_type='application/json',headers=h)
    assert response.status_code==status and response.is_json


def test_size_content_type_security_and_unavailable(settings):
    app=create_app();c,h=client(app)
    assert c.post('/api/ai-assist',data='x',headers=h).status_code==415
    assert c.post('/api/ai-assist',data='{',content_type='application/json',headers=h).status_code==400
    assert c.post('/api/ai-assist',json=payload(code='界'*18000),headers=h).status_code==413
    assert c.post('/api/ai-assist',json=payload(query='x'*9000),headers=h).status_code==413
    assert c.post('/api/ai-assist',data='x'*140000,content_type='application/json',headers=h).status_code==413
    assert c.post('/api/set-model',json={'model':{}},headers=h).status_code==422
    assert c.post('/api/set-model',json={'provider':'claude'},headers=h).status_code==503
    assert c.post('/api/ai-assist',json=payload(),headers=h).status_code==503
    assert c.post('/api/ai-assist',json=payload()).status_code==403
    assert c.post('/api/ai-assist',json=payload(),headers={**h,'Origin':'https://attacker.invalid'}).status_code==403
    assert c.get('/health',headers={'Host':'attacker.invalid'}).status_code==403
    assert c.get('/health',environ_overrides={'REMOTE_ADDR':'192.0.2.1'}).status_code==403
    assert 'frame-ancestors' in c.get('/').headers['Content-Security-Policy']


def test_shared_authenticated_quota_and_permissions(settings,tmp_path):
    with ProviderStub() as stub:
        kwargs={'mode':'authenticated','allowed_hosts':['localhost'],'principals':{'synthetic-token':{'id':'alice','providers':['openai']}},'quota_path':tmp_path/'quota.sqlite','quota_limit':1,'secret_key':'fixture-signing-secret-only'}
        app=create_app(service(settings,stub),**kwargs);c=app.test_client();auth={'Authorization':'Bearer synthetic-token'}
        assert c.get('/health').status_code==401
        csrf=c.get('/api/capabilities',base_url='https://localhost',headers=auth).json['csrf_token'];h={**auth,'X-CSRF-Token':csrf}
        assert c.post('/api/ai-assist',base_url='https://localhost',json=payload(provider='claude',model=settings.ai.anthropic_model),headers=h).status_code==403
        assert c.post('/api/ai-assist',base_url='https://localhost',json=payload(),headers=h).status_code==200
        # Separate application process/factory shares the same quota state.
        other=create_app(service(settings,stub),**kwargs);d=other.test_client();h2={**auth,'X-CSRF-Token':d.get('/api/capabilities',base_url='https://localhost',headers=auth).json['csrf_token']}
        response=d.post('/api/ai-assist',base_url='https://localhost',json=payload(),headers=h2)
        assert response.status_code==429 and response.headers['Retry-After']=='60'


def test_provider_failures_are_not_success(settings):
    with ProviderStub() as stub:
        app=create_app(service(settings,stub));c,h=client(app);stub.status=429
        r=c.post('/api/ai-assist',json=payload(),headers=h);assert r.status_code==429 and r.json['error']['code']=='RATE_LIMITED'
        stub.status=200;stub.finish='length'
        r=c.post('/api/ai-assist',json=payload(),headers=h);assert r.status_code==502
        stub.finish='stop';stub.text='not structured'
        r=c.post('/api/ai-assist',json=payload(action='improve'),headers=h);assert r.status_code==502
