"""Best-effort extraction of numbered questions from a Word test paper.

The result is only a convenience for the answer sheet: if a paper does not follow a
recognisable layout the affected questions are simply left out and the sheet falls back
to bare answer boxes.
"""
import io
import re
import zipfile
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
HEADING = re.compile(r'^Questions?\s+(\d{1,2})\s*(?:[-–—]|to|and|&)\s*(\d{1,2})\b', re.I)
NUMBERED = re.compile(r'^(\d{1,2})[.)]?\s+(?=\S)')
LETTERED = re.compile(r'^([A-J])[.)]?\s+(?=\S)')
GAP = re.compile(r'(?<![\d\w])(\d{1,2})\s*(?:[….]{3,}|_{3,}|(?:\.\s){3,}\.?)')
ANY_GAP = re.compile(r'(?:[….]{3,}|_{3,})')
PICK_N = re.compile(r'choose\s+(two|three|four)\s+letters', re.I)
MCQ_HINT = re.compile(r'\bA,\s*B,\s*C,?\s*(?:or|and)?\s*D\b', re.I)
BOILERPLATE = re.compile(r'^(?:write|in boxes?)\b.*(?:answer sheet|boxes?\s+\d)', re.I)
PART_LINE = re.compile(r'(?:READING PASSAGE|(?:LISTENING\s+)?(?:PART|SECTION))\s*\d', re.I)
MAX_TEXT = 260


def _lines(paragraph):
    """Text of one w:p as a list of lines (w:br / w:cr start a new line)."""
    out = ['']
    for node in paragraph.iter():
        tag = node.tag.rsplit('}', 1)[-1]
        if tag == 't':
            out[-1] += node.text or ''
        elif tag in ('br', 'cr'):
            out.append('')
        elif tag == 'tab':
            out[-1] += ' '
    return [re.sub(r'[ \t ]+', ' ', x).strip() for x in out if x.strip()]


