import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'.deps'))
from reader import validate_annotations,pdf_page,prepare_document,store_highlight


class ReaderTests(unittest.TestCase):
    def test_text_highlight_roundtrip(self):
        value={'marks':[{'id':'test-1','start':4,'end':16,'color':'yellow'}],'updated':123}
        self.assertEqual(validate_annotations(value,'text'),value)

    def test_pdf_rectangle_roundtrip(self):
        value={'marks':[{'id':'box-1','x':.1,'y':.2,'w':.3,'h':.1,'color':'blue'}],'updated':123}
        self.assertEqual(validate_annotations(value,'image'),value)

    def test_reject_outside_pdf_page(self):
        with self.assertRaises(ValueError):
            validate_annotations({'marks':[{'id':'x','x':.9,'y':.1,'w':.3,'h':.2,'color':'green'}]},'image')

    def test_reject_bad_offsets_and_colors(self):
        for mark in [{'id':'x','start':10,'end':3,'color':'yellow'}, {'id':'x','start':0,'end':3,'color':'url(bad)'}, {'id':'x','start':0,'end':float('inf'),'color':'pink'}]:
            with self.assertRaises(ValueError):
                validate_annotations({'marks':[mark]},'text')

    def test_scanned_pdf_render(self):
        import pypdfium2
        from pypdf import PdfWriter
        import io
        writer=PdfWriter();writer.add_blank_page(width=400,height=600)
        stream=io.BytesIO();writer.write(stream)
        result=pdf_page(stream.getvalue(),0)
        self.assertEqual(result['count'],1)
        self.assertTrue(result['image'].startswith('data:image/jpeg;base64,'))
        self.assertEqual(result['text'],'')

    def test_prepare_document_clamps_page_and_falls_back_to_image(self):
        import io
        from pypdf import PdfWriter
        writer=PdfWriter()
        for _ in range(3):
            writer.add_blank_page(width=400,height=600)
        stream=io.BytesIO();writer.write(stream)
        progress={}
        doc,stored,section=prepare_document(stream.getvalue(),'.pdf','rid',progress,page=9,view='text')
        self.assertEqual((doc['page'],doc['pages'],doc['kind']),(3,3,'image'))
        self.assertEqual(section,'pdf-region-3')
        self.assertEqual(doc['document_key'],'rid:pdf-region-3')
        store_highlight(progress,'rid',section,'image',{'marks':[{'id':'a','x':.1,'y':.1,'w':.2,'h':.1,'color':'blue'}],'updated':1})
        self.assertEqual(len(progress['highlights']['rid'][section]['marks']),1)
        with self.assertRaises(ValueError):
            store_highlight(progress,'rid',section,'image',{'marks':[{'id':'a','x':.9,'y':.1,'w':.5,'h':.1,'color':'blue'}]})


if __name__=='__main__':
    unittest.main()
