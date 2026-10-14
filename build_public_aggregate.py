#!/usr/bin/env python3
"""Build a public, aggregate-only OR audit from the live Sheet.

Never call register_site_update.main(): it writes private trackers and public PII.
"""
import collections
import datetime as dt
import html
import json
import os
import re
from pathlib import Path
import sys
import tempfile

BASE = Path(__file__).resolve().parent
STATE = Path('/home/kttwatt/register-history/public-aggregate-state.json')
sys.path[:0] = ['/home/kttwatt/.hermes/scripts', '/home/kttwatt/register-system']
import register_site_update as site
import register_cross_checks as cross
import report_period as period

EXPECTED = {9: 'เวลาเข้าห้องผ่าตัด', 10: 'เวลาเริ่มผ่าตัด',
            11: 'เวลาผ่าตัดเสร็จ', 12: 'เวลาออกจากห้องผ่าตัด',
            13: 'ชื่อ - สกุล ผู้ป่วย', 15: 'HN'}


def compute(raw, today, previous=None, state=None):
    """Pure calculation; public result is an explicit allowlist of aggregates."""
    header = raw[0]
    for index, expected in EXPECTED.items():
        if index >= len(header) or header[index].strip() != expected:
            raise ValueError(f'Header shifted at {index}: expected {expected}')
    rows = [(i, [(v or '').strip() for v in row] + [''] * 61)
            for i, row in enumerate(raw[1:], 2)]
    eligible = [(i, r) for i, r in rows
                if site.finished(r) and period.month_within_cutoff(r[2], today)]
    extras = collections.defaultdict(list)
    for fn, label in ((cross.hn_collisions, 'HN ซ้ำต่างคน'),
                      (cross.an_duplicates, 'AN ซ้ำข้ามคน')):
        for item in fn(eligible):
            for i in item['rows']:
                extras[i].append(label)
    for item in cross.room_overlaps(eligible):
        for i in item['rows']:
            r = rows[i - 2][1]
            if not cross.web_overlap_exempt(r):
                extras[i].append(cross.overlap_label(item))
    labels_by_id = {}
    live_by_id = {}
    keyed = collections.defaultdict(list)
    per_month = collections.defaultdict(lambda: {'finished': 0, 'pending': 0,
                                                  'unfinished': 0, 'types': collections.Counter()})
    for i, r in rows:
        if r[1]:
            live_by_id[r[1]] = r
            keyed[(r[15], r[2])].append(r[1])
        parsed = period.month_key_of(r[2])
        if not parsed or not period.month_within_cutoff(r[2], today):
            continue
        mk = parsed[0]
        if not r[1]:
            continue
        if not site.finished(r):
            per_month[mk]['unfinished'] += 1
            continue
        missing = list(dict.fromkeys(site.missing_cols(r) + extras[i]))
        labels_by_id[r[1]] = missing
        per_month[mk]['finished'] += 1
        if missing:
            per_month[mk]['pending'] += 1
            per_month[mk]['types'].update(missing)
    state = {'observed': {}, 'seeded': False} if state is None else state
    observed = dict(state.get('observed', {}))
    seeded = bool(state.get('seeded', False))
    if not seeded and previous:
        for case in previous.get('all_cases', []):
            key = (str(case.get('hn', '')), str(case.get('date', '')))
            ids = keyed.get(key, [])
            # Ambiguous HN/date pairs are not proof of identity.
            if len(ids) == 1 and case.get('month_key'):
                observed.setdefault(ids[0], case['month_key'])
        seeded = True
    for _i, r in eligible:
        if r[1] and labels_by_id.get(r[1]):
            mk = period.month_key_of(r[2])[0]
            observed.setdefault(r[1], mk)
    report = period.period_for(today)
    mk = report['month_key']
    stats = per_month[mk]
    resolved = sum(1 for case_id, month in observed.items()
                   if month == mk and case_id in labels_by_id and not labels_by_id[case_id])
    # This is the only data sent to public files. No raw row or ID is serialized.
    public = {'as_of': dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).isoformat(timespec='minutes'),
              'period': report['label'], 'month': mk,
              'finished': stats['finished'], 'pending': stats['pending'],
              'resolved_observed': resolved, 'unfinished': stats['unfinished'],
              'types': [{'label': k, 'count': n} for k, n in
                        sorted(stats['types'].items(), key=lambda kv: (-kv[1], kv[0]))],
              'history_scope': 'แก้ไขแล้วจากเคสที่เคยแจ้งตั้งแต่ 9 ต.ค. 2569'}
    private_next = {'observed': observed, 'seeded': seeded}
    return public, private_next, rows


