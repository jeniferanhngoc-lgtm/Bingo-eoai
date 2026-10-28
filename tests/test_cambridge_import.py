import base64
import io
import json
import sys
import tomllib
import unittest
import zipfile
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
from core import MAGIC,docx_html,grade,resource_bytes
from questions import extract_questions
from supplement_cambridge import parse_keys,forms


class CambridgeTests(unittest.TestCase):
    def test_optional_words_and_variants(self):
        self.assertEqual(forms('(its / huarango / the) branches'),['its branches','huarango branches','the branches'])
        self.assertEqual(forms('(unique) expeditions'),['(unique) expeditions'])
        self.assertEqual(forms('NG'),['NOT GIVEN'])

    def test_all_papers_keys_and_encrypted_payloads(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        self.assertEqual(catalog,json.loads((ROOT/'catalog.json').read_text(encoding='utf8')))
        tests=[t for t in catalog['tests'] if t.get('collection')=='cambridge']
        self.assertEqual(len(tests),24)
        key=base64.urlsafe_b64decode(tomllib.loads((ROOT/'.streamlit/secrets.toml').read_text(encoding='utf8'))['DATA_KEY'])
        for test in tests:
            with self.subTest(test=test['id']):
                self.assertEqual(set(test['answers']),{str(i) for i in range(1,41)})
                payload=(ROOT/'data/packs'/test['pack']).read_bytes()
                self.assertTrue(payload.startswith(MAGIC))
                plain=AESGCM(key).decrypt(payload[6:18],payload[18:],MAGIC)
                with zipfile.ZipFile(io.BytesIO(plain)) as pack:
                    for rid in test['resources']:
                        resource=catalog['resources'][rid]
                        original=resource_bytes(resource,test['id'],{})
                        self.assertEqual(pack.read(rid+'.docx'),original)
                        if resource['role']=='paper':
                            self.assertGreater(len(docx_html(original)),10000)
                            self.assertGreater(len(extract_questions(original)['questions']),0)
                        else:self.assertEqual(parse_keys(original),(test['answers'],test['groups']))

    def test_multi_answer_groups_reject_duplicate_choice(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        test=next(t for t in catalog['tests'] if t['id']=='reading-cam20-t3')
        self.assertTrue(all(r['correct'] for r in grade(test,{'20':'E','21':'C'}).values() if r['given']))
        result=grade(test,{'20':'C','21':'C'})
        self.assertEqual(sum(result[n]['correct'] for n in ['20','21']),1)


if __name__=='__main__':unittest.main()
