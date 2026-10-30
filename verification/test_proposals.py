import json
import pytest
from aivim.ai_jobs import AIJob
from aivim.ai_service import AIResult,AIError
from aivim.proposals import parse_proposal,validate_edits

@pytest.mark.parametrize('raw',[
 [{'start':-1,'end':1,'text':'x'}], [{'start':True,'end':1,'text':'x'}],
 [{'start':0,'end':99,'text':'x'}], [{'start':1,'end':2,'text':None}],
 [{'start':0,'end':2,'text':'x'},{'start':1,'end':3,'text':'y'}],
 [{'start':0,'end':0,'text':'x'},{'start':0,'end':0,'text':'y'}],
 [{'start':0,'end':1,'text':'x','extra':0}], 'arbitrary output'])
def test_invalid_edits_rejected_atomically(raw):
    with pytest.raises(AIError):validate_edits(raw,'abc',((0,3),))


def test_selection_scope_and_empty_replacement():
    assert validate_edits([{'start':1,'end':2,'text':''}],'abc',((1,2),))[0].text==''
    with pytest.raises(AIError):validate_edits([{'start':0,'end':2,'text':''}],'abc',((1,2),))


def test_generation_copy_contains_full_document_and_is_undoable(editor):
    source='def f():\n    return 1\n# tail';editor.buffer.set_content(source)
    a,b=editor.line_offsets(1,1)[0]
    job=AIJob(editor.current_tab.document_id,editor.buffer.revision,source,'improve','openai','synthetic',((a,b),),'','',999999999)
    result=AIResult(json.dumps({'code':'    return 2','explanation':'change'}),'openai','synthetic',job.request_id)
    proposal=parse_proposal(job,result);editor.pending_ai_action=proposal
    assert editor.command_handler.execute(':y')
    assert editor.buffer.get_content()=='def f():\n    return 2\n# tail' and editor.tabs[0].buffer.get_content()==source
    editor.switch_to_tab(0);editor.pending_ai_action=proposal;assert editor.command_handler.execute(':apply')
    editor.handle_input('u');assert editor.buffer.get_content()==source
    editor.handle_input(18);assert 'return 2' in editor.buffer.get_content()
    editor.pending_ai_action=proposal;assert not editor.command_handler.execute(':apply')
