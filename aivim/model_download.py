"""Explicit recoverable downloads; no bundled weights or automatic model fetching."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import requests
from .local_worker import verify_model


def download(url,destination,sha256,*,max_bytes=16*1024**3,allow_loopback=False):
    parsed=urlsplit(url)
    if parsed.scheme!='https' and not (allow_loopback and parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost')):raise ValueError('Model downloads require HTTPS')
    if len(sha256)!=64 or any(c not in '0123456789abcdef' for c in sha256.lower()):raise ValueError('Expected SHA-256 digest')
    target=Path(destination).expanduser();target.parent.mkdir(parents=True,exist_ok=True)
    part=target.with_name(target.name+'.part');meta=target.with_name(target.name+'.download.json')
    if target.exists():verify_model(target,sha256,max_bytes);return target
    expected={'url':url,'sha256':sha256,'max_bytes':max_bytes}
    if meta.exists() and json.loads(meta.read_text())!=expected:raise ValueError('Existing partial download belongs to a different model')
    if part.exists() and not meta.exists():raise ValueError('Unidentified partial download; select a new destination')
    meta.write_text(json.dumps(expected));offset=part.stat().st_size if part.exists() else 0
    headers={'Range':f'bytes={offset}-'} if offset else {}
    with requests.get(url,headers=headers,stream=True,timeout=(10,30),allow_redirects=False) as response:
        if response.status_code==416 and offset:
            verify_model(part,sha256,max_bytes);os.replace(part,target);meta.unlink();return target
        response.raise_for_status()
        if response.status_code not in (200,206):raise ValueError('Unexpected download response')
        if response.status_code==206:
            range_header=response.headers.get('Content-Range','')
            if not range_header.startswith(f'bytes {offset}-'):raise ValueError('Server returned an invalid resume range')
        else:offset=0
        if int(response.headers.get('Content-Length','0'))+offset>max_bytes:raise ValueError('Model exceeds configured size limit')
        fd=os.open(part,os.O_CREAT|os.O_WRONLY|(os.O_APPEND if offset else os.O_TRUNC),0o600)
        with os.fdopen(fd,'ab' if offset else 'wb') as f:
            size=offset
            for chunk in response.iter_content(1024*1024):
                size+=len(chunk)
                if size>max_bytes:raise ValueError('Model exceeds configured size limit')
                f.write(chunk)
            f.flush();os.fsync(f.fileno())
    verify_model(part,sha256,max_bytes)
    os.replace(part,target);meta.unlink();return target


def main():
    parser=argparse.ArgumentParser();parser.add_argument('url');parser.add_argument('destination');parser.add_argument('--sha256',required=True);parser.add_argument('--max-bytes',type=int,default=16*1024**3);args=parser.parse_args()
    download(args.url,args.destination,args.sha256,max_bytes=args.max_bytes)
if __name__=='__main__':main()
