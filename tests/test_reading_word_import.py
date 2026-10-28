import io
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
from openpyxl import Workbook
from supplement_reading_word import workbook_keys
from core import docx_html,resource_bytes
from questions import extract_questions


def book(rows):
    workbook=Workbook()
    sheet=workbook.active
    sheet.title='Test 1'
    for row in rows:
        sheet.append(row)
    data=io.BytesIO()
    workbook.save(data)
    return data.getvalue()


class ReadingWordTests(unittest.TestCase):
    def test_boolean_and_numeric_keys(self):
        self.assertEqual(workbook_keys(book([(1,True),(2,False),(3,14)]))[1],{'1':['TRUE'],'2':['FALSE'],'3':['14']})

    def test_numeric_answer_does_not_become_question_number(self):
        result=workbook_keys(book([(1,4,21,'A'),(2,5,22,'B')]))[1]
        self.assertEqual(result,{'1':['4'],'2':['5'],'21':['A'],'22':['B']})

    def test_misnumbered_cell_does_not_overwrite_other_passage(self):
        notes=[]
        result=workbook_keys(book([(1,True,32,'No'),(3,False,3,'Yes'),(4,'NG',34,'NG')]),notes)[1]
        self.assertEqual(result['3'],['FALSE'])
        self.assertNotIn('33',result)
        self.assertEqual(len(notes),1)

    def test_all_thirty_word_papers_default_and_originals_preserved(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8'))
        self.assertEqual(catalog,json.loads((ROOT/'catalog.json').read_text(encoding='utf8')))
        tests={t['id']:t for t in catalog['tests']}
        for vol in [3,4,5]:
            for number in range(1,11):
                with self.subTest(volume=vol,test=number):
                    test=tests[f'reading-v{vol}-t{number}']
                    rid=test['resources'][0]
                    resource=catalog['resources'][rid]
                    self.assertEqual(rid,test['preferred_paper'])
                    self.assertEqual(resource['ext'],'.docx')
                    self.assertTrue(any(catalog['resources'][r]['role']=='paper' and catalog['resources'][r]['ext']=='.pdf' for r in test['resources']))
                    data=resource_bytes(resource,test['id'],{})
                    rendered=docx_html(data)
                    self.assertIn('READING',rendered.upper())
                    self.assertGreater(len(rendered),10000)
                    questions=extract_questions(data)
                    self.assertGreater(len(questions['questions']),0)


if __name__=='__main__':
    unittest.main()
