"""Real Chromium journeys against a loopback Flask server and real SDK adapters."""
import json
from pathlib import Path
import threading
import time
import pytest
from playwright.sync_api import sync_playwright,expect
from werkzeug.serving import make_server
from aivim.web import create_app
from provider_stub import ProviderStub
from test_ai_jobs import service


@pytest.mark.browser
def test_browser_review_failure_cancel_copy_download_and_responsive(settings,tmp_path):
    with ProviderStub() as stub:
        app=create_app(service(settings,stub),quota_limit=100)
        server=make_server('127.0.0.1',0,app,threaded=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch();context=browser.new_context(permissions=['clipboard-read','clipboard-write']);page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(url);expect(page.locator('#status')).to_contain_text('Ready')
                page.select_option('#action','generate');page.fill('#instruction','Print two');stub.text=json.dumps({'code':'print(2)','explanation':'Review this code'})
                page.click('#submit');expect(page.locator('#status')).to_contain_text('Proposal ready')
                assert page.input_value('#code')==''
                page.click('#apply');assert page.input_value('#code')=='print(2)'
                page.click('#undo');assert page.input_value('#code')==''
                page.fill('#code','preserved input');page.select_option('#action','improve');stub.text=json.dumps({'code':'replacement','explanation':'review'})
                page.click('#submit');expect(page.locator('#apply')).to_be_enabled();page.fill('#code','new user input');expect(page.locator('#status')).to_contain_text('Stale')
                assert page.locator('#apply').is_disabled()
                page.click('#submit');expect(page.locator('#apply')).to_be_enabled();page.click('#reject');assert page.input_value('#code')=='new user input'
                stub.status=429;page.click('#submit');expect(page.locator('#status')).to_contain_text('rate limited');assert page.input_value('#code')=='new user input'
                stub.status=200;stub.text='<img src=x onerror="window.fixtureXSS=1"><script>window.fixtureXSS=2</script>'
                page.select_option('#action','explain');page.click('#submit');expect(page.locator('#status')).to_contain_text('Response ready')
                assert page.locator('#result img').count()==0 and page.evaluate('window.fixtureXSS') is None
                page.click('#copy');assert page.evaluate('navigator.clipboard.readText()')=='new user input'
                with page.expect_download() as download:page.click('#download')
                saved=tmp_path/'download.txt';download.value.save_as(saved);assert saved.read_text()=='new user input'
                stub.delay=.3;page.click('#submit');expect(page.locator('#cancel')).to_be_enabled();page.click('#cancel');expect(page.locator('#status')).to_contain_text('Cancelled');time.sleep(.4)
                assert page.input_value('#code')=='new user input' and 'Cancelled' in page.inner_text('#status')
                page.set_viewport_size({'width':375,'height':812});assert page.evaluate('document.body.scrollWidth <= window.innerWidth')
                # Large document interaction measurement, not an AI/provider request.
                page.once('dialog',lambda dialog:dialog.accept())
                large='line\n'*200000;start=time.monotonic();page.set_input_files('#upload',{'name':'synthetic-large.txt','mimeType':'text/plain','buffer':large.encode()});expect(page.locator('#status')).to_contain_text('Local file opened');assert page.input_value('#code')==large
                elapsed=time.monotonic()-start;assert elapsed<10
                (tmp_path/'browser-metrics.json').write_text(json.dumps({'document_bytes':len(large.encode()),'fill_read_seconds':elapsed,'viewport_width':375}))
                page.screenshot(path=str(tmp_path/'browser-mobile.png'),full_page=True)
                assert not errors;browser.close()
        finally:server.shutdown();server.server_close();thread.join()
