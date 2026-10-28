"""Import owner-supplied Cambridge Reading archives into encrypted bundles."""
import base64
import hashlib
import io
import itertools
import re
import secrets
import sys
import tomllib
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import MAGIC, read_json, write_json


def forms(value):
    value = re.sub(r'\s+', ' ', value).strip()
    value = {'T':'TRUE','F':'FALSE','NG':'NOT GIVEN','Y':'YES','N':'NO','FASLE':'FALSE'}.get(value.upper(), value)
    # Expand parenthesised alternatives before splitting slash variants.
    match = re.search(r'\(([^()]* / [^()]*)\)', value)
    if match:
        return list(dict.fromkeys(itertools.chain.from_iterable(forms(value[:match.start()]+v.strip()+value[match.end():]) for v in match[1].split('/'))))
    if value.startswith('IN EITHER ORDER '):
        value = value.removeprefix('IN EITHER ORDER ')
        pieces = re.split(r'\s*\(and\)\s*', value)
        return [' and '.join(pieces), ' '.join(pieces), ' and '.join(reversed(pieces)), ' '.join(reversed(pieces))]
    return [v.strip() for v in re.split(r'\s*(?:/|\bor\b)\s*', value) if v.strip()]


def parse_keys(data):
    doc = Document(io.BytesIO(data))
    candidates = []
    for table in doc.tables:
        answers, groups = {}, []
        for row in table.rows:
            for cell in row.cells:
                for line in cell.text.splitlines():
                    match = re.fullmatch(r'\s*(\d{1,2})(?:\s*&\s*(\d{1,2}))?\s*(?:[.]\s*|\s+)(.+?)\s*', line)
                    if not match or not 1 <= int(match[1]) <= 40:
                        continue
                    number, end, value = int(match[1]), int(match[2] or match[1]), match[3]
                    value = re.sub(r'^'+str(number)+r'\.\s*', '', value)
                    if end != number:
                        letters = re.findall(r'\b[A-H]\b', value)
                        if end == number+1 and len(letters)==2:
                            groups.append({'numbers':[number,end], 'answers':letters})
                            answers.update({str(k):[v] for k,v in zip([number,end],letters)})
                    else:
                        answers[str(number)] = forms(value)
        # CAM18 answer tables use three passage columns with implicit numbering.
        if len(table.rows)==2 and len(table.columns)==3 and all('passage' in c.text.lower() for c in table.rows[0].cells):
            columns = []
            for cell in table.rows[1].cells:
                lines=[s.strip() for s in cell.text.splitlines() if s.strip()]
                values=[]
                for i,line in enumerate(lines):
                    group=re.fullmatch(r'(\d+)&(\d+)\. IN EITHER ORDER',line)
                    if group:
                        groups.append({'numbers':[int(group[1]),int(group[2])], 'answers':lines[i+1:i+3]})
                    else:
                        values.append(re.sub(r'^\d+\.\s*','',line))
                columns.append(values)
            if list(map(len,columns)) == [13,13,14]:
                answers = {str(i):forms(v) for i,v in enumerate(itertools.chain.from_iterable(columns),1)}
        if len(answers)>=30:
            candidates.append((answers,groups))
    if len(candidates)!=1:
        raise ValueError(f'Expected one answer table; found {len(candidates)}')
    answers,groups = candidates[0]
    if len(answers)!=40:
        raise ValueError(f'Incomplete keys: {len(answers)}')
    # Adjacent questions listing the same two choices must consume each once.
    for n in range(1,40):
        a,b=answers[str(n)],answers[str(n+1)]
        if len(a)==2 and a==b and all(re.fullmatch('[A-H]',v) for v in a) and not any(n in g['numbers'] for g in groups):
            groups.append({'numbers':[n,n+1],'answers':a})
    return answers,groups


def main():
    catalog=read_json(ROOT/'data/catalog.json',{})
    sources=read_json(ROOT/'data/local_sources.json',{})
    key=base64.urlsafe_b64decode(tomllib.loads((ROOT/'.streamlit/secrets.toml').read_text(encoding='utf-8'))['DATA_KEY'])
    report=[]
    for volume in [14,15,16,17,18,20]:
        path=ROOT.parent/f'cam{volume}.zip'
        if volume==20:
            path=Path('C:/Users/HP/AppData/Local/Temp/MicrosoftEdgeDownloads/423f6f3f-c401-44e7-8028-550aff531742/cam20.zip')
        source=f'cambridge-{volume}'
        sources[source]=str(path)
        with zipfile.ZipFile(path) as archive:
            for number in range(1,5):
                tid=f'reading-cam{volume}-t{number}'
                entries=[i for i in archive.infolist() if not i.is_dir() and re.search(r'test\s*'+str(number)+r'\b',i.filename,re.I)]
                assert len(entries)==2, (tid,len(entries))
                test={'id':tid,'skill':'reading','collection':'cambridge','volume':volume,'number':number,'title':f'CAM {volume} · Test {number}','resources':[],'answers':{},'groups':[],'has_audio':False}
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as bundle:
                    for item in sorted(entries,key=lambda i: bool(re.search('key|answer',Path(i.filename).name,re.I))):
                        role='key' if re.search('key|answer',Path(item.filename).name,re.I) else 'paper'
                        rid=hashlib.sha256((source+':'+item.filename).encode()).hexdigest()[:16]
                        data=archive.read(item)
                        catalog['resources'][rid]={'id':rid,'source':source,'entry':item.filename,'name':Path(item.filename).name,'ext':'.docx','size':len(data),'role':role,'volume':volume}
                        test['resources'].append(rid)
                        bundle.writestr(rid+'.docx',data)
                        if role=='paper':test['preferred_paper']=rid
                        else:
                            test['answers'],test['groups']=parse_keys(data)
                            test['key_source']=rid
                test['key_count']=len(test['answers'])
                nonce=secrets.token_bytes(12)
                encrypted=MAGIC+nonce+AESGCM(key).encrypt(nonce,buffer.getvalue(),MAGIC)
                test['pack']=tid+'-'+hashlib.sha256(encrypted).hexdigest()[:12]+'.bingo'
                (ROOT/'data/packs'/test['pack']).write_bytes(encrypted)
                catalog['tests']=[t for t in catalog['tests'] if t['id']!=tid]+[test]
                report.append({'id':tid,'keys':test['key_count'],'groups':test['groups'],'bytes':len(encrypted)})
    write_json(ROOT/'data/catalog.json',catalog)
    write_json(ROOT/'catalog.json',catalog)
    write_json(ROOT/'data/local_sources.json',sources)
    write_json(ROOT/'.bingo/cambridge-report.json',report)
    print(report)


if __name__=='__main__':
    main()
