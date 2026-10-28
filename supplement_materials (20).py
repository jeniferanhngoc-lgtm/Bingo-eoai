"""Merge owner-supplied supplemental ZIPs; make versioned encrypted bundles."""
import base64
import hashlib
import io
import json
import re
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core import MAGIC, read_json, write_json
from import_materials import parse_key, plain, text_of


def merge(archives):
    catalog=read_json(ROOT/'data/catalog.json',{})
    sources=read_json(ROOT/'data/local_sources.json',{})
    resources=catalog['resources']
    tests={t['id']:t for t in catalog['tests']}
    changed=set()
    for volume,path,fixed_test in archives:
        source=f'listening-supplement-v{volume}'
        sources[source]=str(path.resolve())
        grouped={}
        shared_keys=[]
        with zipfile.ZipFile(path) as z:
            for item in z.infolist():
                ext=Path(item.filename).suffix.lower()
                if ext not in {'.pdf','.docx','.mp3','.mp4','.m4a','.wma'}:
                    continue
                name=Path(item.filename).name
                normalized=plain(item.filename)
                role=('audio' if ext in {'.mp3','.mp4','.m4a','.wma'} else
                      'key' if 'key' in normalized or 'dap an' in normalized else
                      'transcript' if 'transcript' in normalized else 'paper')
                match=re.search(r'test\s*(\d+)',name,re.I)
                if not match and volume==7 and role=='key':
                    shared_keys.append(item.filename)
                    continue
                number=fixed_test or (int(match[1]) if match else None)
                if not number:
                    matches=re.findall(r'/test\s*(\d+)(?:/|$)',normalized)
                    number=int(matches[-1]) if matches else None
                if not number:
                    continue
                rid=hashlib.sha256((source+':'+item.filename).encode()).hexdigest()[:16]
                resources[rid]={'id':rid,'source':source,'entry':item.filename,'name':name,'ext':ext,'size':item.file_size,'role':role,'volume':volume}
                grouped.setdefault(number,[]).append(rid)
            for number,new_ids in grouped.items():
                tid=f'listening-v{volume}-t{number}'
                t=tests.setdefault(tid,{'id':tid,'skill':'listening','volume':volume,'number':number,'title':f'VOL {volume} · Test {number}','resources':[],'answers':{},'groups':[],'key_source':None})
                # Complete replacement of audio avoids duplicate tracks from older ZIPs.
                if any(resources[r]['role']=='audio' for r in new_ids):
                    t['resources']=[r for r in t['resources'] if resources[r]['role']!='audio']
                if any(resources[r]['role']=='paper' for r in new_ids):
                    t['resources']=[r for r in t['resources'] if resources[r]['role']!='paper']
                t['resources']=list(dict.fromkeys(t['resources']+new_ids))
                for rid in new_ids:
                    r=resources[rid]
                    if r['role']=='key':
                        answers,groups=parse_key(text_of(z,r['entry']))
                        if len(answers)>=max(10,len(t['answers'])):
                            t.update(answers=answers,groups=groups,key_source=rid)
                for name in shared_keys:
                    rid=hashlib.sha256((source+':'+name).encode()).hexdigest()[:16]
                    item=z.getinfo(name)
                    resources[rid]={'id':rid,'source':source,'entry':name,'name':Path(name).name,'ext':'.pdf','size':item.file_size,'role':'key','volume':volume}
                    if rid not in t['resources']:
                        t['resources'].append(rid)
                t.update(key_count=len(t['answers']),has_audio=any(resources[r]['role']=='audio' for r in t['resources']))
                t['resources'].sort(key=lambda r:(resources[r]['role'],plain(resources[r]['name'])))
                changed.add(tid)
    catalog['tests']=sorted(tests.values(),key=lambda t:(t['skill'],t['volume'],t['number']))
    # One new immutable asset per changed test. Existing release assets remain intact.
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import secrets
    config=tomllib.loads((ROOT/'.streamlit/secrets.toml').read_text(encoding='utf-8'))
    key=base64.urlsafe_b64decode(config['DATA_KEY'])
    handles={s:zipfile.ZipFile(p) for s,p in sources.items()}
    try:
        for tid in sorted(changed):
            t=tests[tid]
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=2) as pack:
                for rid in t['resources']:
                    r=resources[rid]
                    pack.writestr(rid+r['ext'],handles[r['source']].read(r['entry']))
            nonce=secrets.token_bytes(12)
            payload=MAGIC+nonce+AESGCM(key).encrypt(nonce,buf.getvalue(),MAGIC)
            name=tid+'-'+hashlib.sha256(payload).hexdigest()[:12]+'.bingo'
            (ROOT/'data/packs'/name).write_bytes(payload)
            t['pack']=name
    finally:
        for z in handles.values():
            z.close()
    write_json(ROOT/'data/catalog.json',catalog)
    write_json(ROOT/'data/local_sources.json',sources)
    write_json(ROOT/'.bingo/supplement-report.json',{'changed':sorted(changed),'tests':len(tests),'new_bundles':len(changed)})
    print(json.dumps({'changed':sorted(changed),'tests':len(tests),'new_bundles':len(changed)}),flush=True)


if __name__=='__main__':
    merge([(8,Path(r'C:\Users\HP\Downloads\LISTENING-20261028T005159Z-1-001.zip'),None),
           (7,Path(r'C:\Users\HP\Downloads\Listening-20261028T005616Z-1-001.zip'),None),
           (5,Path(r'C:\Users\HP\Downloads\Test 2-20261028T005727Z-1-001.zip'),2)])
