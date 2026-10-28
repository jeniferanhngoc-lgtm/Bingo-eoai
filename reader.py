"""A persistent highlighter for document text and original scanned PDF pages."""
import base64
import html
import io
import math
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT=Path(__file__).parent
component=components.declare_component('bingo_highlight_reader',path=str(ROOT/'components/reader'))
exam_component=components.declare_component('bingo_exam',path=str(ROOT/'components/exam'))
COLORS={'yellow','green','blue','pink'}


@st.cache_data(max_entries=6,show_spinner=False)
def pdf_page(data,index):
    import pypdfium2 as pdfium
    document=pdfium.PdfDocument(data)
    count=len(document)
    index=max(0,min(index,count-1))
    page=document[index]
    textpage=page.get_textpage()
    text=textpage.get_text_range()
    textpage.close()
    bitmap=page.render(scale=min(1.7,1200/max(page.get_width(),1)))
    image=bitmap.to_pil()
    buf=io.BytesIO()
    image.save(buf,format='JPEG',quality=88)
    image.close()
    bitmap.close()
    page.close()
    document.close()
    return {'count':count,'image':'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode(),'text':text}


def validate_annotations(value,kind):
    if not isinstance(value,dict) or not isinstance(value.get('marks'),list) or len(value['marks'])>2000:
        raise ValueError('Invalid highlight state')
    marks=[]
    for raw in value['marks']:
        if not isinstance(raw,dict) or raw.get('color') not in COLORS or not isinstance(raw.get('id'),str) or len(raw['id'])>80:
            raise ValueError('Invalid highlight')
        mark={'id':raw['id'],'color':raw['color']}
        fields=['x','y','w','h'] if kind=='image' else ['start','end']
        for key in fields:
            v=raw.get(key)
            if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v):
                raise ValueError('Invalid highlight coordinate')
            if kind=='image' and not 0<=v<=1:
                raise ValueError('Highlight outside page')
            if kind=='text' and (int(v)!=v or not 0<=v<=5_000_000):
                raise ValueError('Invalid text offset')
            mark[key]=v
        if kind=='text' and mark['end']<=mark['start']:
            raise ValueError('Empty highlight')
        if kind=='image' and (mark['w']<=0 or mark['h']<=0 or mark['x']+mark['w']>1.001 or mark['y']+mark['h']>1.001):
            raise ValueError('Invalid rectangle')
        marks.append(mark)
    updated=value.get('updated',0)
    if not isinstance(updated,(int,float)) or not math.isfinite(updated):
        raise ValueError('Invalid timestamp')
    return {'marks':marks,'updated':max(0,min(updated,10**15))}


def highlight_reader(data,extension,rid,progress,save_callback,word_html=None):
    kind='text'
    content=''
    if extension=='.pdf':
        # Inspect page one for page count, then render only the selected page.
        import pypdfium2 as pdfium
        document=pdfium.PdfDocument(data)
        count=len(document)
        document.close()
        index=st.number_input(f'Trang PDF (1–{count})',min_value=1,max_value=count,value=1,key='pdf-page-'+rid)
        info=pdf_page(data,index-1)
        choices=['Trang gốc · kéo vùng highlight']
        if len(info['text'].strip())>30:
            choices.append('Văn bản · bôi chọn chữ')
        view=st.radio('Cách xem và highlight',choices,horizontal=True,key='pdf-view-'+rid)
        if view==choices[0]:
            kind='image'
            content=info['image']
            section=f'pdf-region-{index}'
        else:
            content='<p>'+html.escape(info['text']).replace('\n','<br>')+'</p>'
            section=f'pdf-text-{index}'
        st.caption('Bạn có thể tô cả bài đọc, câu hỏi, bảng và sơ đồ. Mỗi trang lưu highlight riêng.')
    else:
        content=re.search(r'<body>(.*)</body>',word_html,flags=re.S)[1]
        section='word-text'
        st.caption('Bôi chọn chữ trong bài đọc hoặc câu hỏi rồi bấm “Tô đoạn đã chọn”.')
    document_key=rid+':'+section
    stored=progress.setdefault('highlights',{}).setdefault(rid,{}).get(section,{'marks':[],'updated':0})
    try:
        stored=validate_annotations(stored,kind)
    except ValueError:
        stored={'marks':[],'updated':0}
    event=component(document_key=document_key,kind=kind,content=content,annotations=stored,height=800,key='highlight-'+rid,default=None)
    if isinstance(event,dict) and event.get('document_key')==document_key and event.get('nonce')!=st.session_state.get('highlight-event-'+rid):
        try:
            annotations=validate_annotations(event.get('annotations'),kind)
            progress['highlights'][rid][section]=annotations
            save_callback()
            st.session_state['highlight-event-'+rid]=event.get('nonce')
        except ValueError:
            st.warning('Highlight chưa hợp lệ nên chưa được lưu.')
    st.caption('Highlight tự lưu theo tài liệu; cũng có trong file sao lưu tiến độ. Trình duyệt này giữ thêm bản lưu để khôi phục khi cloud khởi động lại.')


def prepare_document(data,extension,rid,progress,page=1,view='image',word_html=None):
    """Return what the exam screen needs to show one document, plus its stored highlights."""
    doc={'kind':'text','content':'','page':1,'pages':0,'can_text':False,'view':'text'}
    if extension=='.pdf':
        info=pdf_page(data,max(0,int(page)-1))
        count=info['count']
        page=max(1,min(int(page),count))
        can_text=len(info['text'].strip())>30
        if view=='text' and not can_text:
            view='image'
        doc.update(pages=count,page=page,can_text=can_text,view=view)
        if view=='image':
            doc.update(kind='image',content=info['image'])
            section=f'pdf-region-{page}'
        else:
            doc.update(kind='text',content='<p>'+html.escape(info['text']).replace('\n','<br>')+'</p>')
            section=f'pdf-text-{page}'
    elif extension=='.docx':
        doc['content']=re.search(r'<body>(.*)</body>',word_html,flags=re.S)[1]
        section='word-text'
    else:
        raise ValueError('Định dạng tài liệu không hỗ trợ trong màn hình làm bài.')
    doc['document_key']=rid+':'+section
    stored=progress.setdefault('highlights',{}).setdefault(rid,{}).get(section,{'marks':[],'updated':0})
    try:
        stored=validate_annotations(stored,doc['kind'])
    except ValueError:
        stored={'marks':[],'updated':0}
    return doc,stored,section


def store_highlight(progress,rid,section,kind,annotations):
    """Validate and store one highlight state; raises ValueError when invalid."""
    clean=validate_annotations(annotations,kind)
    progress.setdefault('highlights',{}).setdefault(rid,{})[section]=clean