def _paragraphs(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        body = ET.fromstring(z.read('word/document.xml')).find(W + 'body')
    return [lines for p in body.iter(W + 'p') if (lines := _lines(p))]


def _sentence_with_gap(text, target):
    """The sentence (or note line) of `text` that holds the gap for `target`; that gap becomes _____."""
    marked = GAP.sub(lambda m: '\x00%s\x00' % m.group(1), text)
    if '\x00%d\x00' % target not in marked:
        return ''
    parts = re.split(r'\n|(?<=[a-z0-9\)\]”"\'\x00])\s*[.!?]\s+(?=[A-Z])', marked)
    sentence = next(p for p in parts if '\x00%d\x00' % target in p).strip()
    sentence = re.sub(r'\x00(\d+)\x00', lambda m: '_____' if int(m.group(1)) == target else '___', sentence)
    if len(sentence) > MAX_TEXT:
        cut = sentence.index('_____')
        sentence = '…' + sentence[max(0, cut - MAX_TEXT // 2):cut + MAX_TEXT // 2] + '…'
    return sentence


def extract_questions(data):
    """Return {'questions': {n: {...}}, 'groups': [...]} for a .docx test paper.

    questions[n] = {'text': str, 'options': [[letter, text], ...], 'shared': bool}
    groups = [{'from': a, 'to': b, 'title': str, 'instructions': [str], 'list': [[letter, text], ...],
               'list_title': str}]
    """
    try:
        paragraphs = _paragraphs(data)
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        return {'questions': {}, 'groups': []}

    questions, groups = {}, []
    group = None
    pick_options = None  # option list of a choose-N-letters question still being filled
    last = None          # last numbered question that may still receive options
    seen_test = 0
    seen_passage1 = 0

    def new_group(a, b, title):
        nonlocal group, last, pick_options
        pick_options = None
        group = {'from': a, 'to': b, 'title': title, 'instructions': [], 'list': [], 'list_title': '',
                 'mcq': False, 'started': False}
        groups.append(group)
        last = None

    for lines in paragraphs:
        first = lines[0]
        # A second test or a second "Passage 1" means the file bundles several tests: keep the first.
        if re.match(r'^TEST\s+\d+\b', first, re.I):
            seen_test += 1
            if seen_test > 1:
                break
        if PART_LINE.fullmatch(first) and re.search(r'\b1$', first):
            seen_passage1 += 1
            if seen_passage1 > 1:
                break

        m = HEADING.match(first)
        if m and int(m.group(1)) <= int(m.group(2)) <= 40:
            new_group(int(m.group(1)), int(m.group(2)), re.sub(r'\s*\(.*', '', first).strip())
            rest = lines[1:]
            if not rest:
                continue
            lines = rest
            first = lines[0]
        elif group is None:
            continue
        if PART_LINE.fullmatch(first):
            group = None
            last = None
            continue

        lo, hi = group['from'], group['to']
        text = ' '.join(lines)

        def accept(n):
            # True when n belongs to this group; a heading that undercounts is stretched to fit.
            nonlocal hi
            if lo <= n <= hi:
                return True
            if group['started'] and n == hi + 1 and n <= 40 and n not in questions:
                hi = group['to'] = n
                return True
            return False

        # "Choose TWO letters" style: one shared stem and option list for several answers.
        if PICK_N.search(text):
            stem, opts = [], []
            for ln in lines:
                lm = LETTERED.match(ln)
                if lm and stem:
                    opts.append([lm.group(1), ln[lm.end():].strip()])
                elif not BOILERPLATE.match(ln) and not PICK_N.search(ln) and not re.match(r'^(?:Choose|Write)\b', ln):
                    stem.append(ln)
            for n in range(lo, hi + 1):
                questions.setdefault(n, {'text': ' '.join(stem), 'options': opts, 'shared': True})
            pick_options = opts
            group['started'] = True
            continue
        if pick_options is not None:
            if all(LETTERED.match(ln) for ln in lines):
                for ln in lines:
                    lm = LETTERED.match(ln)
                    pick_options.append([lm.group(1), ln[lm.end():].strip()])
                continue
            pick_options = None

        # Gap-fill markers anywhere in the paragraph (summaries, notes, flow-chart cells).
        gap_numbers = []
        for g in GAP.finditer(text):
            if accept(int(g.group(1))):
                gap_numbers.append(int(g.group(1)))
        if gap_numbers:
            full = '\n'.join(lines)
            for n in gap_numbers:
                if n not in questions:
                    snippet = _sentence_with_gap(full, n)
                    if snippet:
                        questions[n] = {'text': snippet, 'options': [], 'shared': False}
            group['started'] = True
            last = None
            continue

        letters = [LETTERED.match(ln) for ln in lines]
        numbered = NUMBERED.match(first)
        if numbered and accept(int(numbered.group(1))):
            current = None
            tail_letters = []
            for ln in lines:
                nm = NUMBERED.match(ln)
                lm = LETTERED.match(ln)
                if nm and accept(int(nm.group(1))) and int(nm.group(1)) not in questions:
                    n = int(nm.group(1))
                    current = {'text': ln[nm.end():].strip(), 'options': [], 'shared': False}
                    questions[n] = current
                    last = n
                    tail_letters = []
                elif lm and current is not None:
                    if group['mcq']:
                        current['options'].append([lm.group(1), ln[lm.end():].strip()])
                    else:
                        tail_letters.append([lm.group(1), ln[lm.end():].strip()])
                elif current is not None and not lm:
                    current['text'] += ' ' + ln
            if tail_letters and len(tail_letters) >= 2 and not group['list']:
                group['list'] = tail_letters
            group['started'] = True
            continue

        # A lone letter option or stem line belonging to the previous multiple-choice question.
        if last is not None and group['mcq'] and all(letters):
            for lm, ln in zip(letters, lines):
                questions[last]['options'].append([lm.group(1), ln[lm.end():].strip()])
            continue

        # Shared list of choices (researchers, headings, endings, word bank).
        lettered = [lm for lm in letters if lm]
        if len(lettered) >= 2 and not group['list']:
            heading = [ln for ln, lm in zip(lines, letters) if not lm]
            group['list'] = [[lm.group(1), ln[lm.end():].strip()] for lm, ln in zip(letters, lines) if lm]
            group['list_title'] = heading[0] if heading and heading[0].lower().startswith('list of') else ''
            if not group['started']:
                group['instructions'].extend(ln for ln in heading if ln != group['list_title'])
            continue
        if re.match(r'^List of\b', first, re.I) and len(lines) >= 2:
            roman = [re.match(r'^((?:i{1,3}|iv|v|vi{1,3}|ix|x))\s+(.+)$', ln, re.I) for ln in lines[1:]]
            if all(roman):
                group['list'] = [[r.group(1), r.group(2)] for r in roman]
                group['list_title'] = first
                continue

        if not group['started']:
            if MCQ_HINT.search(text):
                group['mcq'] = True
            if not BOILERPLATE.match(text.split('\n')[0]):
                group['instructions'].extend(ln for ln in lines if not BOILERPLATE.match(ln))
            elif len(lines) > 1:
                group['instructions'].extend(ln for ln in lines if not BOILERPLATE.match(ln))
        elif re.match(r'^List of\b', first, re.I):
            group['list_title'] = first

    out_groups = []
    for g in groups:
        out_groups.append({k: g[k] for k in ('from', 'to', 'title', 'instructions', 'list', 'list_title')})
    return {'questions': {str(k): v for k, v in sorted(questions.items())}, 'groups': out_groups}
