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
EXAM_HTML=r'''<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}
html,body{height:100%;margin:0;overflow:hidden}
body{font:16px/1.5 Arial,Helvetica,sans-serif;color:#222;background:#fff;display:flex;flex-direction:column}
[hidden]{display:none!important}
button{font:inherit;cursor:pointer}
button:disabled{opacity:.45;cursor:default}

/* ---------- top bar ---------- */
#top{flex:none;display:flex;align-items:center;gap:6px;height:56px;padding:0 12px;background:#f7f7f7;border-bottom:1px solid #ddd}
#top .brand{font:700 20px Arial,sans-serif;color:#777;margin:0 10px 0 4px;white-space:nowrap}
#top .tab{display:flex;align-items:center;height:100%;padding:0 16px;color:#666;border:0;background:none;font-size:17px}
#top .tab.active{background:#ececec;color:#333}
#top .title{color:#888;font-size:14px;margin-left:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
#top .spacer{flex:1}
.link{border:0;background:none;color:#2f78c4;font-size:15px;padding:8px 10px;border-radius:4px;white-space:nowrap}
.link:hover{background:#e9f1fa}
.link[aria-pressed=true]{background:#dcebfa}
#mobileTabs{display:none}

/* ---------- panes ---------- */
#main{flex:1;min-height:0;display:flex;position:relative}
#left{flex:none;width:50%;min-width:0;display:flex;flex-direction:column;background:#fffff2}
#right{flex:1;min-width:0;display:flex;flex-direction:column;background:#fff}
#divider{flex:none;width:22px;background:#555;cursor:col-resize;position:relative;touch-action:none}
#divider::after{content:"";position:absolute;left:8px;top:50%;width:6px;height:36px;margin-top:-18px;border-left:1px solid #999;border-right:1px solid #999}
#divider:hover,#divider.drag{background:#3d3d3d}
.paneHead{flex:none;display:flex;flex-wrap:wrap;align-items:center;gap:6px;padding:7px 10px;border-bottom:1px solid #e3e3c8;background:#f6f6df;font-size:13px}
#right .paneHead{background:#f4f4f4;border-bottom-color:#e2e2e2}
.paneHead select,.paneHead input[type=number]{font:13px Arial,sans-serif;padding:4px 6px;border:1px solid #c9c9b0;border-radius:3px;background:#fff;max-width:230px}
.paneHead .sep{width:1px;height:20px;background:#d5d5b8;margin:0 4px}
.tool{min-width:30px;height:30px;padding:0 9px;border:1px solid #c9c9b0;background:#fff;border-radius:3px;font-size:13px;color:#444}
.tool[aria-pressed=true]{outline:2px solid #2f78c4;outline-offset:1px}
.tool.sw{width:30px;padding:0}
.yellow{background:#ffe56b}.green{background:#bce89c}.blue{background:#a6ddff}.pink{background:#ffbfda}
.pageNav{display:flex;align-items:center;gap:4px}
.scroll{flex:1;min-height:0;overflow:auto;overscroll-behavior:contain;scrollbar-gutter:stable}
#docWrap{position:relative;padding:14px 12px 40px}
#document{position:relative;margin:0 auto;max-width:100%}
#document.text{font:calc(17px*var(--zoom,1))/1.7 Arial,Helvetica,sans-serif;color:#111;overflow-wrap:anywhere}
#document.text p{margin:0 0 14px;white-space:pre-wrap}
#document.text table{border-collapse:collapse;max-width:100%;margin:16px 0}
#document.text td{border:1px solid #d8d8b8;padding:6px 8px;vertical-align:top}
#document.text img{max-width:100%;height:auto}
#document.image{width:calc(100%*var(--zoom,1));line-height:0;user-select:none;touch-action:pan-y;background:#fff;box-shadow:0 0 0 1px #e0e0c8}
#document.image.drawing{touch-action:none;cursor:crosshair}
#document.image>img{display:block;width:100%;pointer-events:none}
#document.pages{width:calc(100%*var(--zoom,1));max-width:none;user-select:none;touch-action:pan-y}
#document.pages.drawing{touch-action:none;cursor:crosshair}
#document.pages .pg{position:relative;width:100%;line-height:0;background:#fff;box-shadow:0 0 0 1px #e0e0c8,0 2px 8px #0002;margin:0 0 16px}
#document.pages .pg>img{display:block;width:100%;height:100%;pointer-events:none}
#document.loading{opacity:.45;transition:opacity .15s}
.region{position:absolute;opacity:.43;mix-blend-mode:multiply}
.preview{pointer-events:none;border:1px dashed #6b7d20;z-index:5}
body.erasing [data-mark-id]{cursor:pointer}
mark{color:inherit;border-radius:2px;padding:1px 0}
.empty{padding:40px 24px;color:#777;text-align:center;line-height:1.6}

/* ---------- answer sheet ---------- */
#sheet{padding:10px 22px 60px;max-width:720px}
.rule{margin:0 0 6px;padding:10px 0 4px;font-size:14px;color:#555;line-height:1.6}
.group{margin-top:8px;border-top:3px solid #f5a623}
.group:first-of-type{margin-top:0}
.group h2{margin:18px 0 4px;font:400 30px Arial,sans-serif;color:#222}
.group .sub{color:#777;font-size:13px;margin-bottom:10px}
.row{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:6px 8px;margin:0 -8px;border-radius:6px}
.row.active{background:#eef5fd}
.row .n{flex:none;width:30px;font-weight:700;font-size:17px;color:#333;text-align:right}
.row input{flex:1 1 220px;min-width:0;max-width:340px;font:16px Arial,sans-serif;padding:7px 10px;border:1px solid #aaa;border-radius:4px;background:#fff}
.row input:focus{outline:2px solid #2f78c4;outline-offset:-1px;border-color:#2f78c4}
.row.done input{border-color:#2f78c4;background:#f3f8fe}
.chips{flex:1 0 100%;display:none;gap:5px;flex-wrap:wrap;padding-left:40px;margin-top:2px}
.row.active .chips{display:flex}
.chips button{padding:3px 9px;border:1px solid #bbb;border-radius:12px;background:#fff;font-size:12px;color:#444}
.chips button:hover{background:#eaf2fb;border-color:#2f78c4}
.chips .gap{width:8px}

/* ---------- bottom palette ---------- */
#bottom{flex:none;display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:6px 14px 7px;background:#fcebd2;border-top:1px solid #f0c98d}
#pal{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1 1 520px}
#palTop{display:flex;align-items:center;flex-wrap:wrap;gap:6px 8px}
#parts{display:flex;gap:6px;flex-wrap:wrap}
#palTop .label{font:700 15px Arial,sans-serif;color:#333;margin-right:2px;white-space:nowrap}
.part{padding:2px 10px;border:1px solid #d9b27a;border-radius:14px;background:#fff;font-size:12px;color:#555}
.part.active{background:#333;border-color:#333;color:#fff}
#circles{display:flex;flex-wrap:nowrap;gap:5px;padding:3px 4px;overflow-x:auto;scrollbar-width:none}
#circles::-webkit-scrollbar{display:none}
.c{flex:none;width:30px;height:30px;border-radius:50%;border:1px solid #b9b9b9;background:#fff;font:700 13px Arial,sans-serif;color:#222;padding:0}
.c.done{background:#2f93ee;border-color:#2f93ee;color:#fff}
.c.cur{box-shadow:0 0 0 2px #f5a623}
#legend{display:flex;gap:12px;font-size:12px;color:#555;align-items:center;margin-left:auto;white-space:nowrap}
#legend i{display:inline-block;width:11px;height:11px;border-radius:50%;border:1px solid #aaa;background:#fff;vertical-align:-2px;margin-right:5px}
#legend i.d{background:#2f93ee;border-color:#2f93ee}
#clockBox{display:flex;align-items:center;gap:8px}
#timer{background:#000;color:#fff;font:700 22px/1 "Courier New",monospace;padding:6px 10px;border-radius:6px;min-width:84px;text-align:center;letter-spacing:1px}
#timer.low{color:#ff8b8b}
#timer.paused{color:#9a9a9a}
#pp{width:30px;height:30px;border-radius:50%;border:1px solid #c9a56a;background:#fff;font-size:15px}
#acts{display:flex;gap:8px;margin-left:auto}
.act{display:flex;align-items:center;gap:6px;border:0;border-radius:5px;color:#fff;font-size:15px;padding:7px 14px}
.act svg{width:16px;height:16px;fill:currentColor}
#submit{background:#3fbf4a}#review{background:#2e74be}#solution{background:#f4ae44}
.act:hover:not(:disabled){filter:brightness(1.07)}
#status{font-size:12px;color:#888;margin-right:8px;white-space:nowrap}

/* ---------- modal ---------- */
#modal{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:#0006;z-index:50;padding:16px}
#modal.open{display:flex}
.box{background:#fff;border-radius:8px;max-width:560px;width:100%;max-height:90vh;overflow:auto;padding:22px 24px;box-shadow:0 10px 40px #0005}
.box h3{margin:0 0 8px;font-size:22px}
.box p{margin:6px 0 14px;color:#444}
.box .btns{display:flex;gap:10px;justify-content:flex-end;margin-top:14px}
.box .btns button{padding:9px 18px;border-radius:5px;border:1px solid #bbb;background:#fff}
.box .btns .go{background:#3fbf4a;border-color:#3fbf4a;color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(46px,1fr));gap:8px;margin:10px 0}
.grid .c{width:46px;height:46px;font-size:16px}
.sum{display:flex;gap:18px;font-size:14px;color:#444}

/* ---------- small screens ---------- */
@media(max-width:1100px){#legend{display:none}}
@media(max-width:820px){
 #divider{display:none}
 #left,#right{width:100%!important;flex:1}
 #main[data-pane=left] #right,#main[data-pane=right] #left{display:none}
 #mobileTabs{display:flex}
 #top .tab,#top .title,#top .hide-m{display:none}
 .c{width:30px;height:30px;font-size:13px}
 #bottom{padding:6px 10px 8px;gap:8px}
 #pal{flex:1 1 100%;gap:4px}
 #palTop .label,#legend{display:none}
 #palTop,#circles,#parts{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none}
 .part{white-space:nowrap}
 .c{flex:none}
 #clockBox{flex:none}
 #acts{flex:1;justify-content:flex-end;gap:6px}
 .act svg{display:none}
 #timer{font-size:18px;min-width:76px;padding:5px 8px}
 .act{padding:7px 10px;font-size:14px}
 #acts{margin-left:0}
 #sheet{padding:8px 12px 40px}
 .group h2{font-size:24px}
}
@media print{#top,#bottom,#divider,.paneHead,#right{display:none!important}#left{width:100%!important}.scroll{overflow:visible}}
</style></head>
<body>
<div id="top" role="banner">
 <button class="link" id="back" title="Thoát và lưu tiến độ">← Kho đề</button>
 <span class="brand">Bingo</span>
 <button class="tab active" id="skillTab" tabindex="-1"></button>
 <span class="title" id="title"></span>
 <span class="spacer"></span>
 <span id="mobileTabs">
  <button class="link" id="mtLeft" aria-pressed="true">Đề</button>
  <button class="link" id="mtRight" aria-pressed="false">Trả lời</button>
 </span>
 <span id="status" role="status"></span>
 <button class="link hide-m" id="zoom" title="Đổi cỡ chữ / thu phóng">Larger Text</button>
 <button class="link hide-m" id="print" title="In đề">Print</button>
</div>

<div id="main" data-pane="left">
 <section id="left" aria-label="Đề bài">
  <div class="paneHead" id="leftHead">
   <select id="paper" aria-label="Chọn tài liệu đề"></select>
   <span class="pageNav" id="pageNav">
    <button class="tool" id="prev" aria-label="Trang trước">‹</button>
    <span id="pageLabel"></span>
    <button class="tool" id="next" aria-label="Trang sau">›</button>
   </span>
   <select id="view" aria-label="Cách xem"><option value="image">Trang gốc</option><option value="text">Văn bản</option></select>
   <span class="sep"></span>
   <button class="tool sw yellow" data-color="yellow" aria-label="Tô vàng" aria-pressed="true"></button>
   <button class="tool sw green" data-color="green" aria-label="Tô xanh lá" aria-pressed="false"></button>
   <button class="tool sw blue" data-color="blue" aria-label="Tô xanh dương" aria-pressed="false"></button>
   <button class="tool sw pink" data-color="pink" aria-label="Tô hồng" aria-pressed="false"></button>
   <button class="tool" id="draw" aria-pressed="true" title="Bật: kéo/bôi chọn để tô">Bút tô</button>
   <button class="tool" id="apply" disabled>Tô đoạn chọn</button>
   <button class="tool" id="erase" aria-pressed="false">Xóa nét</button>
   <button class="tool" id="undo">Hoàn tác</button>
   <button class="tool" id="clear">Xóa hết</button>
  </div>
  <div class="scroll" id="leftScroll"><div id="docWrap"><article id="document" aria-label="Bài đọc và câu hỏi"></article></div></div>
 </section>
 <div id="divider" role="separator" aria-orientation="vertical" aria-label="Kéo để đổi kích thước hai khung" tabindex="0"></div>
 <section id="right" aria-label="Phiếu trả lời">
  <div class="paneHead"><strong id="sheetTitle">Phiếu trả lời</strong><span id="sheetCount" style="color:#666"></span></div>
  <div class="scroll" id="rightScroll"><div id="sheet"></div></div>
 </section>
</div>

<div id="bottom">
 <div id="pal">
  <div id="palTop"><span class="label">Question Palette</span><span id="parts"></span><div id="legend"><span><i class="d"></i>answered</span><span><i></i>unanswered</span></div></div>
  <div id="circles" role="group" aria-label="Danh sách câu hỏi"></div>
 </div>
 <div id="clockBox"><div id="timer" role="timer" aria-live="off">00:00</div><button id="pp" title="Tạm dừng / Tiếp tục" aria-label="Tạm dừng hoặc tiếp tục">❚❚</button></div>
 <div id="acts">
  <button class="act" id="submit"><svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>Submit</button>
  <button class="act" id="review"><svg viewBox="0 0 24 24"><path d="M3 3h5v5H3zm7 0h5v5h-5zm7 0h4v5h-4zM3 10h5v5H3zm7 0h5v5h-5zm7 0h4v5h-4zM3 17h5v4H3zm7 0h5v4h-5zm7 0h4v4h-4z"/></svg>Review</button>
  <button class="act" id="solution"><svg viewBox="0 0 24 24"><path d="M12.65 10A6 6 0 1 0 11 14.65L13 17h2v2h2v2h4v-4l-8.35-7zM7 9a2 2 0 1 1 0-4 2 2 0 0 1 0 4z"/></svg>Solution</button>
 </div>
</div>

<div id="modal" role="dialog" aria-modal="true"><div class="box" id="box"></div></div>

<script>
(()=>{'use strict';
const $=id=>document.getElementById(id);
const doc=$('document'),leftScroll=$('leftScroll'),rightScroll=$('rightScroll');
const colors={yellow:'#ffe56b',green:'#bce89c',blue:'#a6ddff',pink:'#ffbfda'};
const TOTAL=40;
const QUICK=[['TRUE','FALSE','NOT GIVEN'],['YES','NO','NOT GIVEN'],['A','B','C','D','E','F','G','H'],['i','ii','iii','iv','v','vi','vii','viii']];

let args=null,session=null;
let answers={},answersUpdated=0,groups=[],activeGroup=0,currentQ=0;
let state={marks:[],updated:0},undoStack=[],docKey=null;
let color='yellow',erasing=false,drawing=!matchMedia('(pointer:coarse)').matches,pending=null,anchor=null,preview=null;
let pgNow=1,anchorPg=null,pgRaf=0;
const isImg=d=>!!d&&(d.kind==='image'||d.kind==='pages');
let zoomLevel=0;const ZOOMS=[1,1.2,1.45,1.75];
let deadline=0,remaining=0,running=false,timedOut=false,tickHandle=0,sendTimer=0,lastHeight=0,booted=false;

/* ---------- Streamlit bridge ---------- */
function send(type,rest={}){parent.postMessage({isStreamlitMessage:true,type,...rest},'*')}
function emit(type,extra={}){
 clearTimeout(sendTimer);
 send('streamlit:setComponentValue',{dataType:'json',value:{session,type,nonce:Date.now().toString(36)+Math.random().toString(36).slice(2),answers,remaining:curRemaining(),running,...extra}});
}
function queueAnswers(){clearTimeout(sendTimer);setStatus('Đang lưu…');sendTimer=setTimeout(()=>{emit('answers');setStatus('Đã lưu')},800)}
function setStatus(t){$('status').textContent=t}

/* fit this iframe to the visible viewport so the page itself never scrolls */
function fit(){
 let h=800;
 try{const fe=window.frameElement;if(fe){
  fe.style.width='100%';
  const top=fe.getBoundingClientRect().top;
  h=Math.max(520,Math.floor(parent.innerHeight-Math.max(0,top)-2));
 }}catch(e){h=Math.max(520,innerHeight||800)}
 if(h!==lastHeight){lastHeight=h;send('streamlit:setFrameHeight',{height:h})}
}
try{parent.addEventListener('resize',fit)}catch(e){}
addEventListener('resize',fit);

/* ---------- storage mirror (survives cloud restarts) ---------- */
const akey=()=>'bingo-exam-answers-v1:'+args.test.id+':'+args.created;
function saveLocal(){try{localStorage.setItem(akey(),JSON.stringify({answers,updated:answersUpdated}))}catch(e){}}
function readLocal(){try{return JSON.parse(localStorage.getItem(akey()))}catch(e){return null}}
const hkey=()=>'bingo-highlights-v1:'+args.doc.document_key;
function saveHL(){try{localStorage.setItem(hkey(),JSON.stringify(state))}catch(e){}}
function readHL(){try{return JSON.parse(localStorage.getItem(hkey()))}catch(e){return null}}

const tkey=()=>'bingo-exam-timer-v1:'+session,ukey=()=>'bingo-exam-ui-v1:'+session;
function saveTimer(){try{localStorage.setItem(tkey(),JSON.stringify({remaining:curRemaining(),running,at:Date.now()}))}catch(e){}}
function readTimer(){try{return JSON.parse(localStorage.getItem(tkey()))}catch(e){return null}}
let uiTimer=0;
function saveUI(){clearTimeout(uiTimer);uiTimer=setTimeout(()=>{try{localStorage.setItem(ukey(),JSON.stringify({q:currentQ,rs:rightScroll.scrollTop}))}catch(e){}},250)}
function readUI(){try{return JSON.parse(localStorage.getItem(ukey()))}catch(e){return null}}

/* ---------- timer ---------- */
function curRemaining(){return running?Math.max(0,Math.round((deadline-Date.now())/1000)):remaining}
function fmt(s){return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}
function paintTimer(){
 const s=curRemaining(),t=$('timer');
 t.textContent=fmt(s);t.classList.toggle('low',s<=300&&s>0);t.classList.toggle('paused',!running);
 $('pp').textContent=running?'❚❚':'▶';
 if(running&&s<=0&&!timedOut){timedOut=true;running=false;remaining=0;paintTimer();showTimeout()}
}
function startClock(){deadline=Date.now()+remaining*1000;running=true;paintTimer();saveTimer()}
function pauseClock(){remaining=curRemaining();running=false;paintTimer();saveTimer()}
$('pp').addEventListener('click',()=>{if(timedOut)return;running?pauseClock():startClock();emit('timer')});
function tick(){paintTimer();saveTimer();fit()}

/* ---------- groups / sheet ---------- */
function buildGroups(){
 groups=args.test.skill==='reading'?[[1,13,'Passage 1'],[14,26,'Passage 2'],[27,40,'Passage 3']]:[[1,10,'Part 1'],[11,20,'Part 2'],[21,30,'Part 3'],[31,40,'Part 4']];
}
function groupOf(q){return Math.max(0,groups.findIndex(g=>q>=g[0]&&q<=g[1]))}
function has(q){return String(answers[q]||'').trim().length>0}
function answeredIn(g){let n=0;for(let q=groups[g][0];q<=groups[g][1];q++)if(has(q))n++;return n}
function answeredCount(){let n=0;for(let q=1;q<=TOTAL;q++)if(has(q))n++;return n}

function buildSheet(){
 const sheet=$('sheet');sheet.replaceChildren();
 const intro=document.createElement('div');intro.className='rule';
 intro.textContent=args.test.skill==='reading'
  ?'Đọc đề ở khung bên trái và ghi đáp án vào các ô bên dưới. Câu nhận định: TRUE / FALSE / NOT GIVEN (hoặc YES / NO / NOT GIVEN). Câu chọn: nhập chữ cái. Câu điền: làm theo giới hạn từ trong đề.'
  :'Nghe audio ở thanh phía trên, đọc đề bên trái và ghi đáp án vào các ô bên dưới. Làm theo giới hạn từ trong đề.';
 sheet.append(intro);
 groups.forEach((g,gi)=>{
  const sec=document.createElement('section');sec.className='group';sec.id='group-'+gi;
  const h=document.createElement('h2');h.textContent=`Questions ${g[0]} - ${g[1]}`;sec.append(h);
  const sub=document.createElement('div');sub.className='sub';sub.textContent=g[2];sec.append(sub);
  for(let q=g[0];q<=g[1];q++){
   const row=document.createElement('div');row.className='row';row.id='row-'+q;row.dataset.q=q;
   const n=document.createElement('span');n.className='n';n.textContent=q;
   const input=document.createElement('input');input.type='text';input.maxLength=120;input.autocomplete='off';input.spellcheck=false;input.id='in-'+q;input.setAttribute('aria-label','Đáp án câu '+q);input.value=answers[q]||'';
   const chips=document.createElement('div');chips.className='chips';
   QUICK.forEach((set,si)=>{if(si)chips.append(Object.assign(document.createElement('span'),{className:'gap'}));set.forEach(v=>{const b=document.createElement('button');b.type='button';b.textContent=v;b.tabIndex=-1;b.addEventListener('mousedown',e=>e.preventDefault());b.addEventListener('click',()=>{input.value=v;setAnswer(q,v);input.focus()});chips.append(b)})});
   input.addEventListener('input',()=>setAnswer(q,input.value));
   input.addEventListener('focus',()=>setCurrent(q,false));
   input.addEventListener('blur',()=>{if(sendTimer){emit('answers');setStatus('Đã lưu')}});
   input.addEventListener('keydown',e=>{if(e.key==='Enter'||(e.key==='ArrowDown')){e.preventDefault();goTo(Math.min(TOTAL,q+1))}else if(e.key==='ArrowUp'){e.preventDefault();goTo(Math.max(1,q-1))}});
   row.append(n,input,chips);sec.append(row);
  }
  sheet.append(sec);
 });
 updateAll();
}
function setAnswer(q,v){
 const t=String(v).slice(0,120);
 if(t.trim())answers[q]=t;else delete answers[q];
 answersUpdated=Date.now();saveLocal();updateAll();queueAnswers();
}
function setCurrent(q,scroll){
 currentQ=q;saveUI();
 document.querySelectorAll('.row.active').forEach(r=>r.classList.remove('active'));
 const row=$('row-'+q);if(row)row.classList.add('active');
 const g=groupOf(q);if(g!==activeGroup){activeGroup=g;paintPalette()}else paintCircles();
 if(scroll&&row)row.scrollIntoView({block:'center',behavior:'smooth'});
}
function goTo(q){
 if($('main').dataset.pane==='left'&&matchMedia('(max-width:820px)').matches)showPane('right');
 setCurrent(q,true);const i=$('in-'+q);if(i)setTimeout(()=>i.focus({preventScroll:true}),60);
}
function updateAll(){
 for(let q=1;q<=TOTAL;q++){const r=$('row-'+q);if(r)r.classList.toggle('done',has(q))}
 $('sheetCount').textContent=` · ${answeredCount()}/${TOTAL} câu đã trả lời`;
 paintPalette();
}

/* ---------- palette ---------- */
function paintPalette(){
 const parts=$('parts');parts.replaceChildren();
 groups.forEach((g,gi)=>{const b=document.createElement('button');b.className='part'+(gi===activeGroup?' active':'');b.textContent=`${g[2]} · ${answeredIn(gi)}/${g[1]-g[0]+1}`;b.addEventListener('click',()=>{activeGroup=gi;paintPalette();const sec=$('group-'+gi);if(sec)rightScroll.scrollTo({top:sec.offsetTop-4,behavior:'smooth'});if(matchMedia('(max-width:820px)').matches)showPane('right')});parts.append(b)});
 paintCircles();
}
function paintCircles(){
 const box=$('circles');box.replaceChildren();
 const g=groups[activeGroup];
 for(let q=g[0];q<=g[1];q++){const b=document.createElement('button');b.className='c'+(has(q)?' done':'')+(q===currentQ?' cur':'');b.textContent=q;b.setAttribute('aria-label',`Câu ${q}${has(q)?' đã trả lời':' chưa trả lời'}`);b.addEventListener('click',()=>goTo(q));box.append(b)}
 const cur=box.querySelector('.cur');if(cur){const a=cur.getBoundingClientRect(),r=box.getBoundingClientRect();if(a.left<r.left)box.scrollLeft-=r.left-a.left+8;else if(a.right>r.right)box.scrollLeft+=a.right-r.right+8}
}
rightScroll.addEventListener('scroll',()=>{
 let g=0;const top=rightScroll.scrollTop+80;
 groups.forEach((_,gi)=>{const s=$('group-'+gi);if(s&&s.offsetTop<=top)g=gi});
 if(g!==activeGroup){activeGroup=g;paintPalette()}
 saveUI();
},{passive:true});

/* ---------- modals ---------- */
function openModal(html,wire){const box=$('box');box.innerHTML=html;$('modal').classList.add('open');if(wire)wire(box);const f=box.querySelector('[data-focus]');if(f)f.focus()}
function closeModal(){$('modal').classList.remove('open')}
$('modal').addEventListener('mousedown',e=>{if(e.target===$('modal')&&!timedOut)closeModal()});
addEventListener('keydown',e=>{if(e.key==='Escape'&&!timedOut)closeModal()});
function confirmSubmit(kind){
 const left=TOTAL-answeredCount();
 const solution=kind==='solution';
 openModal(`<h3>${solution?'Xem lời giải?':'Nộp bài?'}</h3><p>${left?`Bạn còn <b>${left}</b> câu chưa trả lời. `:'Bạn đã trả lời đủ 40 câu. '}${solution?'Xem lời giải sẽ nộp bài và kết thúc lượt làm này.':'Sau khi nộp, bạn sẽ thấy kết quả và đáp án.'}</p><div class="btns"><button id="mNo" data-focus>Làm tiếp</button><button id="mYes" class="go">${solution?'Nộp bài & xem lời giải':'Nộp bài'}</button></div>`,b=>{
  b.querySelector('#mNo').onclick=closeModal;
  b.querySelector('#mYes').onclick=()=>{closeModal();clearInterval(tickHandle);pauseClock();emit(kind,{reason:'user'})};
 });
}
function showReview(){
 const left=TOTAL-answeredCount();
 let grid='';for(let q=1;q<=TOTAL;q++)grid+=`<button class="c${has(q)?' done':''}" data-q="${q}" aria-label="Câu ${q}">${q}</button>`;
 openModal(`<h3>Xem lại bài làm</h3><div class="sum"><span>Đã trả lời: <b>${TOTAL-left}</b></span><span>Chưa trả lời: <b>${left}</b></span></div><div class="grid">${grid}</div><div class="btns">${left?'<button id="mFirst">Đến câu đầu tiên chưa làm</button>':''}<button id="mClose" data-focus>Đóng</button></div>`,b=>{
  b.querySelectorAll('.grid .c').forEach(c=>c.onclick=()=>{closeModal();goTo(+c.dataset.q)});
  b.querySelector('#mClose').onclick=closeModal;
  const f=b.querySelector('#mFirst');if(f)f.onclick=()=>{closeModal();for(let q=1;q<=TOTAL;q++)if(!has(q)){goTo(q);break}};
 });
}
function showTimeout(){
 openModal(`<h3>Hết giờ</h3><p>Thời gian làm bài đã kết thúc. Bài làm của bạn sẽ được nộp và chấm.</p><div class="btns"><button class="go" id="mOk" data-focus>Xem kết quả</button></div>`,b=>{b.querySelector('#mOk').onclick=()=>{closeModal();emit('submit',{reason:'timeout'})}});
 emit('submit',{reason:'timeout'});
}
$('submit').addEventListener('click',()=>confirmSubmit('submit'));
$('solution').addEventListener('click',()=>confirmSubmit('solution'));
$('review').addEventListener('click',showReview);
$('back').addEventListener('click',()=>{pauseClock();emit('back')});
$('print').addEventListener('click',()=>print());
$('zoom').addEventListener('click',()=>{zoomLevel=(zoomLevel+1)%ZOOMS.length;document.documentElement.style.setProperty('--zoom',ZOOMS[zoomLevel]);$('zoom').setAttribute('aria-pressed',String(zoomLevel>0));try{localStorage.setItem('bingo-exam-zoom',String(zoomLevel))}catch(e){}});

/* ---------- panes ---------- */
function showPane(p){$('main').dataset.pane=p;$('mtLeft').setAttribute('aria-pressed',String(p==='left'));$('mtRight').setAttribute('aria-pressed',String(p==='right'))}
$('mtLeft').onclick=()=>showPane('left');$('mtRight').onclick=()=>showPane('right');
const divider=$('divider'),left=$('left');
function setSplit(pct){pct=Math.max(24,Math.min(76,pct));left.style.width=pct+'%';try{localStorage.setItem('bingo-exam-split',String(pct))}catch(e){}}
divider.addEventListener('pointerdown',e=>{divider.setPointerCapture(e.pointerId);divider.classList.add('drag');document.body.style.userSelect='none'});
divider.addEventListener('pointermove',e=>{if(!divider.classList.contains('drag'))return;const r=$('main').getBoundingClientRect();setSplit((e.clientX-r.left)/r.width*100)});
const endDrag=e=>{divider.classList.remove('drag');document.body.style.userSelect='';try{divider.releasePointerCapture(e.pointerId)}catch(_){}};
divider.addEventListener('pointerup',endDrag);divider.addEventListener('pointercancel',endDrag);
divider.addEventListener('keydown',e=>{const cur=parseFloat(left.style.width)||50;if(e.key==='ArrowLeft'){setSplit(cur-3);e.preventDefault()}if(e.key==='ArrowRight'){setSplit(cur+3);e.preventDefault()}});

/* ---------- document pane ---------- */
function renderHeader(){
 const d=args.doc;
 const sel=$('paper');sel.replaceChildren();
 args.papers.forEach(p=>{const o=document.createElement('option');o.value=p.id;o.textContent=p.name;if(p.id===args.paper)o.selected=true;sel.append(o)});
 sel.hidden=args.papers.length<2;
 const isPdf=d.pages>0;
 $('pageNav').hidden=!isPdf||d.pages<2;
 paintPageNav();
 $('view').hidden=!(isPdf&&d.can_text);
 $('view').value=d.view;
 $('draw').setAttribute('aria-pressed',String(drawing));
}
function paintPageNav(){
 const d=args.doc,paged=d.kind==='pages',n=paged?pgNow:d.page;
 $('pageLabel').textContent=`Trang ${n}/${d.pages}`;
 $('prev').disabled=n<=1;$('next').disabled=n>=d.pages;
}
function pageAtScroll(){
 const lr=leftScroll.getBoundingClientRect();let cur=1;
 doc.querySelectorAll('.pg').forEach((pg,i)=>{if(pg.getBoundingClientRect().top-lr.top<=lr.height*.35)cur=i+1});
 return cur;
}
function scrollToPage(n){
 const pg=doc.querySelector(`.pg[data-p="${n}"]`);if(!pg)return;
 const lr=leftScroll.getBoundingClientRect();
 leftScroll.scrollBy({top:pg.getBoundingClientRect().top-lr.top-8,behavior:'smooth'});
}
leftScroll.addEventListener('scroll',()=>{
 if(!args||args.doc.kind!=='pages'||pgRaf)return;
 pgRaf=requestAnimationFrame(()=>{pgRaf=0;const n=pageAtScroll();if(n!==pgNow){pgNow=n;paintPageNav()}});
},{passive:true});
function renderDoc(){
 const d=args.doc;
 doc.className=d.kind+(drawing&&isImg(d)?' drawing':'');
 if(d.kind==='empty'){doc.className='';doc.innerHTML='<div class="empty"></div>';doc.firstChild.textContent=d.message||'Chưa mở được tài liệu.';return}
 renderMarks();
}
function renderMarks(){
 const d=args.doc,top=leftScroll.scrollTop;
 doc.className=d.kind+(drawing&&isImg(d)?' drawing':'');
 $('draw').hidden=false;
 if(d.kind!=='pages')delete doc.dataset.key;
 if(d.kind==='pages'){
  if(doc.dataset.key!==d.document_key||!doc.querySelector('.pg')){
   doc.replaceChildren();doc.dataset.key=d.document_key;
   d.content.forEach((pg,i)=>{const box=document.createElement('div');box.className='pg';box.dataset.p=i+1;box.style.aspectRatio=pg.w+' / '+pg.h;const img=document.createElement('img');img.src=pg.src;img.alt='Trang đề gốc '+(i+1);box.append(img);doc.append(box)});
  }
  doc.querySelectorAll('.region').forEach(r=>r.remove());
  for(const m of state.marks){const box=doc.querySelector(`.pg[data-p="${m.p}"]`);if(!box)continue;const b=document.createElement('div');b.className='region';b.dataset.markId=m.id;Object.assign(b.style,{left:m.x*100+'%',top:m.y*100+'%',width:m.w*100+'%',height:m.h*100+'%',background:colors[m.color]||colors.yellow});box.append(b)}
 }else if(d.kind==='image'){
  doc.replaceChildren();const img=document.createElement('img');img.src=d.content;img.alt='Trang đề gốc';doc.append(img);
  for(const m of state.marks){const b=document.createElement('div');b.className='region';b.dataset.markId=m.id;Object.assign(b.style,{left:m.x*100+'%',top:m.y*100+'%',width:m.w*100+'%',height:m.h*100+'%',background:colors[m.color]||colors.yellow});doc.append(b)}
 }else{
  doc.innerHTML=d.content;
  const walker=document.createTreeWalker(doc,NodeFilter.SHOW_TEXT);const nodes=[];let n,off=0;
  while(n=walker.nextNode()){nodes.push({node:n,start:off,end:off+n.textContent.length});off+=n.textContent.length}
  for(const it of nodes){
   const hits=state.marks.filter(m=>m.end>it.start&&m.start<it.end);if(!hits.length)continue;
   const bounds=new Set([0,it.end-it.start]);for(const m of hits){bounds.add(Math.max(0,m.start-it.start));bounds.add(Math.min(it.end-it.start,m.end-it.start))}
   const cuts=[...bounds].sort((a,b)=>a-b),frag=document.createDocumentFragment(),text=it.node.textContent;
   for(let i=0;i<cuts.length-1;i++){const a=cuts[i],b=cuts[i+1],hit=[...hits].reverse().find(m=>m.start<it.start+b&&m.end>it.start+a);if(hit){const s=document.createElement('mark');s.dataset.markId=hit.id;s.style.background=colors[hit.color]||colors.yellow;s.textContent=text.slice(a,b);frag.append(s)}else frag.append(document.createTextNode(text.slice(a,b)))}
   it.node.replaceWith(frag);
  }
 }
 leftScroll.scrollTop=top;pending=null;$('apply').disabled=true;
}
function commit(marks){undoStack.push(JSON.parse(JSON.stringify(state.marks)));state={marks:marks,updated:Date.now()};renderMarks();saveHL();emit('highlight',{document_key:args.doc.document_key,annotations:state})}
const mid=()=>Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,9);

document.querySelectorAll('[data-color]').forEach(b=>b.addEventListener('click',()=>{color=b.dataset.color;document.querySelectorAll('[data-color]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));erasing=false;drawing=true;$('erase').setAttribute('aria-pressed','false');$('draw').setAttribute('aria-pressed','true');document.body.classList.remove('erasing');doc.classList.toggle('drawing',isImg(args?.doc))}));
$('draw').addEventListener('click',()=>{drawing=!drawing;$('draw').setAttribute('aria-pressed',String(drawing));doc.classList.toggle('drawing',drawing&&isImg(args.doc));if(drawing){erasing=false;$('erase').setAttribute('aria-pressed','false');document.body.classList.remove('erasing')}});
$('erase').addEventListener('click',()=>{erasing=!erasing;$('erase').setAttribute('aria-pressed',String(erasing));document.body.classList.toggle('erasing',erasing)});
doc.addEventListener('click',e=>{if(!erasing)return;const hit=e.target.closest('[data-mark-id]');if(hit)commit(state.marks.filter(m=>m.id!==hit.dataset.markId))});
function captureSelection(){
 if(!args||args.doc.kind!=='text'||erasing)return null;
 const sel=getSelection();if(!sel||sel.isCollapsed||!sel.rangeCount)return null;
 const r=sel.getRangeAt(0);if(!doc.contains(r.startContainer)||!doc.contains(r.endContainer))return null;
 const b=document.createRange();b.selectNodeContents(doc);b.setEnd(r.startContainer,r.startOffset);const start=b.toString().length;b.setEnd(r.endContainer,r.endOffset);const end=b.toString().length;
 if(end>start){pending={start,end};$('apply').disabled=false;return pending}return null;
}
document.addEventListener('selectionchange',captureSelection);
doc.addEventListener('mouseup',()=>{const p=captureSelection();if(p&&drawing){getSelection().removeAllRanges();commit([...state.marks,{id:mid(),color,...p}])}});
$('apply').addEventListener('mousedown',e=>e.preventDefault());
$('apply').addEventListener('click',()=>{if(!pending)return;const m={id:mid(),color,...pending};getSelection()?.removeAllRanges();commit([...state.marks,m])});
$('undo').addEventListener('click',()=>{if(!undoStack.length)return;state={marks:undoStack.pop(),updated:Date.now()};renderMarks();saveHL();emit('highlight',{document_key:args.doc.document_key,annotations:state})});
$('clear').addEventListener('click',()=>{if(state.marks.length)commit([])});
function pt(e,el){const r=(el||doc).getBoundingClientRect();return{x:Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))}}
doc.addEventListener('pointerdown',e=>{if(!args||!isImg(args.doc)||!drawing||erasing||e.button!==0)return;let host=doc;if(args.doc.kind==='pages'){host=e.target.closest('.pg');if(!host)return}e.preventDefault();anchorPg=host;anchor=pt(e,host);doc.setPointerCapture(e.pointerId);preview=document.createElement('div');preview.className='region preview';preview.style.background=colors[color];host.append(preview)});
doc.addEventListener('pointermove',e=>{if(!anchor)return;const p=pt(e,anchorPg);Object.assign(preview.style,{left:Math.min(anchor.x,p.x)*100+'%',top:Math.min(anchor.y,p.y)*100+'%',width:Math.abs(p.x-anchor.x)*100+'%',height:Math.abs(p.y-anchor.y)*100+'%'})});
doc.addEventListener('pointerup',e=>{if(!anchor)return;const p=pt(e,anchorPg),m={id:mid(),color,x:Math.min(anchor.x,p.x),y:Math.min(anchor.y,p.y),w:Math.abs(p.x-anchor.x),h:Math.abs(p.y-anchor.y)};if(args.doc.kind==='pages')m.p=+anchorPg.dataset.p;anchor=null;anchorPg=null;preview?.remove();preview=null;try{doc.releasePointerCapture(e.pointerId)}catch(_){}if(m.w>.003&&m.h>.003)commit([...state.marks,m])});
doc.addEventListener('pointercancel',()=>{anchor=null;anchorPg=null;preview?.remove();preview=null});

/* ---------- navigation requests to Python ---------- */
function busy(){doc.classList.add('loading')}
$('prev').addEventListener('click',()=>{
 if(args.doc.kind!=='pages'){busy();emit('page',{page:args.doc.page-1});return}
 const n=pageAtScroll(),box=doc.querySelector(`.pg[data-p="${n}"]`);
 const atTop=box&&Math.abs(box.getBoundingClientRect().top-leftScroll.getBoundingClientRect().top)<24;
 scrollToPage(atTop?Math.max(1,n-1):n);
});
$('next').addEventListener('click',()=>{if(args.doc.kind==='pages'){scrollToPage(Math.min(args.doc.pages,pageAtScroll()+1))}else{busy();emit('page',{page:args.doc.page+1})}});
$('paper').addEventListener('change',e=>{busy();emit('paper',{paper:e.target.value})});
$('view').addEventListener('change',e=>{busy();emit('view',{view:e.target.value})});

/* ---------- render from Streamlit ---------- */
function onRender(next){
 const firstForSession=!booted||session!==next.session;
 args=next;
 if(firstForSession){
  booted=true;session=next.session;timedOut=false;
  buildGroups();
  answers={};for(const [k,v] of Object.entries(args.answers||{}))if(String(v).trim())answers[k]=String(v);
  answersUpdated=args.answers_updated||0;
  const loc=readLocal();
  if(loc&&loc.answers&&loc.updated>answersUpdated){answers={};for(const [k,v] of Object.entries(loc.answers))if(String(v).trim())answers[k]=String(v);answersUpdated=loc.updated;setTimeout(()=>emit('answers'),0)}
  currentQ=1;activeGroup=0;
  $('skillTab').textContent=args.test.skill==='reading'?'Reading':'Listening';
  $('title').textContent=args.test.title;
  buildSheet();
  remaining=Math.max(0,Math.round(args.remaining));running=false;
  let wantRun=!!args.running;
  const lt=readTimer();
  if(lt&&typeof lt.remaining==='number'&&lt.at>(args.stamp||0)){remaining=lt.running?Math.max(0,Math.round(lt.remaining-(Date.now()-lt.at)/1000)):Math.max(0,Math.round(lt.remaining));wantRun=!!lt.running}
  if(wantRun&&remaining>0)startClock();else paintTimer();
  if(wantRun&&remaining<=0&&!timedOut){timedOut=true;paintTimer();showTimeout()}
  const ui=readUI();if(ui&&ui.q>=1&&ui.q<=TOTAL){currentQ=ui.q;activeGroup=groupOf(ui.q);paintPalette();const r=$('row-'+ui.q);if(r)r.classList.add('active');setTimeout(()=>{rightScroll.scrollTop=ui.rs||0},0)}
  clearInterval(tickHandle);tickHandle=setInterval(tick,1000);
  try{const sp=parseFloat(localStorage.getItem('bingo-exam-split'));if(sp)setSplit(sp);const z=parseInt(localStorage.getItem('bingo-exam-zoom')||'0',10);if(z>0&&z<ZOOMS.length){zoomLevel=z;document.documentElement.style.setProperty('--zoom',ZOOMS[z]);$('zoom').setAttribute('aria-pressed','true')}}catch(e){}
 }
 renderHeader();
 if(docKey!==args.doc.document_key||firstForSession){
  docKey=args.doc.document_key;undoStack=[];
  state=args.annotations||{marks:[],updated:0};
  const loc=readHL();if(loc&&Array.isArray(loc.marks)&&loc.updated>(state.updated||0)){state=loc;setTimeout(()=>emit('highlight',{document_key:args.doc.document_key,annotations:state}),0)}
  const keepScroll=false;leftScroll.scrollTop=keepScroll?leftScroll.scrollTop:0;pgNow=1;
  doc.classList.remove('loading');renderDoc();
 }else if((args.annotations?.updated||0)>(state.updated||0)){state=args.annotations;renderMarks()}
 doc.classList.remove('loading');
 fit();
}
addEventListener('message',e=>{
 if(e.source!==parent||e.data?.type!=='streamlit:render')return;
 onRender(e.data.args);
});
/* expose for tests */
window.__bingoExam={onRender};
send('streamlit:componentReady',{apiVersion:1});fit();
})();
</script></body></html>
'''
component=components.declare_component('bingo_highlight_reader',path=str(ROOT/'components/reader'))
def _materialize_exam_component():
    """Write the exam screen to disk at start-up so the app works even when only the .py files
    are deployed. Streamlit serves custom components from a folder."""
    import tempfile
    for base in (ROOT/'.bingo', Path(tempfile.gettempdir())/'bingo'):
        folder=base/'exam-component'
        try:
            folder.mkdir(parents=True,exist_ok=True)
            target=folder/'index.html'
            if not target.is_file() or target.read_text(encoding='utf-8')!=EXAM_HTML:
                target.write_text(EXAM_HTML,encoding='utf-8')
            return folder
        except OSError:
            continue
    raise RuntimeError('Không ghi được thư mục tạm cho màn hình làm bài.')


