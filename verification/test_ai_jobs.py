import json
import threading
import time
import pytest
from aivim.editor import Editor
from aivim.ai_service import AIService,AIError
from aivim.nlp_mode import NLPHandler
from provider_stub import ProviderStub


def wait(editor,timeout=3):
    deadline=time.monotonic()+timeout
    while editor.ai_processing and time.monotonic()<deadline:editor.poll_ai_events();time.sleep(.01)
    editor.poll_ai_events();assert not editor.ai_processing


def service(settings,stub):
    settings.ai.retry_on_error=False
    return AIService(settings=settings,credentials={'openai':'synthetic-only','claude':'synthetic-only'},endpoints={'openai':stub.url+'/v1','claude':stub.url})


def test_real_sdk_adapters_typed_errors(settings):
    with ProviderStub() as stub:
        s=service(settings,stub)
        assert s.request('query',instruction='synthetic',provider='openai').text=='plain response'
        assert s.request('query',instruction='synthetic',provider='claude').provider=='claude'
        assert [x[0] for x in stub.calls]==['/v1/chat/completions','/v1/messages']
        stub.status=429
        with pytest.raises(AIError) as err:s.request('query',instruction='synthetic')
        assert err.value.code=='RATE_LIMITED'
        stub.status=200;stub.finish='length'
        with pytest.raises(AIError) as err:s.request('query',instruction='synthetic')
        assert err.value.code=='INVALID_RESPONSE'


def test_wall_deadline_and_bounded_transport(settings):
    with ProviderStub() as stub:
        s=service(settings,stub);s._client('openai');settings.ai.timeout=.05;stub.delay=.3
        started=time.monotonic()
        with pytest.raises(AIError) as err:s.request('query',instruction='synthetic')
        assert err.value.code=='TIMEOUT' and time.monotonic()-started<.2


def test_document_ownership_switch_edit_close_cancel_and_newer(settings):
    with ProviderStub() as stub:
        stub.text=json.dumps({'code':'changed','explanation':'review'});stub.delay=.08
        e=Editor(settings=settings,ai_service=service(settings,stub));e.buffer.set_content('origin');e.buffer.mark_as_saved()
        assert e.ai_improve(0,0);e.create_tab('other');e.switch_to_tab(1);e.buffer.set_content('other');wait(e)
        assert e.buffer.get_content()=='other' and e.tabs[0].buffer.get_content()=='origin'
        assert e.command_handler.execute(':apply');assert e.tabs[0].buffer.get_content()=='changed' and e.buffer.get_content()=='other'
        e.switch_to_tab(0);assert e.ai_improve(0,0);e.buffer.set_content('new input');wait(e)
        assert e.buffer.get_content()=='new input' and 'STALE' in e.status_message
        e.buffer.mark_as_saved();assert e.ai_generate(0,'synthetic');e._cancel_ai_processing();time.sleep(.12);e.poll_ai_events()
        assert not e.pending_ai_action and len(e.tabs)==2
        assert e.ai_improve(0,0);assert e.close_current_tab('discard');time.sleep(.12);e.poll_ai_events()
        assert len(e.tabs)==1 and e.buffer.get_content()=='other'


def test_old_completion_does_not_reset_new_job(settings):
    class Controlled:
        current_model='openai'
        def models(self):return {'openai':'synthetic'}
        def request(self,*args,**kwargs):
            from aivim.ai_service import AIResult
            gate=first if args[3]=='first' else second;gate.wait(2)
            return AIResult('answer','openai','synthetic',kwargs['request_id'])
    first=threading.Event();second=threading.Event();e=Editor(settings=settings,ai_service=Controlled())
    e.ai_custom_query('first');e._cancel_ai_processing();e.ai_custom_query('second');new=e.current_job_id
    first.set();time.sleep(.03);e.poll_ai_events();assert e.ai_processing and e.current_job_id==new
    second.set();wait(e)


def test_nlp_scopes_and_invalid_response_preserve_inputs(settings):
    with ProviderStub() as stub:
        e=Editor(settings=settings,ai_service=service(settings,stub));e.buffer.set_content('def f():\n    #nlp return one\n    pass')
        e.create_tab('private');e.tabs[1].buffer.set_content('DO_NOT_SEND')
        e.nlp_handler=NLPHandler(e);assert not e.nlp_handler.live_mode_enabled
        a,b=e.line_offsets(1,1)[0];stub.text=json.dumps({'edits':[{'start':a,'end':b,'text':'    return 1'}]})
        e.nlp_handler.force_submit();wait(e)
        prompt=stub.calls[-1][1]['messages'][-1]['content'];assert 'DO_NOT_SEND' not in prompt
        assert e.command_handler.execute(':apply');assert e.buffer.get_content()=='def f():\n    return 1\n    pass'
        e.handle_input('u');assert '#nlp' in e.buffer.get_content()
        e.nlp_handler.select_context([e.tabs[1].document_id]);assert e.nlp_handler.context_preview()[0]['content']=='DO_NOT_SEND'
        stub.text='Error: fixture provider timed out';e.nlp_handler.force_submit();wait(e)
        assert '#nlp' in e.buffer.get_content() and e.pending_ai_action is None


def test_improvement_sends_selection_with_local_context_and_applies_exact_range(settings):
    with ProviderStub() as stub:
        e=Editor(settings=settings,ai_service=service(settings,stub));e.buffer.set_content('def f():\n    return 1\n# tail')
        stub.text=json.dumps({'code':'    return 2','explanation':'selection rewrite'})
        e.ai_improve(1,1);wait(e)
        prompt=json.loads(stub.calls[0][1]['messages'][-1]['content'])
        assert prompt['source']=='    return 1' and 'def f():' in prompt['context']
        assert e.command_handler.execute(':apply')
        assert e.buffer.get_content()=='def f():\n    return 2\n# tail'


def test_live_nlp_schedule_cannot_submit_another_document(editor):
    editor.settings.ai.nlp_live_mode=True;editor.mode='NLP';editor.buffer.set_content('#nlp original instruction')
    editor.nlp_handler=NLPHandler(editor);editor.handle_input('x')
    editor.nlp_handler._due=time.monotonic()-1
    index=editor.create_tab('other');editor.tabs[index].buffer.set_content('#nlp unrelated instruction');editor.switch_to_tab(index)
    editor.nlp_handler.tick()
    assert not editor.ai_processing and not editor.jobs.active
