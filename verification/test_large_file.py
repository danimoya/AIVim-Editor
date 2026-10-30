import json
import time


def test_measured_large_document_input(editor,tmp_path):
    text=('x'*99+'\n')*100000;editor.buffer.set_content(text);editor.buffer.mark_as_saved()
    start=time.monotonic();editor.handle_input('i')
    burst='Aé界xyz'*167
    for key in burst:editor.handle_input(key)
    editor.handle_input(27)
    elapsed=time.monotonic()-start
    assert editor.buffer.get_content()==burst+text and elapsed<3
    editor.handle_input('u');assert editor.buffer.get_content()==text and not editor.buffer.is_modified()
    editor.handle_input(18);assert editor.buffer.get_content()==burst+text
    (tmp_path/'large-file-metrics.json').write_text(json.dumps({'document_bytes':len(text.encode()),'input_characters':len(burst),'input_seconds':elapsed}))
