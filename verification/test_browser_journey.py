"""Real Chromium workspace journeys through the real SDK streaming adapters."""
import json
import hashlib
from pathlib import Path
import threading
import time
import sys
import pytest
from playwright.sync_api import sync_playwright,expect
from werkzeug.serving import make_server
from aivim.web import create_app
from provider_stub import ProviderStub
from test_ai_jobs import service


def fill_document(page,text):
    editor=page.locator('.cm-content');editor.click();page.keyboard.press('Meta+a' if sys.platform=='darwin' else 'Control+a');page.keyboard.insert_text(text)

def document_text(page):
    # The Windows system clipboard represents text line endings as CRLF.
    page.click('#copy');return page.evaluate('navigator.clipboard.readText()').replace('\r\n','\n')

def select_all(page):
    page.locator('.cm-content').click();page.keyboard.press('Meta+a' if sys.platform=='darwin' else 'Control+a')

@pytest.fixture
def workspace(settings):
    with ProviderStub() as stub:
        app=create_app(service(settings,stub),quota_limit=100)
        server=make_server('127.0.0.1',0,app,threaded=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch();context=browser.new_context(permissions=['clipboard-read','clipboard-write']);page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}');expect(page.locator('#status')).to_contain_text('Ready')
                yield page,stub,errors
                assert not errors
                browser.close()
        finally:server.shutdown();server.server_close();thread.join()

@pytest.mark.browser
def test_browser_review_failure_cancel_copy_download_and_responsive(workspace,tmp_path):
    page,stub,errors=workspace
    page.select_option('#action','generate');page.fill('#instruction','Print two');stub.text=json.dumps({'code':'print(2)','explanation':'Review this code'})
    page.click('#submit');expect(page.locator('#status')).to_contain_text('Proposal ready')
    assert document_text(page)==''
    page.click('#apply');assert document_text(page)=='print(2)'
    page.click('#undo');assert document_text(page)==''
    fill_document(page,'preserved input');select_all(page);page.select_option('#action','improve');stub.text=json.dumps({'code':'replacement','explanation':'review'})
    page.click('#submit');expect(page.locator('#apply')).to_be_enabled();fill_document(page,'new user input');expect(page.locator('#status')).to_contain_text('Stale')
    assert page.locator('#apply').is_disabled()
    select_all(page);page.click('#submit');expect(page.locator('#apply')).to_be_enabled();page.click('#reject');assert document_text(page)=='new user input'
    stub.status=429;select_all(page);page.click('#submit');expect(page.locator('#status')).to_contain_text('rate limited');assert document_text(page)=='new user input'
    stub.status=200;stub.text='<img src=x onerror="window.fixtureXSS=1"><script>window.fixtureXSS=2</script>'
    page.select_option('#action','explain');select_all(page);page.click('#submit');expect(page.locator('#status')).to_contain_text('Response ready')
    assert page.locator('#result img').count()==0 and page.evaluate('window.fixtureXSS') is None
    assert document_text(page)=='new user input'
    with page.expect_download() as download:page.click('#download')
    saved=tmp_path/'download.txt';download.value.save_as(saved);assert saved.read_text()=='new user input'
    stub.delay=.3;select_all(page);page.click('#submit');expect(page.locator('#cancel')).to_be_enabled();page.click('#cancel');expect(page.locator('#status')).to_contain_text('Cancelled');page.wait_for_timeout(400)
    assert document_text(page)=='new user input'
    page.set_viewport_size({'width':375,'height':812});assert page.evaluate('document.body.scrollWidth <= window.innerWidth')
    large='line\n'*200000;start=time.monotonic();page.set_input_files('#upload',{'name':'synthetic-large.txt','mimeType':'text/plain','buffer':large.encode()});expect(page.locator('#status')).to_contain_text('Local file opened')
    # Digest comparison also avoids quadratic assertion diffs on repeated lines.
    assert hashlib.sha256(document_text(page).encode()).digest()==hashlib.sha256(large.encode()).digest()
    elapsed=time.monotonic()-start;assert elapsed<10
    (tmp_path/'browser-metrics.json').write_text(json.dumps({'document_bytes':len(large.encode()),'fill_read_seconds':elapsed,'viewport_width':375}))
    page.screenshot(path=str(tmp_path/'browser-mobile.png'),full_page=True)

