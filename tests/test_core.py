import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import ROOT, accepted_forms, audio_files, audio_part, missing_audio_parts, band, docx_html, grade, normalize, resource_bytes


class GradingTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize('  TRUE. '),'true')
        self.assertEqual(normalize('NGV'),'not given')
        self.assertEqual(normalize('14,000'),'14000')
        self.assertEqual(normalize('well-known'),'well known')

    def test_optional_words(self):
        self.assertEqual(accepted_forms('book(s)'),{'book(s)','books','book'})

    def test_unordered_group_no_double_credit(self):
        test={'answers':{'1':['B'],'2':['D']},'groups':[{'numbers':[1,2],'answers':['B','D']}]}
        result=grade(test,{'1':'D','2':'B'})
        self.assertTrue(all(r['correct'] for r in result.values()))
        result=grade(test,{'1':'B','2':'B'})
        self.assertEqual(sum(r['correct'] for r in result.values()),1)

    def test_empty_not_correct(self):
        self.assertFalse(grade({'answers':{'1':['hotel']}},{})['1']['correct'])

    def test_audio_order_and_missing_parts(self):
        resources={'a':{'name':'section1.m4a','role':'audio'},'b':{'name':'section 3.m4a','role':'audio'}}
        test={'resources':['b','a']}
        self.assertEqual(audio_files(test,resources),['a','b'])
        self.assertEqual(missing_audio_parts(test,resources),[2,4])
        self.assertEqual(audio_part({'name':'AudioTrack 02.mp3'}),2)

    def test_band_boundaries(self):
        self.assertEqual(band(40,'reading'),9)
        self.assertEqual(band(30,'listening'),7)

    def test_catalog_integrity(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
        ids={t['id'] for t in catalog['tests']}
        self.assertEqual(len(ids),139)
        for t in catalog['tests']:
            self.assertTrue(any(catalog['resources'][r]['role']=='paper' for r in t['resources']))
            self.assertEqual(t['key_count'],len(t['answers']))
            self.assertTrue(all(1<=int(k)<=40 for k in t['answers']))

    def test_word_diagrams_preserved(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
        t=next(t for t in catalog['tests'] if t['id']=='reading-v7-t1')
        r=next(catalog['resources'][r] for r in t['resources'] if catalog['resources'][r]['role']=='paper')
        output=docx_html(resource_bytes(r,t['id'],{}))
        self.assertIn('CARNIVOROUS',output.upper())
        self.assertNotIn('<script',output)


if __name__=='__main__':
    unittest.main()
