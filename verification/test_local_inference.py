import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import multiprocessing
import threading
import time
import pytest
from aivim.ai_service import AIError
from aivim.local_worker import LocalWorker,verify_model
from aivim.model_download import download


def stuck_child(connection,config,system,prompt):time.sleep(5)
def healthy_child(connection,config,system,prompt):connection.send(('OK','synthetic lifecycle response'));connection.close()


def model(settings,tmp_path):
    path=tmp_path/'synthetic.gguf';raw=b'GGUFsynthetic-fixture-only';path.write_bytes(raw)
    settings.ai.local_model_path=str(path);settings.ai.local_model_sha256=hashlib.sha256(raw).hexdigest();return path


def test_integrity_and_child_lifecycle_limits(settings,tmp_path):
    path=model(settings,tmp_path)
    with pytest.raises(AIError):verify_model(path,'0'*64)
    before={p.pid for p in multiprocessing.active_children()}
    assert LocalWorker(settings.ai,healthy_child).complete('synthetic','synthetic',2)=='synthetic lifecycle response'
    start=time.monotonic()
    with pytest.raises(AIError) as error:LocalWorker(settings.ai,stuck_child).complete('synthetic','synthetic',.1)
    assert error.value.code=='TIMEOUT' and time.monotonic()-start<1
    assert {p.pid for p in multiprocessing.active_children()}==before
    cancelled=threading.Event();cancelled.set()
    with pytest.raises(AIError) as error:LocalWorker(settings.ai,stuck_child).complete('synthetic','synthetic',2,cancelled)
    assert error.value.code=='CANCELLED'


def test_real_native_boundary_without_optional_engine(settings,tmp_path):
    model(settings,tmp_path)
    with pytest.raises(AIError) as error:LocalWorker(settings.ai).complete('synthetic','synthetic',3)
    assert error.value.code in ('NOT_CONFIGURED','LOCAL_FAILED')


def test_integrity_failure_is_typed_and_cannot_reach_inference(settings,tmp_path):
    path=model(settings,tmp_path)
    settings.ai.local_model_sha256='0'*64
    with pytest.raises(AIError) as error:LocalWorker(settings.ai,healthy_child).complete('synthetic','synthetic',2)
    assert error.value.code=='MODEL_INTEGRITY'
    path.unlink()
    with pytest.raises(AIError) as error:LocalWorker(settings.ai,healthy_child).complete('synthetic','synthetic',2)
    assert error.value.code=='MODEL_INTEGRITY'


def test_download_resume_integrity_and_recovery(tmp_path):
    raw=b'GGUF'+b'synthetic'*100;digest=hashlib.sha256(raw).hexdigest();requests=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            offset=int(self.headers.get('Range','bytes=0-').split('=')[1].split('-')[0]);requests.append(offset)
            self.send_response(206 if offset else 200)
            if offset:self.send_header('Content-Range',f'bytes {offset}-{len(raw)-1}/{len(raw)}')
            self.send_header('Content-Length',str(len(raw)-offset));self.end_headers();self.wfile.write(raw[offset:])
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}/model';target=tmp_path/'model.gguf'
    try:
        import json
        target.with_suffix('.gguf.part').write_bytes(raw[:100]);target.with_suffix('.gguf.download.json').write_text(json.dumps({'url':url,'sha256':digest,'max_bytes':10000}))
        assert download(url,target,digest,max_bytes=10000,allow_loopback=True).read_bytes()==raw and requests==[100]
        assert not target.with_suffix('.gguf.part').exists()
        bad=tmp_path/'bad.gguf'
        with pytest.raises(AIError):download(url,bad,'0'*64,max_bytes=10000,allow_loopback=True)
        assert not bad.exists() and bad.with_suffix('.gguf.part').exists()
        with pytest.raises(ValueError):download(url,tmp_path/'small',digest,max_bytes=8,allow_loopback=True)
        with pytest.raises(ValueError):download(url,tmp_path/'insecure',digest)
    finally:server.shutdown();server.server_close();thread.join()
