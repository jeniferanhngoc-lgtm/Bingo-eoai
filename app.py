"""Bingo: personal IELTS Listening and Reading, deployable on Streamlit Cloud."""
import hashlib
import hmac
import io
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from core import ROOT, band, docx_html, grade, read_json, resource_bytes, write_json

st.set_page_config(page_title='Bingo · IELTS Practice', page_icon='🎯', layout='wide')
css_path = ROOT/'assets/bingo.css' if (ROOT/'assets/bingo.css').exists() else ROOT/'bingo.css'
css = css_path.read_text(encoding='utf-8')
st.html('<style>'+'\n'.join(line for line in css.splitlines() if not line.startswith('@import'))+'</style>')


def setting(name, default=''):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except FileNotFoundError:
        return os.getenv(name, default)


def settings():
    return {key:setting(key) for key in ['DATA_REPOSITORY','DATA_RELEASE','GITHUB_TOKEN','DATA_KEY']}


def gate():
    password = setting('BINGO_PASSWORD')
    if not password:
        st.title('Bingo · Thiết lập mật khẩu')
        st.info('Thêm BINGO_PASSWORD vào Streamlit Secrets để mở ứng dụng. Bingo luôn yêu cầu mật khẩu, kể cả khi mã nguồn công khai.')
        st.code('BINGO_PASSWORD = "mat-khau-cua-ban"', language='toml')
        st.stop()
    fingerprint = hashlib.sha256(password.encode()).hexdigest()
    if st.session_state.get('authenticated') == fingerprint:
        return
    _, center, _ = st.columns([1,1.2,1])
    with center:
        st.html('<div class="hero"><div class="eyebrow">YOUR PERSONAL IELTS SPACE</div><h1>Bin<span style="color:#2FADDE">go.</span></h1><p>Mỗi bài luyện, một bước tiến.</p></div>')
        with st.form('login'):
            value = st.text_input('Mật khẩu của bạn', type='password')
            submit = st.form_submit_button('Vào Bingo →', type='primary', width='stretch')
        if submit:
            if hmac.compare_digest(value.encode(), password.encode()):
                st.session_state.authenticated = fingerprint
                st.rerun()
            else:
                st.error('Mật khẩu chưa đúng.')
    st.stop()


gate()
catalog_path = ROOT/'data/catalog.json' if (ROOT/'data/catalog.json').exists() else ROOT/'catalog.json'
catalog = read_json(catalog_path, {'tests':[], 'resources':{}})
tests = catalog['tests']
by_id = {t['id']:t for t in tests}
resources = catalog['resources']
STATE = ROOT/'.bingo/progress.json'
if 'progress' not in st.session_state:
    st.session_state.progress = read_json(STATE, {'drafts':{},'history':[], 'favorites':[]})
progress = st.session_state.progress


def save():
    write_json(STATE, progress)


def draft(test):
    return progress['drafts'].setdefault(test['id'], {'answers':{},'remaining':3600 if test['skill']=='reading' else 2400,'deadline':None})


def record(test):
    d = draft(test)
    if d.get('deadline'):
        d['remaining'] = max(0,int(d['deadline']-time.time()))
    d['deadline'] = None
    marked = grade(test,d['answers'])
    item = {'id':f"{test['id']}-{time.time_ns()}", 'test_id':test['id'], 'title':test['title'], 'skill':test['skill'], 'date':datetime.now(timezone.utc).isoformat(), 'responses':dict(d['answers']), 'results':marked, 'score':sum(r['correct'] for r in marked.values()), 'total':len(marked)}
    progress['history'].insert(0,item)
    save()
    st.session_state.result_id = item['id']


@st.cache_data(max_entries=4, show_spinner=False)
def load_resource(rid, tid, config):
    return resource_bytes(resources[rid], tid, config)


