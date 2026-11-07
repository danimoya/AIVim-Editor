import asyncio
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
import pytest
from aivim.project import Project, ChangeSet
from aivim.runner import CommandRun
from aivim.tui import TerminalWorkspace
from aivim.project_widgets import ChangeReview
from provider_stub import ProviderStub
from test_ai_jobs import service
from test_tui_workspace import settle


def proposal(project,names,changes):return ChangeSet.parse(project,json.dumps({'files':changes}),project.snapshots(names))


def test_project_search_honors_ignores_and_bounds(tmp_path):
    (tmp_path/'sample.py').write_text('def greet(name):\n    return name\n')
    (tmp_path/'.env').write_text('greet=secret')
    (tmp_path/'node_modules').mkdir();(tmp_path/'node_modules'/'bad.js').write_text('greet')
    p=Project(tmp_path);matches=p.search('greet')
    assert [x['path'] for x in matches]==['sample.py'] and 'def greet' in matches[0]['text']
    for name in ['../escape','/etc/passwd','.env','node_modules/bad.js','private.key']:
        with pytest.raises(ValueError):p.path(name)
    if os.name!='nt':
        (tmp_path/'external').symlink_to('/tmp')
        with pytest.raises(ValueError):p.path('external/outside')


def test_per_hunk_apply_checkpoint_and_rollback(tmp_path):
    path=tmp_path/'app.py';path.write_text('first=1\nkeep=2\nlast=3\n')
    p=Project(tmp_path)
    plan=proposal(p,['app.py'],[{'path':'app.py','content':'first=10\nkeep=2\nlast=30\n'},{'path':'new.txt','content':'new file\n'}])
    assert len(plan.changes[0].hunks())==2
    checkpoint=plan.apply([(0,0),(1,0)])
    assert path.read_text()=='first=10\nkeep=2\nlast=3\n'
    assert (tmp_path/'new.txt').exists()
    plan.rollback(checkpoint)
    assert path.read_text()=='first=1\nkeep=2\nlast=3\n' and not (tmp_path/'new.txt').exists()


def test_changes_reject_stale_unapproved_and_outside_paths(tmp_path):
    path=tmp_path/'app.py';path.write_text('original')
    p=Project(tmp_path);snapshots=p.snapshots(['app.py'])
    plan=ChangeSet.parse(p,json.dumps({'files':[{'path':'app.py','content':'generated'}]}),snapshots)
    path.write_text('user changed')
    with pytest.raises(ValueError,match='externally'):plan.apply([(0,0)])
    assert path.read_text()=='user changed'
    for name in ['app.py','../escape']:
        with pytest.raises(ValueError):ChangeSet.parse(p,json.dumps({'files':[{'path':name,'content':'bad'}]}),{})


def test_partial_failure_compensates_and_rollback_refuses_newer_edits(tmp_path):
    for name in ['a.py','b.py']:(tmp_path/name).write_text('old\n')
    p=Project(tmp_path);plan=proposal(p,['a.py','b.py'],[{'path':n,'content':'new\n'} for n in ['a.py','b.py']])
    original=p.store.save;calls=0
    def failing(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==2:raise OSError('synthetic disk failure')
        return original(*args,**kwargs)
    with patch.object(p.store,'save',failing):
        with pytest.raises(OSError):plan.apply([(0,0),(1,0)])
    assert all((tmp_path/n).read_text()=='old\n' for n in ['a.py','b.py'])
    checkpoint=plan.apply([(0,0),(1,0)])
    (tmp_path/'b.py').write_text('manual edit')
    with pytest.raises(ValueError,match='newer edits'):plan.rollback(checkpoint)
    assert (tmp_path/'a.py').read_text()=='new\n' and (tmp_path/'b.py').read_text()=='manual edit'


def test_command_output_bounded_timeout_and_no_shell_expansion(tmp_path):
    run=CommandRun([sys.executable,'-c','print("$HOME")'],tmp_path)
    run.execute();assert run.returncode==0 and run.output.strip()=='$HOME'
    run=CommandRun([sys.executable,'-c','import time; time.sleep(10)'],tmp_path,timeout=.1)
    run.execute();assert run.finished.is_set() and run.cancelled.is_set()


def test_project_review_is_required_and_changes_can_roll_back(settings,tmp_path):
    async def journey(stub):
        path=tmp_path/'app.py';path.write_text('old=1\n')
        stub.text=json.dumps({'files':[{'path':'app.py','content':'new=2\n'}]})
        app=TerminalWorkspace(settings=settings,service=service(settings,stub),project=tmp_path)
        async with app.run_test(size=(110,40)) as pilot:
            app.source_file(str(path))
            app.action_project_generate();await pilot.pause()
            app.screen.dismiss('Update app');await settle(pilot,lambda:isinstance(app.screen,ChangeReview))
            assert path.read_text()=='old=1\n'
            await pilot.pause()
            await pilot.click('#changes-apply');await pilot.pause()
            assert path.read_text()=='new=2\n'
            app.action_project_rollback();await pilot.pause();app.screen.dismiss('rollback');await pilot.pause()
            assert path.read_text()=='old=1\n'
    with ProviderStub() as stub:asyncio.run(journey(stub))


def test_instruction_provenance_survives_manual_edit_and_restore(settings):
    from textual.widgets import TextArea
    async def journey(stub):
        stub.text=json.dumps({'code':'print(2)','explanation':'Generated'})
        app=TerminalWorkspace(settings=settings,service=service(settings,stub))
        async with app.run_test() as pilot:
            app.query_one('#instruction',TextArea).load_text('Print two')
            app.submit_action('generate');await settle(pilot,lambda:app.proposal is not None)
            app.action_accept();await pilot.pause()
            assert app.document.intents[0]['instruction']=='Print two'
            app.editor.replace('print(3)',(0,0),app.editor.document.end);await pilot.pause()
            b=app.document.intents[0]
            assert b['edited'] and app.document.content[b['start']:b['end']]=='print(3)'
            app.snapshot_session()
        restored=TerminalWorkspace(settings=settings,restore_session=True)
        async with restored.run_test():
            assert restored.document.intents[0]['instruction']=='Print two'
            assert restored.document.intents[0]['edited']
    with ProviderStub() as stub:asyncio.run(journey(stub))


def test_checkpoint_recovers_write_before_journal_confirmation(tmp_path):
    path=tmp_path/'app.py';path.write_text('old\n')
    project=Project(tmp_path);plan=proposal(project,['app.py'],[{'path':'app.py','content':'new\n'}])
    checkpoint=plan.apply([(0,0)])
    data=json.loads(checkpoint.read_text());data['state']='prepared';data['files'][0]['written']=False
    checkpoint.write_text(json.dumps(data))
    assert plan.rollback(checkpoint)==1 and path.read_text()=='old\n'


def test_project_cli_resolves_relative_filename_inside_root(settings,tmp_path,monkeypatch):
    import aivim.tui
    from aivim import run_editor
    captured={}
    class Workspace:
        def __init__(self,filename,**kwargs):captured.update(filename=filename,**kwargs)
        def run(self):captured['ran']=True
    monkeypatch.setattr(aivim.tui,'TerminalWorkspace',Workspace)
    monkeypatch.setattr(sys,'argv',['aivim','--project',str(tmp_path),'sample.py','--config',str(settings.config_path)])
    run_editor.main()
    assert captured['filename']==str(tmp_path/'sample.py') and captured['ran']
