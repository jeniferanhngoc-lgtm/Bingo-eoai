"""Study, grading, document rendering and encrypted resource storage."""
import base64
import hashlib
import html
import io
import json
import os
import re
import unicodedata
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent
MAGIC = b'BINGO1'


def audio_part(resource):
    name = resource['name'].casefold()
    match = re.search(r'(?:audiotrack|track|part|secction|section|\b[ps])[\s_]*(0?[1-4])\b', name)
    if not match:
        match = re.match(r'^(0?[1-4])(?:\s+track|\.)',name)
    return int(match[1]) if match else 0


def audio_files(test, resources):
    return sorted([r for r in test['resources'] if resources[r]['role']=='audio'],key=lambda r:(audio_part(resources[r]),resources[r]['name'].casefold()))


def missing_audio_parts(test, resources):
    parts = {audio_part(resources[r]) for r in audio_files(test,resources)} - {0}
    return sorted({1,2,3,4}-parts) if parts else []


def normalize(value):
    value = unicodedata.normalize('NFKC', str(value)).casefold().strip()
    value = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', value)
    value = re.sub(r'[‐‑–—-]', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip(' .')
    return {'t': 'true', 'f': 'false', 'ng': 'not given', 'ngv': 'not given', 'n/g': 'not given'}.get(value, value)


def accepted_forms(answer):
    forms = {normalize(answer)}
    # Optional words: "(the) forest" accepts both versions. Optional plural: "book(s)".
    if '(' in answer and ')' in answer:
        forms.add(normalize(re.sub(r'\(([^)]*)\)', r'\1', answer)))
        forms.add(normalize(re.sub(r'\([^)]*\)', '', answer)))
    return forms


def grade(test, responses):
    results = {}
    for number, variants in test['answers'].items():
        given = responses.get(number, '')
        correct = bool(normalize(given)) and any(normalize(given) in accepted_forms(v) for v in variants)
        results[number] = {'given': given, 'expected': ' / '.join(variants), 'correct': correct}
    for group in test.get('groups', []):
        expected = Counter(normalize(v) for v in group['answers'])
        for n in group['numbers']:
            n = str(n)
            value = normalize(responses.get(n, ''))
            correct = bool(value) and expected[value] > 0
            if correct:
                expected[value] -= 1
            results[n] = {'given': responses.get(n, ''), 'expected': ', '.join(group['answers']) + ' (bất kỳ thứ tự)', 'correct': correct}
    return results


def band(score, skill):
    thresholds = ([(39,9),(37,8.5),(35,8),(33,7.5),(30,7),(27,6.5),(23,6),(19,5.5),(15,5),(13,4.5),(10,4),(8,3.5),(6,3),(4,2.5)]
                  if skill == 'listening' else
                  [(39,9),(37,8.5),(35,8),(33,7.5),(30,7),(27,6.5),(23,6),(19,5.5),(15,5),(13,4.5),(10,4),(8,3.5),(6,3),(4,2.5)])
    return next((b for minimum,b in thresholds if score >= minimum), 0)


def read_json(path, fallback):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fallback


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def decrypt_pack(payload, key):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not payload.startswith(MAGIC):
        raise ValueError('Gói dữ liệu không đúng định dạng Bingo.')
    raw = AESGCM(base64.urlsafe_b64decode(key)).decrypt(payload[6:18], payload[18:], MAGIC)
    return raw


def remote_pack(test_id, settings):
    # Stable per-key cache names prevent stale data after secret changes.
    repo = settings.get('DATA_REPOSITORY', '')
    release = settings.get('DATA_RELEASE', 'bingo-data-v1')
    key = settings.get('DATA_KEY', '')
    if not repo or not key:
        raise FileNotFoundError('Chưa cấu hình kho dữ liệu. Thêm DATA_REPOSITORY và DATA_KEY trong Streamlit Secrets.')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or not re.fullmatch(r'[A-Za-z0-9_.-]+', release):
        raise ValueError('Tên repository hoặc release không hợp lệ.')
    digest = hashlib.sha256((repo+release+key).encode()).hexdigest()[:12]
    folder = ROOT/'.bingo'/'cache'/digest
    folder.mkdir(parents=True, exist_ok=True)
    cached = folder/f'{test_id}.zip'
    if cached.exists():
        return cached
    asset_name = f'{test_id}.bingo'
    token = settings.get('GITHUB_TOKEN', '')
    headers = {'User-Agent':'Bingo-IELTS', 'Accept':'application/vnd.github+json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = urllib.request.Request(f'https://api.github.com/repos/{repo}/releases/tags/{release}', headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        release_data = json.load(response)
    asset = next((a for a in release_data['assets'] if a['name']==asset_name), None)
    if not asset:
        raise FileNotFoundError('Bài này chưa được tải lên kho dữ liệu GitHub Releases.')
    if token:
        request = urllib.request.Request(asset['url'], headers={**headers,'Accept':'application/octet-stream'})
    else:
        request = urllib.request.Request(asset['browser_download_url'], headers={'User-Agent':'Bingo-IELTS'})
    with urllib.request.urlopen(request, timeout=120) as response:
        encrypted = response.read(180_000_001)
    if len(encrypted)>180_000_000:
        raise ValueError('Gói bài học vượt dung lượng cho phép.')
    raw = decrypt_pack(encrypted, key)
    temporary = cached.with_suffix('.tmp')
    temporary.write_bytes(raw)
    temporary.replace(cached)
    return cached


def resource_bytes(resource, test_id, settings):
    sources = read_json(ROOT/'data/local_sources.json', {})
    local = sources.get(resource['source'])
    if local and Path(local).is_file():
        with zipfile.ZipFile(local) as z:
            return z.read(resource['entry'])
    local_pack = ROOT/'data/packs'/f'{test_id}.bingo'
    if local_pack.is_file() and settings.get('DATA_KEY'):
        with zipfile.ZipFile(io.BytesIO(decrypt_pack(local_pack.read_bytes(), settings['DATA_KEY']))) as z:
            return z.read(resource['id'] + resource['ext'])
    with zipfile.ZipFile(remote_pack(test_id, settings)) as z:
        return z.read(resource['id'] + resource['ext'])


def docx_html(data):
    """Render text, tables and embedded diagrams, with escaped user-owned content."""
    ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main', 'a':'http://schemas.openxmlformats.org/drawingml/2006/main', 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        rels = ET.fromstring(z.read('word/_rels/document.xml.rels'))
        targets = {r.attrib['Id']:r.attrib.get('Target','') for r in rels}
        body = ET.fromstring(z.read('word/document.xml')).find('w:body',ns)

        def render(node):
            tag = node.tag.rsplit('}',1)[-1]
            if tag == 't':
                return html.escape(node.text or '')
            if tag in {'br','cr'}:
                return '<br>'
            if tag == 'tab':
                return '&emsp;'
            if tag == 'blip':
                rid = node.attrib.get('{'+ns['r']+'}embed')
                target = targets.get(rid,'')
                path = 'word/'+target
                if target.startswith('media/') and path in z.namelist():
                    ext = Path(target).suffix.lower().strip('.')
                    mime = 'jpeg' if ext in {'jpg','jpeg'} else ext
                    if mime in {'jpeg','png','gif','webp'}:
                        return f'<img alt="Hình trong đề" src="data:image/{mime};base64,{base64.b64encode(z.read(path)).decode()}">'
                return ''
            if tag.endswith('Pr') or tag in {'instrText','delText'}:
                return ''
            inside = ''.join(render(c) for c in node)
            if tag == 'p':
                return '<p>'+inside+'</p>'
            if tag == 'r':
                if node.find('w:rPr/w:b',ns) is not None:
                    inside='<strong>'+inside+'</strong>'
                if node.find('w:rPr/w:i',ns) is not None:
                    inside='<em>'+inside+'</em>'
            return {'tbl':'<table>'+inside+'</table>','tr':'<tr>'+inside+'</tr>','tc':'<td>'+inside+'</td>'}.get(tag,inside)
        content = render(body)
    return '<html lang="en"><meta charset="utf-8"><style>body{font:17px/1.8 Georgia,serif;color:#243542;padding:20px 28px;background:#fff}p{margin:0 0 14px;white-space:pre-wrap}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;margin:18px 0}td{border:1px solid #ccdce5;padding:8px;vertical-align:top}::selection{background:#ffeb85}</style><body>'+content+'</body></html>'