def viewer(rid, tid):
    r = resources[rid]
    try:
        with st.spinner('Đang mở tài liệu…'):
            data = load_resource(rid,tid,settings())
        if r['ext']=='.pdf':
            try:
                st.pdf(data,height=760,key='pdf-'+rid)
            except (ImportError,ModuleNotFoundError):
                st.warning('Cần cài streamlit[pdf] để xem PDF trực tiếp. Bạn vẫn có thể tải tài liệu bên dưới.')
        elif r['ext']=='.docx':
            st.iframe(docx_html(data),height=760)
        elif r['ext'] in {'.jpg','.png'}:
            st.image(data)
        elif r['ext']=='.xlsx':
            import openpyxl
            book = openpyxl.load_workbook(io.BytesIO(data),data_only=True)
            sheet_name = st.selectbox('Bảng đáp án',book.sheetnames,index=next((i for i,n in enumerate(book.sheetnames) if n.lower()==f"test {by_id[tid]['number']}"),0),key='sheet-'+rid)
            rows = list(book[sheet_name].values)
            st.dataframe([[str(v or '') for v in row] for row in rows],hide_index=True,width='stretch')
        st.download_button('Tải tài liệu gốc ↗', data,file_name=r['name'],key='download-'+rid)
    except Exception as e:
        # Don't leak private URLs, tokens or exception internals to the page.
        st.error('Chưa mở được tài liệu. Kiểm tra cấu hình dữ liệu hoặc kết nối mạng trong mục Hướng dẫn.')
        if isinstance(e,FileNotFoundError):
            st.caption(str(e))


def open_test(tid):
    st.session_state.active = tid
    st.session_state.pop('result_id',None)


with st.sidebar:
    st.html('<div class="bingo-logo">Bin<span>go.</span></div><p class="muted">Không gian IELTS của riêng bạn</p>')
    page = st.radio('Điều hướng',['Kho đề','Lịch sử','Sao lưu & hướng dẫn'],label_visibility='collapsed')
    st.divider()
    st.caption('TẬP TRUNG HÔM NAY')
    st.write('🎧 Listening  ·  📖 Reading')
    st.caption('Luyện theo nhịp của bạn. Tiến bộ từng ngày.')
    st.divider()
    if st.button('Đăng xuất',width='stretch'):
        st.session_state.clear()
        st.rerun()


