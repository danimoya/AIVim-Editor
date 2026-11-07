"""User journeys for 2.1 prompts, file mentions, compact controls and effects."""
import asyncio
import json
from pathlib import Path
import time
from textual.widgets import Button, Checkbox, OptionList, Select, TextArea
from aivim.tui import TerminalWorkspace
from aivim.interface_widgets import ProjectPrompt, SettingsDialog, MatrixLoading
from aivim.project_widgets import ChangeReview
from aivim.languages import infer_language
from provider_stub import ProviderStub
from test_ai_jobs import service
from test_tui_workspace import settle


def test_project_prompt_multiline_mentions_use_exact_selected_files(settings,tmp_path):
    async def journey(stub):
        a=tmp_path/'app.py';a.write_text('value=1\n')
        b=tmp_path/'recent notes.md';b.write_text('Recent reference text')
        stub.text=json.dumps({'files':[{'path':'app.py','content':'value=2\n'}]})
        app=TerminalWorkspace(settings=settings,service=service(settings,stub),project=tmp_path)
        async with app.run_test(size=(110,40)) as pilot:
            await app.open_document(str(a));await app.open_document(str(b))
            closed=app.current_id;await app.remove_document(closed)
            app.action_project_generate();await pilot.pause()
            assert isinstance(app.screen,ProjectPrompt)
            area=app.screen.query_one('#project-instruction',TextArea)
            assert area.content_region.height==5 and area.region.width>70
            await pilot.press('@','a');await pilot.pause()
            assert app.screen.matches[0].path==str(a)
            await pilot.press('tab');assert '@app.py ' in area.text
            await pilot.press('enter',*'Use two.','enter',*'Keep other files unchanged.')
            assert area.text.count('\n')==2 and not stub.calls
            await pilot.press('ctrl+enter')
            await settle(pilot,lambda:isinstance(app.screen,ChangeReview))
            sent=json.loads(stub.calls[0][1]['messages'][-1]['content'])
            context=json.loads(sent['context'])
            assert context['files']==[{'path':'app.py','content':'value=1\n'}]
            assert '\nUse two.\n' in sent['instruction']
            assert a.read_text()=='value=1\n'
    with ProviderStub() as stub:asyncio.run(journey(stub))


def test_recent_mentions_spaces_mouse_selection_and_scrolling(settings,tmp_path):
    async def journey():
        path=tmp_path/'recent notes.md';path.write_text('reference')
        app=TerminalWorkspace(settings=settings,project=tmp_path)
        async with app.run_test(size=(90,30)) as pilot:
            await app.open_document(str(path));await app.remove_document(app.current_id)
            app.action_project_generate();await pilot.pause()
            area=app.screen.query_one('#project-instruction',TextArea)
            await pilot.press(*'@recent');await pilot.pause()
            assert app.screen.matches[0].origin=='Recent'
            await pilot.click('#file-completions',offset=(3,0));await pilot.pause()
            assert '@"recent notes.md" ' in area.text
            area.insert('\n'.join('line '+str(n) for n in range(12)));await pilot.pause()
            assert area.content_region.height==5 and area.max_scroll_y>0
    asyncio.run(journey())


def test_clickable_tabs_and_rotating_mode_keep_two_rows(settings,tmp_path):
    async def journey():
        app=TerminalWorkspace(settings=settings)
        async with app.run_test(size=(80,24)) as pilot:
            first=app.current_id
            second=await app.new_document('other.sh','echo hello')
            await pilot.pause()
            await pilot.click('#buffer-'+first);await pilot.pause();assert app.current_id==first
            await pilot.click('#buffer-'+second.id);await pilot.pause();assert app.current_id==second.id
            assert app.editor.region.height==22
            for live,auto in [(True,False),(True,True),(False,False)]:
                await pilot.click('#live-mode');await pilot.pause()
                assert app.query_one('#live',Checkbox).value==live
                assert app.query_one('#auto',Checkbox).value==auto
            assert app.editor.region.height==22
    asyncio.run(journey())


