import errno
import os
from pathlib import Path
import pytest
from aivim.file_store import FileStore


def test_dirty_documents_and_all_tab_exit(editor):
    editor.handle_input('i');editor.handle_input('x');editor.handle_input(27)
    editor.create_tab('clean');editor.switch_to_tab(1)
    assert not editor.quit() and not editor.should_quit
    editor.switch_to_tab(0);assert not editor.close_current_tab()
    assert len(editor.tabs)==2 and editor.buffer.get_content()=='x'
    assert editor.close_current_tab('discard')
    assert editor.quit()

@pytest.mark.parametrize('raw',[b'one\r\ntwo\r\n',b'one\ntwo',b'\xef\xbb\xbfcaf\xc3\xa9\n',b'a\rb'])
def test_properties_permissions_symlinks(editor,tmp_path,raw):
    target=tmp_path/'document';target.write_bytes(raw);target.chmod(0o751)
    expected_mode=target.stat().st_mode & 0o777
    link=tmp_path/'link';link.symlink_to(target)
    assert editor.load_file(str(link));assert editor.save_file()
    assert link.is_symlink() and target.read_bytes()==raw
    assert target.stat().st_mode & 0o777 == expected_mode


def test_external_conflict_and_saveas_failure(editor,tmp_path,monkeypatch):
    path=tmp_path/'original';path.write_text('initial');editor.load_file(str(path))
    editor.buffer.set_content('unsaved');path.write_text('external')
    state=(editor.filename,list(editor.history.versions),editor.buffer.get_content())
    assert not editor.command_handler.execute(':wq')
    assert not editor.should_quit and path.read_text()=='external'
    assert (editor.filename,list(editor.history.versions),editor.buffer.get_content())==state
    assert editor.buffer.is_modified()
    def full(*args,**kw):raise OSError(errno.ENOSPC,'synthetic disk full')
    monkeypatch.setattr(os,'replace',full)
    assert not editor.command_handler.execute(':saveas '+str(tmp_path/'new'))
    assert editor.filename==str(path) and editor.buffer.is_modified()
    assert not list(tmp_path.glob('.aivim-*'))


def test_new_target_conflict_encoding_backup_error(editor,tmp_path):
    p=tmp_path/'target';p.write_text('other')
    editor.buffer.set_content('mine')
    assert not editor.save_file(str(p)) and p.read_text()=='other'
    assert editor.save_file(str(p),force=True)
    editor.buffer.set_content('你好');editor.current_tab.file_identity=None;editor.settings.file.encoding='ascii'
    assert not editor.save_file(str(tmp_path/'ascii')) and editor.buffer.is_modified()
    editor.current_tab.file_identity=FileStore().load(str(p)).identity
    blocker=tmp_path/'not-a-directory';blocker.write_text('x')
    editor.settings.file.auto_backup=True;editor.settings.file.backup_dir=str(blocker)
    assert not editor.save_file() and p.read_text()=='mine'


def test_undo_to_saved_and_save_close(editor,tmp_path):
    p=tmp_path/'doc';p.write_text('');editor.load_file(str(p))
    for key in ['i','A','é',27]:editor.handle_input(key)
    assert editor.buffer.is_modified();editor.handle_input('u')
    assert editor.buffer.get_content()=='' and not editor.buffer.is_modified()
    editor.handle_input(18);assert editor.buffer.get_content()=='Aé' and editor.buffer.is_modified()
    editor.create_tab('second');assert editor.close_current_tab('save')
    assert p.read_text()=='Aé'


def test_symlink_retarget_conflict(editor,tmp_path):
    a=tmp_path/'a';b=tmp_path/'b';a.write_text('a');b.write_text('b');link=tmp_path/'link';link.symlink_to(a)
    editor.load_file(str(link));editor.buffer.set_content('edit');link.unlink();link.symlink_to(b)
    assert not editor.save_file() and b.read_text()=='b' and a.read_text()=='a'
