import json
import os
import pytest
from aivim.settings import Settings
from aivim.config_migrate import migrate
from aivim.ai_service import AIService
from aivim.ai_service import AIError
from provider_stub import ProviderStub
from test_ai_jobs import service


def test_explicit_json_precedence_and_validation(tmp_path):
    p=tmp_path/'explicit.json';p.write_text(json.dumps({'schema_version':1,'editor':{'tabstop':8},'ai':{'default_model':'claude','timeout':2}}))
    s=Settings(str(p));assert s.editor.tabstop==8 and s.ai.default_model=='claude'
    assert not s.set('tabstop',0) and s.editor.tabstop==8
    assert not s.set('undofile',True) and not s.file.undofile
    assert s.set('timeout',10)
    p.write_text('{"ai":{"api_key":"synthetic"}}')
    with pytest.raises(ValueError):Settings(str(p))
    p.write_text('{"file":{"undofile":true}}')
    with pytest.raises(ValueError):Settings(str(p))


def test_legacy_migration_preserves_original_and_credentials(tmp_path,monkeypatch):
    p=tmp_path/'legacy.ini';original='[General]\ndefault_model=claude\n[Anthropic]\napi_key=synthetic-legacy\nmodel=fixture-model\n';p.write_text(original)
    destination=tmp_path/'settings.json';migrate(p,destination)
    data=destination.read_text();assert 'synthetic-legacy' not in data and p.read_text()==original
    assert json.loads(data)['schema_version']==1 and Settings(str(destination)).ai.anthropic_model=='fixture-model'
    s=Settings(str(p));assert AIService(settings=s,credentials={'claude':'synthetic-explicit'}).credentials['claude']=='synthetic-explicit'
    monkeypatch.setenv('ANTHROPIC_API_KEY','synthetic-env')
    assert AIService(settings=s).credentials['claude']=='synthetic-env'
    with pytest.raises(ValueError):migrate(p,destination)


def test_opt_in_content_logs_permissions_retention_and_default_privacy(settings,tmp_path,caplog):
    settings.ai.content_log_dir=str(tmp_path/'logs');settings.ai.content_log_retention=2
    with ProviderStub() as stub:
        s=service(settings,stub);stub.text='SECRET_SYNTHETIC_RESPONSE'
        s.request('query',instruction='SECRET_SYNTHETIC_PROMPT')
        assert not (tmp_path/'logs').exists()
        assert 'SECRET_SYNTHETIC' not in caplog.text
        s.enable_debug_logging()
        (tmp_path/'logs').mkdir(mode=0o755)
        for _ in range(3):s.request('query',instruction='SECRET_SYNTHETIC_PROMPT')
        logs=list((tmp_path/'logs').glob('*.json'));assert len(logs)==2
        if os.name!='nt':
            assert all(p.stat().st_mode & 0o777 == 0o600 for p in logs)
            assert (tmp_path/'logs').stat().st_mode & 0o777 == 0o700
        else:
            import subprocess
            import shutil
            # Inspect the actual OS ACL rather than POSIX mode emulation.
            for path in [tmp_path/'logs',*logs]:
                script='(Get-Acl -LiteralPath $env:AIVIM_PERMISSION_FIXTURE).Access | Select-Object IdentityReference,FileSystemRights,AccessControlType | ConvertTo-Json -Compress'
                powershell=shutil.which('pwsh') or shutil.which('powershell')
                assert powershell, 'PowerShell is required for OS ACL verification'
                result=subprocess.run([powershell,'-NoProfile','-NonInteractive','-Command',script],env={**os.environ,'AIVIM_PERMISSION_FIXTURE':str(path)},capture_output=True,text=True)
                assert result.returncode==0,result.stderr
                acl=json.loads(result.stdout)
                assert isinstance(acl,dict) and acl['FileSystemRights']==2032127 and acl['AccessControlType']==0
        s.disable_debug_logging();s.request('query',instruction='MORE_SYNTHETIC');assert len(list((tmp_path/'logs').glob('*.json')))==2


def test_log_symlink_failure_is_safe_and_nonretryable(settings,tmp_path):
    outside=tmp_path/'outside';outside.mkdir();original_mode=outside.stat().st_mode
    path=tmp_path/'linked-logs';path.symlink_to(outside,target_is_directory=True)
    settings.ai.content_log_dir=str(path)
    with ProviderStub() as stub:
        s=service(settings,stub);s.enable_debug_logging()
        with pytest.raises(AIError) as error:s.request('query',instruction='SYNTHETIC')
        assert error.value.code=='LOG_FAILED' and not error.value.retryable
    assert not list(outside.iterdir()) and outside.stat().st_mode==original_mode


def test_effective_runtime_settings(editor):
    assert editor.command_handler.execute(':set shiftwidth=6')
    editor.handle_input('i');editor.handle_input(20);assert editor.buffer.get_content()==' '*6
    editor.handle_input(4);assert editor.buffer.get_content()=='';editor.handle_input(27)
    assert not editor.command_handler.execute(':set expandtab=invalid')
    editor.buffer.set_content('FOO foo');editor.settings.search.ignorecase=False;editor._start_search('foo')
    assert editor.search_results==[(0,4,3)]
    editor.settings.search.wrapscan=False;editor.cursor_x=4;editor._find_next_search_match()
    assert editor.cursor_x==4 and 'end' in editor.status_message
    assert editor.command_handler.execute(':set undolevels=2') and editor.history.max_history==2
