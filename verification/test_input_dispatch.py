import curses


def keys(editor,text):
    for k in text:editor.handle_input(k)


def test_burst_uppercase_unicode_and_undo(editor):
    text=('ABCé界xyz'*125)[:1000]
    keys(editor,'i'+text);editor.handle_input(27)
    assert editor.buffer.get_content()==text
    editor.handle_input('u');assert editor.buffer.get_content()==''
    editor.handle_input(18);assert editor.buffer.get_content()==text


def test_modal_delete_yank_paste_motions(editor):
    editor.buffer.set_content('one two\nthree\nfour');editor.buffer.mark_as_saved()
    keys(editor,'w');assert editor.cursor_x==4
    keys(editor,'b');assert editor.cursor_x==0
    keys(editor,'yyjp');assert editor.buffer.get_content()=='one two\nthree\none two\nfour'
    keys(editor,'u');assert editor.buffer.get_content()=='one two\nthree\nfour'
    keys(editor,'gg2dd');assert editor.buffer.get_content()=='four'
    keys(editor,'u');assert editor.buffer.get_content()=='one two\nthree\nfour'
    keys(editor,'A!');editor.handle_input(27);assert editor.buffer.get_line(editor.cursor_y).endswith('!')


def test_command_substitutions_regex_delimiter_and_confirmation(editor):
    editor.buffer.set_content('a a\na a');editor.buffer.mark_as_saved()
    keys(editor,':%s/a/b/g');editor.handle_input(10)
    assert editor.buffer.get_content()=='b b\nb b'
    assert editor.command_handler.execute(r':%s#b#c\#d#g')
    assert editor.buffer.get_content()=='c#d c#d\nc#d c#d'
    before=editor.buffer.get_content()
    assert not editor.command_handler.execute(':%s/[//g')
    assert editor.buffer.get_content()==before
    assert editor.command_handler.execute(':1s/c#d/z/gc')
    keys(editor,'ny');assert editor.buffer.get_line(0)=='c#d z'
    keys(editor,'u');assert editor.buffer.get_content()==before


def test_tab_aliases_reject_are_distinct(editor):
    editor.create_tab('second');assert editor.command_handler.execute(':nexttab')
    assert editor.current_tab_index==1
    editor.command_handler.execute(':prevtab');assert editor.current_tab_index==0
    editor.command_handler.execute(':n');assert editor.current_tab_index==1


def test_insert_paste_enter_backspace_and_settings(editor):
    editor.clipboard=['alpha','βeta'];keys(editor,'i');editor.handle_input(22)
    assert editor.buffer.get_content()=='alpha\nβeta'
    editor.handle_input(curses.KEY_BACKSPACE);assert editor.buffer.get_content()=='alpha\nβet'
    editor.settings.editor.tabstop=8;editor.handle_input(9)
    assert editor.cursor_x==8
    editor.handle_input(10);assert editor.buffer.get_content().endswith('\n')


def test_chunked_bracketed_paste_preserves_literal_commands_and_is_undoable(editor):
    from aivim.input_decoder import InputDecoder
    decoder=InputDecoder();text='dd :q!\n界\nA'
    for key in '\x1b[200~'+text+'\x1b[201~':
        for event in decoder.feed(key):editor.handle_input(event)
    assert editor.buffer.get_content()==text and not editor.should_quit
    editor.handle_input('u');assert editor.buffer.get_content()==''


def test_visual_range_substitution_through_real_dispatch(editor):
    editor.buffer.set_content('a a\na a\na a');editor.buffer.mark_as_saved()
    keys(editor,'vj:');keys(editor,'s/a/b/g');editor.handle_input(10)
    assert editor.buffer.get_content()=='b b\nb b\na a'
    editor.handle_input('u');assert editor.buffer.get_content()=='a a\na a\na a'