def library():
    st.html('<section class="hero"><div class="eyebrow">BINGO / PRACTICE LIBRARY</div><h1>Đặt mục tiêu.<br>Luyện tập. Bứt phá.</h1><p>Kho Listening và Reading của bạn, trong một không gian gọn gàng. Chọn bài, tập trung làm và nhìn lại điều mình đã học.</p></section>')
    a,b,c = st.columns(3)
    a.metric('Bài Reading',sum(t['skill']=='reading' for t in tests))
    b.metric('Bài Listening',sum(t['skill']=='listening' for t in tests))
    c.metric('Lượt đã luyện',len(progress['history']))
    st.write('')
    a,b,c,d = st.columns([1.2,1,2,1])
    skill = a.selectbox('Kỹ năng',['Tất cả','Reading','Listening'])
    volumes = sorted({t['volume'] for t in tests})
    vol = b.selectbox('Bộ đề',['Tất cả']+[f'VOL {n}' for n in volumes])
    search = c.text_input('Tìm bài',placeholder='Ví dụ: Test 3')
    favorite_only = d.checkbox('Đã lưu',value=False)
    shown = [t for t in tests if (skill=='Tất cả' or t['skill']==skill.lower()) and (vol=='Tất cả' or t['volume']==int(vol.split()[1])) and (not search or search.lower() in t['title'].lower()) and (not favorite_only or t['id'] in progress['favorites'])]
    st.caption(f'{len(shown)} bài phù hợp · Đề gốc và đáp án được giữ nguyên để đối chiếu.')
    page_count = max(1,(len(shown)+11)//12)
    number = st.number_input('Trang',min_value=1,max_value=page_count,value=1,step=1)
    for offset in range(0,len(shown[(number-1)*12:number*12]),3):
        for column,t in zip(st.columns(3),shown[(number-1)*12+offset:(number-1)*12+offset+3]):
            with column,st.container(border=True):
                st.html(f'<span class="tag {t["skill"]}">{t["skill"].upper()}</span><div class="bingo-card-title">{t["title"]}</div>')
                st.caption(('60 phút' if t['skill']=='reading' else '40 phút')+' · Phiếu 40 câu')
                st.caption(f"Chấm tự động {t['key_count']}/40 câu" if t['key_count'] else 'Đối chiếu đáp án gốc')
                if t['skill']=='listening' and not t['has_audio']:
                    st.warning('ZIP chưa có audio cho bài này.',icon='🎧')
                done = sum(h['test_id']==t['id'] for h in progress['history'])
                if done:
                    st.caption(f'✓ Đã luyện {done} lần')
                x,y = st.columns([3,1])
                x.button('Tiếp tục →' if t['id'] in progress['drafts'] else 'Luyện ngay →',key='open-'+t['id'],type='primary',width='stretch',on_click=open_test,args=(t['id'],))
                star = t['id'] in progress['favorites']
                if y.button('★' if star else '☆',key='star-'+t['id'],help='Lưu bài'):
                    if star:
                        progress['favorites'].remove(t['id'])
                    else:
                        progress['favorites'].append(t['id'])
                    save()
                    st.rerun()


@st.fragment(run_every=1)
def clock_panel(test):
    d = draft(test)
    left = max(0,int(d['deadline']-time.time())) if d.get('deadline') else d['remaining']
    st.html(f'<div class="timer">{left//60:02d}:{left%60:02d}</div>')
    if d.get('deadline') and left==0:
        record(test)
        st.rerun()
    if st.button('Tạm dừng' if d.get('deadline') else 'Bắt đầu / Tiếp tục',key='timer-button-'+test['id']):
        if d.get('deadline'):
            d.update(remaining=left,deadline=None)
        else:
            d['deadline']=time.time()+left
        save()
        st.rerun(scope='fragment')


@st.fragment
def audio_panel(test):
    audio = [r for r in test['resources'] if resources[r]['role']=='audio']
    if not audio:
        st.warning('Chưa có audio trong ZIP cho bài này. Bạn có thể luyện bài khác hoặc bổ sung audio sau.')
        return
    rid = st.selectbox('Bản ghi',audio,format_func=lambda r:resources[r]['name'],key='audio-'+test['id'])
    try:
        data = load_resource(rid,test['id'],settings())
        ext = resources[rid]['ext']
        if ext == '.mp4':
            st.video(data)
        elif ext == '.wma':
            st.warning('Audio WMA có thể không phát trong trình duyệt. Tải xuống để nghe bằng ứng dụng trên máy.')
            st.download_button('Tải audio WMA',data,file_name=resources[rid]['name'])
        else:
            st.audio(data,format={'.mp3':'audio/mpeg','.m4a':'audio/mp4'}.get(ext,'audio/mpeg'))
        st.caption('Chọn bản ghi tiếp theo khi kết thúc. Bạn có thể nghe lại khi luyện tập.')
    except Exception:
        st.error('Chưa tải được audio. Kiểm tra kho dữ liệu và kết nối mạng.')


def answer_changed(tid,number,key):
    progress['drafts'][tid]['answers'][number] = st.session_state[key]
    save()


@st.fragment
def answers_panel(test):
    d = draft(test)
    count = sum(bool(a.strip()) for a in d['answers'].values())
    st.subheader('Phiếu trả lời')
    st.progress(min(count/40,1),text=f'{count}/40 câu đã điền · tự lưu khi rời ô')
    st.caption('Nhập chữ cái cho câu lựa chọn; TRUE / FALSE / NOT GIVEN cho câu nhận định. Làm theo giới hạn từ trong đề.')
    part = st.radio('Nhóm câu',['1–10','11–20','21–30','31–40'],horizontal=True,key='part-'+test['id'])
    start = int(part.split('–')[0])
    for i in range(start,start+10):
        number = str(i)
        key = f'ans-{test["id"]}-{number}'
        if key not in st.session_state:
            st.session_state[key] = d['answers'].get(number,'')
        st.text_input(f'Câu {i}',key=key,max_chars=120,on_change=answer_changed,args=(test['id'],number,key))
    if st.button('Nộp bài & xem kết quả',type='primary',width='stretch',key='submit-'+test['id']):
        record(test)
        st.rerun()
    st.caption('Hết giờ sẽ tự nộp bài khi trang đang mở. Thời gian vẫn trôi nếu bạn đóng trang khi đồng hồ đang chạy.')


def result_view(item,test):
    st.success('Đã lưu lượt luyện của bạn.')
    a,b,c=st.columns(3)
    a.metric('Câu đúng',f"{item['score']}/{item['total']}" if item['total'] else 'Chưa có khóa chấm')
    b.metric('Đã trả lời',f"{sum(bool(v.strip()) for v in item['responses'].values())}/40")
    c.metric('Band tham khảo',f"{band(item['score'],test['skill']):.1f}" if item['total']==40 else '—')
    st.caption('Đáp án được nhập tự động từ tài liệu bạn cung cấp. Hãy đối chiếu bản gốc khi có khác biệt; band chỉ để tham khảo. Reading dùng bảng quy đổi Academic.')
    if item['total']<40:
        st.info(f"Bài này mới có khóa chấm cho {item['total']}/40 câu. Các câu còn lại cần đối chiếu tài liệu gốc; chưa tính band toàn bài.")
    rows=[]
    for n in range(1,41):
        r=item['results'].get(str(n))
        rows.append({'Câu':n,'Bạn trả lời':item['responses'].get(str(n),''),'Đáp án':r['expected'] if r else 'Đối chiếu tài liệu gốc','Kết quả':('✓ Đúng' if r['correct'] else '✗ Chưa đúng') if r else 'Chưa chấm'})
    st.dataframe(rows,hide_index=True,width='stretch',height=500)
    keys=[r for r in test['resources'] if resources[r]['role'] in {'key','transcript'}]
    if keys:
        rid=st.selectbox('Đáp án / lời giải / transcript gốc',keys,format_func=lambda r:resources[r]['name'])
        viewer(rid,test['id'])
    if st.button('Làm lại bài này',type='primary'):
        progress['drafts'].pop(test['id'],None)
        for k in list(st.session_state):
            if k.startswith(f'ans-{test["id"]}-'):
                del st.session_state[k]
        st.session_state.pop('result_id',None)
        save()
        st.rerun()


def practice(test):
    if st.button('← Về kho đề'):
        st.session_state.pop('active',None)
        st.session_state.pop('result_id',None)
        st.session_state.pop('show_review',None)
        st.rerun()
    st.html(f'<div class="eyebrow">{test["skill"].upper()} / YOUR PRACTICE</div>')
    st.title(test['title'])
    item=next((h for h in progress['history'] if h['id']==st.session_state.get('result_id')),None)
    if item:
        result_view(item,test)
        return
    main,side=st.columns([2.3,1],gap='large')
    with main:
        if test['skill']=='listening':
            audio_panel(test)
        papers=[r for r in test['resources'] if resources[r]['role']=='paper']
        rid=st.selectbox('Đề gốc',papers,format_func=lambda r:resources[r]['name'])
        st.caption('Đọc và làm theo số câu trong đề gốc. Một số PDF chứa cả Listening và Reading; chuyển đến phần tương ứng. Có thể chọn văn bản trong bản Word để đánh dấu tạm thời.')
        viewer(rid,test['id'])
    with side:
        clock_panel(test)
        answers_panel(test)


def history():
    st.title('Nhìn lại hành trình')
    st.caption('Mỗi lượt luyện là một bước tiến của bạn.')
    if not progress['history']:
        st.info('Chưa có lượt luyện. Chọn một bài trong Kho đề để bắt đầu.')
    for h in progress['history']:
        with st.container(border=True):
            a,b=st.columns([4,1])
            a.subheader(f"{h['skill'].title()} · {h['title']}")
            a.caption(f"{h['date'][:10]} · {h['score']}/{h['total']} câu đã chấm")
            if b.button('Xem lại →',key=h['id']):
                st.session_state.active=h['test_id']
                st.session_state.result_id=h['id']
                st.session_state.show_review=True
                st.rerun()


def backup():
    st.title('Sao lưu & hướng dẫn')
    st.write('Bingo lưu câu trả lời khi bạn rời ô nhập. Trên máy cá nhân, tiến độ nằm trong thư mục .bingo. Trên Streamlit Cloud, dữ liệu trên ổ đĩa có thể mất khi ứng dụng khởi động lại; hãy tải bản sao lưu sau mỗi buổi học.')
    st.download_button('↓ Tải bản sao lưu tiến độ',json.dumps(progress,ensure_ascii=False,indent=2).encode('utf-8'),file_name='bingo-progress.json',mime='application/json',type='primary')
    uploaded=st.file_uploader('Khôi phục tiến độ từ Bingo',type=['json'])
    if uploaded and st.button('Khôi phục bản sao lưu'):
        try:
            if uploaded.size>5_000_000:
                raise ValueError()
            restored=json.loads(uploaded.getvalue())
            if not isinstance(restored.get('drafts'),dict) or not isinstance(restored.get('history'),list) or not isinstance(restored.get('favorites'),list):
                raise ValueError()
            if any(tid not in by_id for tid in restored['drafts']) or any(not isinstance(h,dict) or h.get('test_id') not in by_id or not all(k in h for k in ['id','title','skill','date','responses','results','score','total']) for h in restored['history']):
                raise ValueError()
            for tid,d in restored['drafts'].items():
                if not isinstance(d,dict) or not isinstance(d.get('answers'),dict) or not isinstance(d.get('remaining'),(int,float)):
                    raise ValueError()
                if any(k not in {str(i) for i in range(1,41)} or not isinstance(v,str) or len(v)>120 for k,v in d['answers'].items()):
                    raise ValueError()
                d['deadline']=None
            st.session_state.progress=restored
            write_json(STATE,restored)
            for key in list(st.session_state):
                if key.startswith('ans-'):
                    del st.session_state[key]
            st.success('Đã khôi phục. Chọn Kho đề để tiếp tục.')
            st.rerun()
        except (ValueError,TypeError,KeyError):
            st.error('Bản sao lưu không hợp lệ. Chọn file JSON được xuất từ Bingo.')
    st.divider()
    st.subheader('Dữ liệu đề thi')
    st.write(f"Đã lập danh mục {len(tests)} bài. {sum(t['key_count']==40 for t in tests)} bài có khóa chấm đủ 40 câu. Các bài thiếu audio hoặc khóa chấm được ghi rõ trong kho đề.")
    st.write('Ở máy này, Bingo đọc trực tiếp hai ZIP gốc. Trên cloud, ứng dụng tải gói mã hóa của bài bạn đang chọn từ GitHub Releases. Cần cấu hình BINGO_PASSWORD, DATA_REPOSITORY, DATA_RELEASE và DATA_KEY trong Streamlit Secrets.')
    st.caption('Giao diện dựa trên Basic của WebThemez (CC BY 3.0), được điều chỉnh cho học IELTS. Đề thi và audio là tài liệu do chủ ứng dụng cung cấp.')


if page=='Sao lưu & hướng dẫn':
    backup()
elif page=='Lịch sử' and st.session_state.get('show_review') and st.session_state.get('active') in by_id:
    practice(by_id[st.session_state.active])
elif page=='Lịch sử':
    history()
elif st.session_state.get('active') in by_id:
    practice(by_id[st.session_state.active])
else:
    library()

st.html('<div class="footer">Bingo · Your personal IELTS practice &nbsp; / &nbsp; Basic theme adapted from <a href="https://webthemez.com/" target="_blank" rel="noopener">WebThemez</a> · CC BY 3.0</div>')
