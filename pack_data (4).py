"""Create small encrypted per-test bundles; never publish plaintext materials."""
import argparse
import base64
import hashlib
import io
import json
import secrets
import sys
import tomllib
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core import MAGIC, read_json


def main():
    config=ROOT/'.streamlit/secrets.toml'
    if not config.exists():
        key=base64.urlsafe_b64encode(AESGCM.generate_key(bit_length=256)).decode()
        password=secrets.token_urlsafe(12)
        config.write_text(f'BINGO_PASSWORD = "{password}"\nDATA_REPOSITORY = "jeniferanhngoc-lgtm/Bingo-eoai"\nDATA_RELEASE = "bingo-data-v1"\nDATA_KEY = "{key}"\n',encoding='utf-8')
    with config.open('rb') as f:
        settings=tomllib.load(f)
    key=base64.urlsafe_b64decode(settings['DATA_KEY'])
    c=read_json(ROOT/'data/catalog.json',{})
    sources=read_json(ROOT/'data/local_sources.json',{})
    output=ROOT/'data/packs'
    output.mkdir(exist_ok=True)
    parser=argparse.ArgumentParser()
    parser.add_argument('--test')
    parser.add_argument('--refresh',action='store_true',help='Create an immutable revision and update the catalog')
    args=parser.parse_args()
    count=0
    total=0
    handles={s:zipfile.ZipFile(p) for s,p in sources.items()}
    try:
        for test in c['tests']:
            if args.test and test['id']!=args.test:
                continue
            target=output/(test.get('pack') or test['id']+'.bingo')
            if target.exists() and not args.refresh:
                continue
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=2) as pack:
                for rid in test['resources']:
                    r=c['resources'][rid]
                    pack.writestr(rid+r['ext'],handles[r['source']].read(r['entry']))
            nonce=secrets.token_bytes(12)
            encrypted=MAGIC+nonce+AESGCM(key).encrypt(nonce,buf.getvalue(),MAGIC)
            if args.refresh:
                test['pack']=test['id']+'-'+hashlib.sha256(encrypted).hexdigest()[:12]+'.bingo'
                target=output/test['pack']
            target.write_bytes(encrypted)
            total+=len(encrypted)
            count+=1
            if count%10==0:
                print(f'Packed {count} tests',flush=True)
        if count:
            (ROOT/'data/catalog.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'Ready: {count} new encrypted bundles ({total/1e6:.1f} MB). Secrets saved locally, not printed.')
    finally:
        for handle in handles.values():
            handle.close()


if __name__=='__main__':
    main()