exam_component=components.declare_component('bingo_exam',path=str(_materialize_exam_component()))
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


@st.cache_data(max_entries=3,show_spinner=False)
def pdf_all_pages(data):
    """Render every page once so the exam screen can show the whole paper as one scrolling column."""
    import pypdfium2 as pdfium
    document=pdfium.PdfDocument(data)
    pages=[]
    chars=0
    try:
        for index in range(len(document)):
            page=document[index]
            textpage=page.get_textpage()
            chars+=len(textpage.get_text_range().strip())
            textpage.close()
            bitmap=page.render(scale=min(1.5,1100/max(page.get_width(),1)))
            image=bitmap.to_pil()
            buf=io.BytesIO()
            image.save(buf,format='JPEG',quality=82)
            pages.append({'src':'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode(),'w':image.width,'h':image.height})
            image.close()
            bitmap.close()
            page.close()
    finally:
        document.close()
    return {'count':len(pages),'pages':pages,'can_text':chars>30}


def validate_annotations(value,kind):
    if not isinstance(value,dict) or not isinstance(value.get('marks'),list) or len(value['marks'])>2000:
        raise ValueError('Invalid highlight state')
    marks=[]
    for raw in value['marks']:
        if not isinstance(raw,dict) or raw.get('color') not in COLORS or not isinstance(raw.get('id'),str) or len(raw['id'])>80:
            raise ValueError('Invalid highlight')
        mark={'id':raw['id'],'color':raw['color']}
        fields=['x','y','w','h'] if kind in ('image','pages') else ['start','end']
        for key in fields:
            v=raw.get(key)
            if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v):
                raise ValueError('Invalid highlight coordinate')
            if kind in ('image','pages') and not 0<=v<=1:
                raise ValueError('Highlight outside page')
            if kind=='text' and (int(v)!=v or not 0<=v<=5_000_000):
                raise ValueError('Invalid text offset')
            mark[key]=v
        if kind=='text' and mark['end']<=mark['start']:
            raise ValueError('Empty highlight')
        if kind=='pages':
            page_no=raw.get('p')
            if not isinstance(page_no,int) or isinstance(page_no,bool) or not 1<=page_no<=10000:
                raise ValueError('Invalid page number')
            mark['p']=page_no
        if kind in ('image','pages') and (mark['w']<=0 or mark['h']<=0 or mark['x']+mark['w']>1.001 or mark['y']+mark['h']>1.001):
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
    if extension=='.pdf' and view=='image':
        # Whole paper as one scrolling column; highlights stay stored per page for compatibility.
        allp=pdf_all_pages(data)
        doc.update(kind='pages',content=allp['pages'],pages=allp['count'],page=1,can_text=allp['can_text'],view='image')
        section='pdf-all'
        marks=[]
        updated=0
        saved=progress.setdefault('highlights',{}).setdefault(rid,{})
        for number in range(1,allp['count']+1):
            try:
                one=validate_annotations(saved.get(f'pdf-region-{number}',{'marks':[],'updated':0}),'image')
            except ValueError:
                continue
            updated=max(updated,one['updated'])
            marks.extend({**m,'p':number} for m in one['marks'])
        doc['document_key']=rid+':'+section
        return doc,{'marks':marks,'updated':updated},section
    if extension=='.pdf':
        info=pdf_page(data,max(0,int(page)-1))
        count=info['count']
        page=max(1,min(int(page),count))
        can_text=pdf_all_pages(data)['can_text']
        if not can_text:
            return prepare_document(data,extension,rid,progress,page,'image',word_html)
        doc.update(pages=count,page=page,can_text=can_text,view='text')
        text=info['text'].strip()
        doc.update(kind='text',content='<p>'+html.escape(info['text']).replace('\n','<br>')+'</p>' if text else '<p><i>Trang này không có lớp văn bản. Chuyển sang “Trang gốc” để xem.</i></p>')
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
    store=progress.setdefault('highlights',{}).setdefault(rid,{})
    if kind=='pages':
        # The continuous view keeps one list; split it back into the per-page sections.
        per_page={}
        for mark in clean['marks']:
            per_page.setdefault(mark['p'],[]).append({k:v for k,v in mark.items() if k!='p'})
        for key in [k for k in store if k.startswith('pdf-region-')]:
            if int(key.rsplit('-',1)[1]) not in per_page:
                store[key]={'marks':[],'updated':clean['updated']}
        for number,marks in per_page.items():
            store[f'pdf-region-{number}']={'marks':marks,'updated':clean['updated']}
        return
    store[section]=clean
