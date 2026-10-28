import io
import sys
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from questions import extract_questions


def make_docx(paragraphs):
    """paragraphs: list of strings; "\n" inside a string becomes a Word line break."""
    body = ''
    for text in paragraphs:
        runs = '<w:br/>'.join(f'<w:t>{escape(line)}</w:t>' for line in text.split('\n'))
        body += f'<w:p><w:r>{runs}</w:r></w:p>'
    xml = ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f'<w:body>{body}</w:body></w:document>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('word/document.xml', xml)
    return buf.getvalue()


class QuestionTests(unittest.TestCase):
    def test_statements_lists_and_gaps(self):
        r = extract_questions(make_docx([
            'READING PASSAGE 1',
            '1999 was a long time ago.',            # passage text must not become a question
            'Questions 1-2',
            'Match each theory with the researcher, A-B.\nWrite the correct letter, A-B, in boxes 1-2 on your answer sheet.',
            '1 Humans came from many places.\n2 Megafauna died quickly.',
            'List of Researchers\nA Jim Bowler\nB Alan Thorne',
            'Questions 3-4',
            'Complete the summary below.',
            'Title line\nMungo man lived 3 ………………………. ago. Experts studied the 4………………………. near the lake.',
        ]))
        q = r['questions']
        self.assertEqual(q['1']['text'], 'Humans came from many places.')
        self.assertEqual(q['3']['text'], 'Mungo man lived _____ ago')
        self.assertEqual(q['4']['text'], 'Experts studied the _____ near the lake.')
        self.assertNotIn('5', q)
        self.assertEqual(r['groups'][0]['list'], [['A', 'Jim Bowler'], ['B', 'Alan Thorne']])
        self.assertEqual(r['groups'][0]['list_title'], 'List of Researchers')

    def test_multiple_choice_and_choose_two(self):
        r = extract_questions(make_docx([
            'Questions 5-6', 'Choose the correct letter, A, B, C or D.',
            '5 What happened first?\nA a storm\nB a flood\nC a fire\nD a war',
            '6 Why?\nA no reason\nB money\nC fear\nD pride',
            'Questions 7-8', 'Choose TWO letters A-E.\nWrite the correct letters in boxes 7 and 8.\nWhich TWO are true?',
            'A one\nB two\nC three',
        ]))
        q = r['questions']
        self.assertEqual([o[0] for o in q['5']['options']], ['A', 'B', 'C', 'D'])
        self.assertEqual(q['6']['text'], 'Why?')
        self.assertTrue(q['7']['shared'])
        self.assertEqual(q['7']['text'], 'Which TWO are true?')
        self.assertEqual(len(q['8']['options']), 3)

    def test_bundle_keeps_only_first_test(self):
        r = extract_questions(make_docx([
            'TEST 1', 'READING PASSAGE 1', 'Questions 1-1', '1 first test',
            'TEST 2', 'READING PASSAGE 1', 'Questions 1-1', '1 second test']))
        self.assertEqual(r['questions']['1']['text'], 'first test')

    def test_garbage_input_is_harmless(self):
        self.assertEqual(extract_questions(b'not a zip'), {'questions': {}, 'groups': []})


if __name__ == '__main__':
    unittest.main()