def test_ai_fullscreen_restores_pin_and_esc_does_not_consume_editor_escape(settings):
    async def journey():
        app=TerminalWorkspace(settings=settings)
        async with app.run_test(size=(110,36)) as pilot:
            await pilot.press('alt+a');await pilot.pause();await pilot.click('#pin-ai');await pilot.pause()
            previous=app.editor.region.width
            result=app.query_one('#result',TextArea);result.load_text('\n'.join('Response '+str(i) for i in range(100)))
            await pilot.click('#fullscreen-ai');await pilot.pause()
            assert app.ai_fullscreen and app.query_one('#ai-panel').region.width==110
            assert result.region.height>=28 and result.read_only
            assert not app.query_one('#instruction').display
            result.scroll_to(y=30,animate=False);await pilot.pause()
            before_scroll=result.scroll_y
            app.update_ai_response(result.text+'\nMore streamed text')
            await pilot.pause();assert result.scroll_y==before_scroll
            await pilot.press('escape');await pilot.pause()
            assert not app.ai_fullscreen and app.sidebar_pinned and app.editor.region.width==previous
            assert result.text.startswith('Response 0')
            app.collapse_ai();await pilot.press('i','x','escape');await pilot.pause()
            assert app.editor.mode=='NORMAL' and app.editor.text=='x'
    asyncio.run(journey())


def test_settings_persist_and_reduced_motion_disables_effects(settings):
    async def journey():
        app=TerminalWorkspace(settings=settings)
        async with app.run_test(size=(100,34)) as pilot:
            app.action_settings();await pilot.pause();assert isinstance(app.screen,SettingsDialog)
            app.screen.query_one('#setting-vim',Checkbox).value=False
            app.screen.query_one('#setting-numbers',Checkbox).value=False
            app.screen.query_one('#setting-indent',Select).value='2'
            app.screen.query_one('#setting-ai-animation',Select).value='matrix'
            app.screen.query_one('#setting-startup',Select).value='matrix'
            app.screen.query_one('#setting-streaming',Select).value='matrix'
            button=app.screen.query_one('#settings-save',Button);button.scroll_visible(animate=False)
            await pilot.pause();await pilot.click('#settings-save');await pilot.pause()
            assert app.streaming_effect=='matrix' and app.editor.indent_width==2 and not app.vim_enabled
            values=app.settings_values();values['reduce_motion']=True;app.apply_user_settings(values)
            assert not app.writing_effect
        restored=TerminalWorkspace(settings=settings)
        async with restored.run_test():
            assert restored.streaming_effect=='matrix' and restored.reduce_motion and not restored.writing_effect
            assert not restored.vim_enabled and restored.editor.indent_width==2
    asyncio.run(journey())


def test_language_inference_sources_and_explicit_intent():
    assert infer_language('task.sh',prompt='Print hello')=='bash'
    assert infer_language('task.py',prompt='Write a Bash script')=='bash'
    assert infer_language('untitled-1.py',prompt='Print hello',opened=[('build.sh','',True)])=='bash'
    assert infer_language('notes',content='#!/usr/bin/env python3\nprint(1)')=='python'
    assert infer_language('script',content='echo hello')=='bash'
    assert infer_language('task.js',prompt='Convert JavaScript to Python')=='python'
    assert infer_language('types.ts')=='typescript'


def test_request_language_is_frozen_from_open_project_files(settings,tmp_path):
    async def journey(stub):
        stub.text=json.dumps({'code':'echo hello','explanation':'Bash'})
        app=TerminalWorkspace(settings=settings,service=service(settings,stub),project=tmp_path)
        async with app.run_test() as pilot:
            await app.new_document('build.sh','echo old')
            doc=await app.new_document()
            request=app.make_request(doc,0,0,'generate','Print hello',live=True)
            assert request.language=='bash'
            app.start_request(request)
            await settle(pilot,lambda:app.proposal is not None)
            prompt=json.loads(stub.calls[0][1]['messages'][-1]['content'])
            assert prompt['instruction'].startswith('Requested output language: bash')
    with ProviderStub() as stub:asyncio.run(journey(stub))