def render(summary, page):
    esc = html.escape
    title = 'รายงานข้อมูลไม่ครบถ้วน' if page == 'index' else 'ภาพรวมทะเบียนผ่าตัด'
    lis = ''.join(f'<li><span>{esc(t["label"])}</span><strong>{t["count"]}</strong></li>'
                  for t in summary['types']) or '<li>ไม่พบรายการค้างในช่วงรายงาน</li>'
    return f'''<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — OR Audit</title><style>
:root{{color-scheme:dark;font-family:system-ui,-apple-system,sans-serif;background:#0b0b0c;color:#ededed}}
*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1050px;margin:auto;padding:24px 16px 64px}}
nav{{border-bottom:1px solid #303038;padding:16px;display:flex;gap:24px;justify-content:center}}
a{{color:#69dacc}}nav a{{text-decoration:none}}h1{{font-size:clamp(1.5rem,3vw,2rem)}}
.muted{{color:#aaaab4}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}}
.card,.panel{{border:1px solid #303038;background:#151517;padding:18px}}.card strong{{display:block;font-size:2.2rem;margin-top:8px}}
.panel{{margin-top:16px}}ul{{padding:0;list-style:none}}li{{border-top:1px solid #303038;padding:12px 0;display:flex;justify-content:space-between;gap:12px}}
.note{{line-height:1.65}}@media(max-width:480px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.card{{padding:12px}}.card strong{{font-size:1.8rem}}}}
</style></head><body><nav><a href="index.html">ข้อมูล</a><a href="dashboard.html">Dashboard</a></nav>
<main><h1>{title}</h1><p class="muted">{esc(summary['period'])} · อัปเดต {esc(summary['as_of'])} (เวลาไทย)</p>
<section class="grid" aria-label="สรุป"><div class="card">เคสเสร็จแล้ว<strong>{summary['finished']}</strong></div>
<div class="card">รอตรวจแก้<strong>{summary['pending']}</strong></div>
<div class="card">แก้ไขแล้ว*<strong>{summary['resolved_observed']}</strong></div>
<div class="card">ยังไม่ลงเวลาเสร็จ<strong>{summary['unfinished']}</strong></div></section>
<section class="panel"><h2>ประเภทข้อแจ้งเตือนปัจจุบัน</h2><ul>{lis}</ul></section>
<p class="note muted">*{esc(summary['history_scope'])} ตัวเลขนี้หมายถึงเคสที่เคยมีข้อแจ้งเตือนและปัจจุบันไม่ติดเกณฑ์แล้ว ไม่ใช่เวลาที่เจ้าหน้าที่แก้ไขจริง ข้อมูลวันนี้ยังไม่นับจนกว่าจะสิ้นวัน</p>
<p class="note">รายละเอียดเคสอยู่ใน <a href="https://docs.google.com/spreadsheets/d/1T57OJl3Pa2oSgCp1pms4IMlwQyu6qdIIihpqqjwFoCk/edit#gid=0">ทะเบียนผ่าตัด (ต้องมีสิทธิ์เข้าถึง)</a></p>
</main></body></html>'''


def atomic_write(path, content, private=False):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.aggregate-')
    try:
        os.fchmod(fd, 0o600 if private else 0o644)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    raw = site.gsheet.values(site.SHEET, "'ทะเบียนผ่าตัด'!A1:BD")
    previous = json.loads((BASE / 'audit_data.json').read_text(encoding='utf-8')) if (BASE / 'audit_data.json').exists() else None
    current = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else None
    public, private_next, rows = compute(raw, period.today_bangkok(), previous, current)
    outputs = {'public_summary.json': json.dumps(public, ensure_ascii=False, indent=2) + '\n',
               'index.html': render(public, 'index'), 'dashboard.html': render(public, 'dashboard')}
    # Privacy gate: no patient names, HN, AN, or stable IDs in published bytes.
    flat = '\n'.join(outputs.values()).replace(site.SHEET, '[AUTHORIZED_SHEET_LINK]')
    for _i, row in rows:
        for index in (1, 13, 15, 16):
            token = row[index].strip()
            if len(token) >= 5 and re.search(r'(?<![0-9A-Za-z])' + re.escape(token) + r'(?![0-9A-Za-z])', flat):
                raise RuntimeError(f'Public artifact contains patient field at col {index}; aborting')
    if any(key in public for key in ('all_cases', 'cases', 'patients', 'hn', 'an', 'name')):
        raise RuntimeError('Public schema contains forbidden key')
    STATE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(STATE.parent, 0o700)
    for name, text in outputs.items():
        atomic_write(BASE / name, text)
    atomic_write(STATE, json.dumps(private_next, ensure_ascii=False), private=True)
    print(json.dumps(public, ensure_ascii=False))


if __name__ == '__main__':
    main()