@pytest.mark.browser
def test_sources_selection_unicode_vim_and_history(workspace,tmp_path):
    page,stub,_=workspace
    fill_document(page,'# 😀 keep\nreturn 1\n# tail')
    page.click('[data-tab=sources]')
    for name,content in [('Conventions','Return integers'),('Architecture','Pure functions'),('Private','DO_NOT_SEND')]:
        page.fill('#source-name',name);page.fill('#source-content',content);page.click('#source-form button')
    page.locator('.source-card').nth(2).locator('input').uncheck()
    page.click('[data-tab=editor]')
    # Select the second line through real keyboard selection.
    page.locator('.cm-content').click();page.keyboard.press('Meta+ArrowUp' if sys.platform=='darwin' else 'Control+Home');page.keyboard.press('ArrowDown');page.keyboard.press('Home');page.keyboard.press('Shift+End')
    stub.text=json.dumps({'code':'return 2','explanation':'Use two'})
    page.fill('#instruction','Use two instead');page.click('[data-action=improve]');expect(page.locator('#apply')).to_be_enabled()
    sent=json.loads(stub.calls[-1][1]['messages'][-1]['content']);assert sent['source']=='return 1'
    assert 'Return integers' in sent['context'] and 'Pure functions' in sent['context'] and 'DO_NOT_SEND' not in sent['context']
    assert sent['instruction']=='Use two instead'
    page.click('#apply');assert document_text(page)=='# 😀 keep\nreturn 2\n# tail'
    page.click('#undo');assert document_text(page)=='# 😀 keep\nreturn 1\n# tail'
    page.click('#vim');page.locator('.cm-content').click();page.keyboard.press('Escape');page.keyboard.type('ggdd')
    assert document_text(page)=='return 1\n# tail'
    page.locator('.cm-content').click();page.keyboard.type('u');assert document_text(page)=='# 😀 keep\nreturn 1\n# tail'
    page.click('[data-tab=history]');expect(page.locator('#history-list')).to_contain_text('Accepted');expect(page.locator('#history-list')).to_contain_text('Use two instead')
    page.click('[data-tab=editor]');page.screenshot(path=str(tmp_path/'workspace-desktop.png'),full_page=True)

@pytest.mark.browser
def test_live_blocks_queue_stream_edit_preservation_and_undo(workspace):
    page,stub,_=workspace
    stub.text=json.dumps({'code':'print(2)','explanation':'Generated'});stub.chunk_delay=.04
    page.check('#live');page.check('#auto-apply');page.locator('.cm-content').click()
    page.keyboard.type('print two');page.keyboard.press('Enter');page.wait_for_timeout(150);assert not stub.calls
    page.keyboard.type('on the console');page.keyboard.press('Enter');page.wait_for_timeout(150);assert not stub.calls
    page.keyboard.press('Enter');expect(page.locator('#result')).to_contain_text('print',timeout=5000)
    # Keep creating a new block while the first streams.
    page.keyboard.type('print two again');page.keyboard.press('Enter');page.keyboard.press('Enter')
    expect(page.locator('#status')).to_contain_text('accepted',timeout=10000)
    page.wait_for_function("document.querySelector('#cancel').disabled && document.querySelector('#result').textContent.includes('Generated')",timeout=10000)
    # Wait for both provider calls and both replacements.
    expect(page.locator('.cm-content')).not_to_contain_text('again',timeout=10000)
    assert len(stub.calls)==2
    text=document_text(page);assert text.count('print(2)')==2 and 'print two' not in text
    page.click('#undo');assert 'print two again' in document_text(page)
    # Re-arm at a fresh document, then edit the submitted instruction mid-stream.
    page.click('#new-document');page.uncheck('#live');page.check('#live');page.locator('.cm-content').click()
    page.keyboard.type('print two');page.keyboard.press('Enter');page.keyboard.press('Enter')
    expect(page.locator('#cancel')).to_be_enabled();page.keyboard.press('Meta+ArrowUp' if sys.platform=='darwin' else 'Control+Home');page.keyboard.type('changed ')
    expect(page.locator('#status')).to_contain_text('Stale',timeout=10000)
    assert 'changed print two' in document_text(page) and 'print(2)' not in document_text(page)

@pytest.mark.browser
def test_request_stays_with_original_document_and_visual_selection(workspace):
    page,stub,_=workspace
    fill_document(page,'return 1');select_all(page)
    stub.text=json.dumps({'code':'return 2','explanation':'Updated'});stub.delay=.2
    page.click('[data-action=improve]');page.click('#new-document');fill_document(page,'unrelated document')
    expect(page.locator('#apply')).to_be_enabled();page.click('#apply')
    assert document_text(page)=='unrelated document'
    page.locator('#documents button').first.click();assert document_text(page)=='return 2'
    page.click('#undo');assert document_text(page)=='return 1'
    stub.delay=0;stub.text='Explanation'
    page.check('#vim');page.locator('.cm-content').click();page.keyboard.press('Escape');page.keyboard.type('ggV')
    page.click('[data-action=explain]');expect(page.locator('#status')).to_contain_text('Response ready')
    sent=json.loads(stub.calls[-1][1]['messages'][-1]['content']);assert sent['source']=='return 1'
