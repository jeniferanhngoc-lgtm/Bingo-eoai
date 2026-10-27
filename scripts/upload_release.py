"""Upload encrypted study bundles using Git Credential Manager or GH_TOKEN.

Tokens stay in process memory. Original ZIPs, secrets and unencrypted packs
are never sent to GitHub. Uploads resume by matching asset name and size.
"""
import concurrent.futures
import http.client
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO='jeniferanhngoc-lgtm/Bingo-eoai'
TAG='bingo-data-v1'


def credential():
    token=os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
    if token:
        return token
    env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'}
    result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\nusername=jeniferanhngoc-lgtm\n\n',text=True,capture_output=True,env=env,timeout=30)
    fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if not fields.get('password'):
        raise RuntimeError('Sign in with Git Credential Manager before uploading.')
    return fields['password']


def api(token,path,body=None):
    payload=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request('https://api.github.com'+path,data=payload,headers={'User-Agent':'Bingo-Setup','Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as response:
        return json.load(response)


def main():
    token=credential()
    try:
        release=api(token,f'/repos/{REPO}/releases/tags/{TAG}')
    except urllib.error.HTTPError as error:
        if error.code!=404:
            raise
        release=api(token,f'/repos/{REPO}/releases',{'tag_name':TAG,'target_commitish':'main','name':'Bingo encrypted study library','body':'Encrypted per-test study bundles for Bingo. The decryption key is configured separately in Streamlit Secrets.','draft':False,'prerelease':False})
    assets=[]
    for page in range(1,10):
        batch=api(token,f'/repos/{REPO}/releases/{release["id"]}/assets?per_page=100&page={page}')
        assets.extend(batch)
        if len(batch)<100:
            break
    present={a['name']:a['size'] for a in assets}
    files=sorted((ROOT/'data/packs').glob('*.bingo'))
    pending=[p for p in files if present.get(p.name)!=p.stat().st_size]
    print(f'{len(files)} bundles; {len(pending)} uploads needed.',flush=True)

    def upload(path):
        for attempt in range(3):
            try:
                connection=http.client.HTTPSConnection('uploads.github.com',timeout=300)
                target=f'/repos/{REPO}/releases/{release["id"]}/assets?name={urllib.parse.quote(path.name)}'
                with path.open('rb') as body:
                    connection.request('POST',target,body=body,headers={'Authorization':'Bearer '+token,'User-Agent':'Bingo-Setup','Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)})
                    response=connection.getresponse()
                    output=json.loads(response.read())
                connection.close()
                if response.status==201:
                    return path.name
                if response.status==422:
                    # A retried upload may have completed before the connection dropped.
                    recent=api(token,f'/repos/{REPO}/releases/{release["id"]}/assets?per_page=100')
                    if any(a['name']==path.name and a['size']==path.stat().st_size for a in recent):
                        return path.name
                raise RuntimeError(f'Upload rejected (HTTP {response.status}) for {path.name}')
            except Exception:
                if attempt==2:
                    raise
                time.sleep(2**attempt)
    completed=0
    failures=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(upload,p):p for p in pending}
        for job in concurrent.futures.as_completed(jobs):
            try:
                job.result()
                completed+=1
                print(f'Uploaded {completed}/{len(pending)}',flush=True)
            except Exception as error:
                failures.append(jobs[job].name)
                print('Failed: '+jobs[job].name,flush=True)
    print(f'Finished: {completed} uploaded, {len(failures)} failed.',flush=True)
    if failures:
        raise SystemExit(1)


if __name__=='__main__':
    main()
