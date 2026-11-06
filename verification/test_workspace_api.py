import json
import threading
import pytest
from aivim.ai_service import AIError
from aivim.web import create_app
from provider_stub import ProviderStub
from test_ai_jobs import service
from test_web_api import client,payload

@pytest.mark.parametrize('provider',['openai','claude'])
def test_real_stream_deltas_and_complete_selection_proposal(settings,provider):
    with ProviderStub() as stub:
        stub.text=json.dumps({'code':'return 2','explanation':'Changed selection'})
        s=service(settings,stub);app=create_app(s);c,h=client(app)
        response=c.post('/api/ai-stream',json=payload(action='improve',provider=provider,model=s.models()[provider],code='界\nreturn 1\n# keep',selection_start=2,selection_end=10,context='selected reference'),headers=h)
        events=[json.loads(line) for line in response.data.splitlines() if line]
        assert events[0]['type']=='start'
        assert ''.join(e['data'] for e in events if e['type']=='delta')==stub.text
        final=events[-1]['data']['proposal'];assert final['content']=='界\nreturn 2\n# keep'
        assert final['replacement']=='return 2'
        prompt=json.loads(stub.calls[0][1]['messages'][-1]['content'])
        assert prompt['source']=='return 1' and prompt['context']=='selected reference'

@pytest.mark.parametrize('selection',[{'selection_start':-1},{'selection_end':900},{'selection_start':True},{'selection_start':4,'selection_end':2}])
def test_invalid_selection(settings,selection):
    with ProviderStub() as stub:
        c,h=client(create_app(service(settings,stub)))
        assert c.post('/api/ai-stream',json=payload(**selection),headers=h).status_code==422
        assert not stub.calls

def test_stream_partial_failure_never_proposes(settings):
    with ProviderStub() as stub:
        stub.text=json.dumps({'code':'incomplete','explanation':''});stub.finish='length'
        c,h=client(create_app(service(settings,stub)))
        r=c.post('/api/ai-stream',json=payload(action='improve'),headers=h)
        events=[json.loads(line) for line in r.data.splitlines() if line]
        assert events[-1]['type']=='error' and events[-1]['data']['code']=='INVALID_RESPONSE'
        assert not any(e['type']=='done' for e in events)

def test_stream_deadline_and_cancellation(settings):
    with ProviderStub() as stub:
        s=service(settings,stub);s._client('openai');settings.ai.timeout=.05;stub.delay=.3
        with pytest.raises(AIError) as exc:s.request('query',instruction='hello',on_delta=lambda x:None)
        assert exc.value.code=='TIMEOUT'
        cancelled=threading.Event();cancelled.set()
        with pytest.raises(AIError) as exc:s.request('query',instruction='hello',cancel=cancelled,on_delta=lambda x:None)
        assert exc.value.code=='CANCELLED'

def test_generation_does_not_forward_whole_document_and_stream_has_same_boundary(settings):
    with ProviderStub() as stub:
        stub.text=json.dumps({'code':'print(2)','explanation':'new'})
        c,h=client(create_app(service(settings,stub)))
        data=payload(action='generate',code='PRIVATE_DOCUMENT',specification='print two',context='',language='python')
        assert c.post('/api/ai-stream',json=data).status_code==403
        assert c.post('/api/ai-stream',json=data,headers={**h,'Origin':'https://attacker.invalid'}).status_code==403
        result=c.post('/api/ai-stream',json=data,headers=h)
        events=[json.loads(line) for line in result.data.splitlines() if line]
        assert events[-1]['type']=='done'
        prompt=json.loads(stub.calls[-1][1]['messages'][-1]['content'])
        assert prompt['source']=='' and prompt['context']==''
        assert 'python' in prompt['instruction'] and 'PRIVATE_DOCUMENT' not in json.dumps(prompt)