def test_startup_ascii_effect_and_skip_keeps_first_key(settings):
    async def journey():
        app=TerminalWorkspace(settings=settings,show_startup=True)
        async with app.run_test(size=(80,24)) as pilot:
            await settle(pilot,lambda:isinstance(app.screen,MatrixLoading))
            assert app.screen.query_one('#startup-matrix').render()
            await pilot.press('i');await pilot.pause()
            assert not isinstance(app.screen,MatrixLoading) and app.editor.mode=='INSERT'
    asyncio.run(journey())


def test_startup_does_not_reorder_a_burst_of_typing(settings):
    from textual import events
    async def journey():
        app=TerminalWorkspace(settings=settings,show_startup=True)
        async with app.run_test() as pilot:
            await settle(pilot,lambda:isinstance(app.screen,MatrixLoading))
            for char in 'ihello': app.post_message(events.Key(char,char))
            await pilot.pause(.2)
            assert app.editor.text=='hello' and app.editor.mode=='INSERT'
    asyncio.run(journey())


def test_unsaved_mentioned_buffer_is_read_only_context(settings,tmp_path):
    async def journey(stub):
        target=tmp_path/'app.py';target.write_text('value=1\n')
        stub.text=json.dumps({'files':[{'path':'new.py','content':'value=2\n'}]})
        app=TerminalWorkspace(settings=settings,service=service(settings,stub),project=tmp_path)
        async with app.run_test(size=(110,40)) as pilot:
            await app.open_document(str(target));app.editor.insert('# unsaved\n');await pilot.pause()
            app.action_project_generate();await pilot.pause()
            area=app.screen.query_one('#project-instruction',TextArea)
            area.insert('Use @app.py as reference and create new.py.')
            await pilot.press('ctrl+enter')
            await settle(pilot,lambda:isinstance(app.screen,ChangeReview))
            sent=json.loads(stub.calls[0][1]['messages'][-1]['content']);context=json.loads(sent['context'])
            assert not context['files']
            assert '# unsaved' in context['references'][0]['content']
            assert context['references'][0]['read_only'] and context['references'][0]['unsaved']
            assert target.read_text()=='value=1\n'
    with ProviderStub() as stub:asyncio.run(journey(stub))


def test_generation_activity_animates_then_clears(settings):
    async def journey(stub):
        stub.stream_gate.clear();stub.text=json.dumps({'code':'print(1)','explanation':'Generated'})
        app=TerminalWorkspace(settings=settings,service=service(settings,stub))
        async with app.run_test() as pilot:
            app.query_one('#instruction',TextArea).load_text('Print one')
            app.submit_action('generate');await pilot.pause(.1)
            first=app._activity_value;assert first
            await pilot.pause(.2);assert app._activity_value and app._activity_value!=first
            stub.stream_gate.set();await settle(pilot,lambda:app.proposal is not None)
            await pilot.pause(.2);assert app._activity_value==''
    with ProviderStub() as stub:asyncio.run(journey(stub))


def test_mentions_disambiguate_saved_and_unsaved_names_and_punctuation(tmp_path):
    from aivim.file_mentions import file_candidates,referenced_files
    from aivim.tui_model import Document
    from aivim.file_store import FileStore
    path=tmp_path/'same.py';path.write_text('saved')
    saved=Document('same.py','saved','saved',FileStore().load(path).identity)
    draft=Document('same.py','unsaved')
    candidates=file_candidates([draft,saved],[],tmp_path)
    assert candidates[0].token!=candidates[1].token
    assert referenced_files(candidates[0].token,candidates)==[candidates[0]]
    assert referenced_files('@same.py:',candidates)==[candidates[1]]
