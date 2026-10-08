#!/usr/bin/env python3
"""Generate a self-contained index.html report from audit_data.json.

Visual design: dark theme modelled on the OpenCode Console
(near-black page, soft dark panels, subtle borders, muted grey labels,
white monospace values, pill chips).

หมายเหตุ: ตรรกะเลือกปีงบ/เดือน, กรองตาราง, กราฟ, URL state และ drill-down อยู่ที่
assets/audit_ui.js (ใช้ร่วมกับ dashboard.html) — ไฟล์นี้ทำหน้าที่แค่ render HTML
ตั้งต้น + ผูก callback ให้ panel ของหน้านี้วาดใหม่ตามที่ผู้ใช้เลือก.
"""
import json
import html
import os
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "audit_data.json"
OUT_PATH = BASE_DIR / "index.html"

CSS_BLOCK = '''  :root {
    --bg: #0b0b0c;
    --bg-panel: #151517;
    --bg-elevated: #1b1b1e;
    --bg-muted: #1f1f23;
    --border: #27272b;
    --border-soft: #1f1f23;
    --text: #ededed;
    --text-muted: #8b8b90;
    --text-dim: #6b6b70;
    --accent: #ffffff;
    --warn: #fbbf24;
    --ok: #4ade80;
    --bg-translucent: rgba(11, 11, 12, 0.92);
  }

  :root[data-theme="light"] {
    --bg: #f5f5f6;
    --bg-panel: #ffffff;
    --bg-elevated: #ececee;
    --bg-muted: #e4e4e7;
    --border: #d4d4d8;
    --border-soft: #e4e4e7;
    --text: #18181b;
    --text-muted: #52525b;
    --text-dim: #71717a;
    --accent: #000000;
    --warn: #b45309;
    --ok: #15803d;
    --bg-translucent: rgba(245, 245, 246, 0.92);
  }

  html { scroll-behavior: smooth; }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    padding: 0 12px 64px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Helvetica, Arial, sans-serif;
    font-size: 15px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  .mono, .data-table td, .data-table th, .chip, .stat-value {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  }

  .wrap {
    max-width: 900px;
    margin: 0 auto;
  }

  /* top bar — workspace switcher + active view tab, like the console */
  .topbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 2px;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    background: var(--bg-translucent);
    backdrop-filter: blur(8px);
    z-index: 10;
  }

  .ws-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 0;
    padding: 5px 10px;
    font-size: 0.82rem;
    color: var(--text);
  }

  .ws-dot {
    width: 18px;
    height: 18px;
    border-radius: 0;
    background: var(--bg-muted);
    border: 1px solid var(--border);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.6rem;
    color: var(--text-muted);
  }

  .theme-toggle {
    margin-left: auto;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    color: var(--text);
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.95rem;
    cursor: pointer;
  }

  .theme-toggle:hover {
    background: var(--bg-muted);
  }

  .tabs {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
    margin-left: 4px;
  }

  .tab {
    padding: 8px 16px 9px;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-muted);
    white-space: nowrap;
    text-decoration: none;
    background: var(--bg-muted);
    border: 1px solid var(--border);
    border-bottom: none;
    margin-bottom: -1px;
    position: relative;
    top: 3px;
    transition: top 0.15s ease, color 0.15s ease;
  }

  .tab:hover {
    color: var(--text);
    top: 1px;
  }

  .tab.active {
    color: var(--accent);
    background: var(--bg);
    border-color: var(--border);
    top: 0;
    z-index: 1;
    box-shadow: 2px -2px 4px rgba(0, 0, 0, 0.15);
  }

  .page-head {
    padding: 22px 2px 14px;
  }

  .page-title {
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 0 0 6px;
    color: var(--text);
  }

  .page-sub {
    color: var(--text-muted);
    font-size: 0.88rem;
    margin: 0;
  }

  .warn-sub {
    color: var(--warn);
    font-weight: 600;
    margin-top: 6px;
  }

  .all-clear {
    color: var(--ok);
    font-weight: 600;
    margin: 0;
  }

  .stat-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 0 0 16px;
  }

  .stat {
    flex: 1 1 140px;
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    border-radius: 0;
    padding: 12px 14px;
  }

  .stat-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin: 0 0 6px;
  }

  .stat-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text);
    margin: 0;
    line-height: 1.2;
  }

  .panel {
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    border-radius: 0;
    margin-bottom: 18px;
    overflow: hidden;
  }

  .panel-body {
    padding: 16px 14px;
  }

  .section-title {
    font-size: 1.05rem;
    font-weight: 650;
    color: var(--text);
    margin: 0 0 4px;
  }

  .section-sub {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin: 0 0 14px;
  }

  .table-wrap {
    overflow-x: auto;
  }

  .progress-stats {
    display: flex;
    gap: 10px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }

  .progress-stat {
    flex: 1 1 90px;
    text-align: center;
    background: var(--bg-elevated);
    border: 1px solid var(--border-soft);
    padding: 10px 8px;
  }

  .progress-stat-label {
    font-size: 0.72rem;
    color: var(--text-muted);
    margin: 0 0 4px;
  }

  .progress-stat-value {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 1.4rem;
    font-weight: 650;
    color: var(--text);
    margin: 0;
  }

  .progress-stat-button {
    color: inherit;
    font: inherit;
    cursor: pointer;
    transition: border-color 0.15s ease, background-color 0.15s ease;
  }
  .progress-stat-button:hover,
  .progress-stat-button[aria-expanded="true"] { border-color: var(--ok); }
  .progress-stat-button:focus-visible { outline: 3px solid var(--ok); outline-offset: 2px; }
  .progress-stat-button .progress-stat-label,
  .progress-stat-button .progress-stat-value { display: block; }
  .resolved-history {
    margin-top: 14px;
    padding: 12px;
    border: 1px solid var(--border-soft);
    background: var(--bg-elevated);
    max-height: 380px;
    overflow-y: auto;
  }
  .resolved-history[hidden] { display: none !important; }
  .resolved-history-intro,
  .resolved-history-empty { color: var(--text-muted); font-size: 0.84rem; margin: 0 0 10px; }
  .resolved-history-list { list-style: none; margin: 0; padding: 0; }
  .resolved-history-item { padding: 10px 0; border-top: 1px solid var(--border-soft); }
  .resolved-history-case { font-weight: 650; overflow-wrap: anywhere; }
  .resolved-history-tags { color: var(--text-muted); font-size: 0.82rem; margin-top: 4px; overflow-wrap: anywhere; }

  .progress-warn { color: var(--warn); }
  .progress-ok { color: var(--ok); }

  .progress-track {
    width: 100%;
    height: 14px;
    background: var(--bg-muted);
    overflow: hidden;
    display: flex;
  }

  .progress-fill-resolved {
    height: 100%;
    min-width: 8px;
    flex-shrink: 0;
    background: repeating-linear-gradient(
      45deg,
      var(--ok) 0, var(--ok) 4px,
      #ffffff88 4px, #ffffff88 8px
    );
    background-color: var(--ok);
  }

  .progress-fill-pending {
    height: 100%;
    min-width: 8px;
    flex-shrink: 0;
    background: var(--warn);
  }

  .progress-fill-rest {
    height: 100%;
    flex: 1 1 auto;
    background: var(--ok);
  }

  .progress-pct {
    margin: 8px 0 0;
    font-size: 0.82rem;
    color: var(--text-muted);
    text-align: right;
  }

  .filter-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }

  .filter-label {
    font-size: 0.82rem;
    color: var(--text-muted);
  }

  .month-select {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 10px;
    font-size: 0.85rem;
    font-family: inherit;
    cursor: pointer;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }

  .data-table th {
    background: var(--bg-elevated);
    color: var(--text-muted);
    font-weight: 600;
    text-align: left;
    padding: 9px 10px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    position: sticky;
    top: 0;
  }

  .data-table td {
    padding: 9px 10px;
    border-bottom: 1px solid var(--border-soft);
    vertical-align: top;
    color: var(--text);
  }

  .data-table tbody tr:last-child td {
    border-bottom: none;
  }

  .data-table tbody tr:hover {
    background: var(--bg-elevated);
  }

  .name-cell {
    white-space: nowrap;
  }

  .circ-cell {
    font-weight: 700;
    color: var(--accent);
  }

  .circ-name {
    display: block;
    white-space: nowrap;
  }

  .chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 0;
    font-size: 0.7rem;
    font-weight: 600;
    margin: 2px 4px 2px 0;
    white-space: nowrap;
  }

  .chip-warn {
    background: rgba(251, 191, 36, 0.13);
    color: var(--warn);
    border: 1px solid rgba(251, 191, 36, 0.28);
  }

  .chip-blank {
    background: var(--bg-muted);
    color: var(--text-muted);
    border: 1px solid var(--border);
  }

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  footer {
    text-align: center;
    color: var(--text-dim);
    font-size: 0.78rem;
    margin-top: 28px;
  }

  @media (max-width: 640px) {
    body { padding: 0 10px 56px; }
    .page-title { font-size: 1.2rem; }
    .stat { flex: 1 1 90px; }
    .stat-value { font-size: 1.15rem; }
    .data-table thead {
      display: none;
    }
    .data-table, .data-table tbody, .data-table tr, .data-table td {
      display: block;
      width: 100%;
    }
    .data-table tr {
      border: 1px solid var(--border-soft);
      border-radius: 0;
      margin-bottom: 10px;
      padding: 8px 12px;
      background: var(--bg-elevated);
    }
    .data-table td {
      border-bottom: none;
      padding: 4px 0;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      text-align: right;
    }
    .data-table td::before {
      content: attr(data-label);
      font-weight: 600;
      color: var(--text-muted);
      text-align: left;
      flex: 0 0 auto;
    }
    .data-table td.missing-cell { align-items: flex-start; }
    .missing-items {
      flex: 1 1 auto;
      min-width: 0;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      text-align: right;
    }
    .missing-items .pair-line { width: 100%; text-align: right; overflow-wrap: anywhere; }
    .missing-items .chip { margin-right: 0; }
    .data-table td.circ-cell {
      align-items: flex-start;
      text-align: right;
    }
    .data-table td.circ-cell::before {
      padding-top: 1px;
    }
    .circ-names {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }
  }

  .chart-wrap {
    padding-top: 4px;
  }

  .chart-legend {
    display: flex;
    gap: 16px;
    margin-bottom: 12px;
    font-size: 0.78rem;
    color: var(--text-muted);
  }

  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    display: inline-block;
  }

  .legend-ok { background: var(--ok); }
  .legend-missing { background: var(--warn); }

  .bar-chart {
    display: flex;
    align-items: flex-end;
    gap: 3px;
    height: 160px;
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .bar-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    flex: 1 0 18px;
    height: 100%;
    min-width: 18px;
  }

  .bar-stack {
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    background: var(--bg-muted);
    min-height: 2px;
  }

  .bar-seg {
    width: 100%;
  }

  .bar-missing { background: var(--warn); }
  .bar-ok { background: var(--ok); }

  .bar-label {
    font-size: 0.62rem;
    color: var(--text-dim);
    margin-top: 4px;
  }'''


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def asset_version() -> str:
    try:
        return str(int(max(os.path.getmtime(BASE_DIR / "assets" / n)
                           for n in ("audit_ui.js", "audit_ui.css"))))
    except OSError:
        return "1"


def pair_line(p):
    mins = p.get("minutes", "")
    mins = int(mins) if isinstance(mins, float) and mins.is_integer() else mins
    return (f'<div class="pair-line">{esc(p.get("name", ""))} HN{esc(p.get("hn", ""))} '
            f'วันที่ {esc(p.get("date", ""))} เข้า {esc(p.get("enter", ""))} ออก {esc(p.get("exit", ""))} '
            f'({esc(p.get("tag", ""))} {esc(f"{mins}")} นาที)</div>')


def render_cases_table(cases: list) -> str:
    rows = []
    for case in cases:
        missing = case.get("missing", []) or []
        missing_html = "".join(f'<span class="chip chip-warn" data-rule="{esc(m)}" title="กดเพื่อดูคำอธิบาย">{esc(m)}</span>' for m in missing)
        pair_html = "".join(
            pair_line(p)
            for p in (case.get("pair", []) or []))
        times = case.get("times", []) or []
        time_html = (f'<div class="pair-line">เข้า {esc(times[0])} เริ่ม {esc(times[1])} เสร็จ {esc(times[2])} ออก {esc(times[3])}</div>'
                     if len(times) == 4 else "")
        days = case.get("days_pending")
        days_html = f'{esc(days)} วัน' if days is not None else "-"
        circ_names = [n.strip() for n in (case.get("circ", "") or "").split(",") if n.strip()]
        circ_spans = "".join(f'<span class="circ-name">{esc(n)}</span>' for n in circ_names)
        circ_html = f'<div class="circ-names">{circ_spans}</div>'
        date = case.get("date", "")
        day = date.split("/")[0] if date else ""
        rows.append(
            f'''<tr data-key="{esc(case.get("hn", ""))}|{esc(date)}" data-month="{esc(case.get("month_key", ""))}"
            data-dept="{esc(case.get("dept", ""))}" data-day="{esc(day)}"
            data-missing="{esc(",".join(missing))}" data-days="{esc(days if days is not None else "")}">
        <td data-label="วันที่">{esc(date)}</td>
        <td data-label="HN">{esc(case.get("hn", ""))}</td>
        <td data-label="ชื่อ" class="name-cell">{esc(case.get("name", ""))}</td>
        <td data-label="แผนก">{esc(case.get("dept", ""))}</td>
        <td data-label="การผ่าตัด">{esc(case.get("op", ""))}</td>
        <td data-label="Circulating" class="circ-cell">{circ_html}</td>
        <td data-label="ข้อมูลที่ขาด" class="missing-cell"><div class="missing-items">{missing_html}{pair_html}{time_html}</div></td>
        <td data-label="รอแก้ไข">{days_html}</td>
      </tr>'''
        )
    table = f'''<div class="table-wrap">
      <table class="data-table" id="allCasesTable">
        <thead>
          <tr>
            <th data-sort="date">วันที่</th>
            <th data-sort="hn">HN</th>
            <th data-sort="name">ชื่อ</th>
            <th data-sort="dept">แผนก</th>
            <th>การผ่าตัด</th>
            <th>Circulating</th>
            <th>ข้อมูลที่ขาด</th>
            <th data-sort="days">รอแก้ไข</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows)}
        </tbody>
      </table>
    </div>
    <p class="empty-state" id="noCasesMsg" style="display:none">ไม่มีเคสข้อมูลไม่ครบในช่วงที่เลือก</p>
    <div class="audit-pager" id="pager" style="display:none"></div>'''
    return table


def build_html(data: dict) -> str:
    repo = data.get("repo", "")
    as_of = data.get("as_of", "")
    period = data.get("period", {}) or {}
    all_cases = data.get("all_cases", []) or []
    table_html = render_cases_table(all_cases)
    audit_json = json.dumps(
        {k: data.get(k) for k in ("current", "fiscal_years", "periods", "fy_totals",
                                  "all_cases", "period", "as_of", "generated_at", "repo")},
        ensure_ascii=False, separators=(",", ":"))
    ver = asset_version()

    return f'''<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="dark">
<title>{esc(repo)} — Audit</title>
<script>
(function() {{
  var t = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', t);
}})();
</script>
<style>
{CSS_BLOCK}
</style>
<link rel="stylesheet" href="assets/audit_ui.css?v={ver}">
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <nav class="tabs">
        <a class="tab" href="dashboard.html">Dashboard</a>
        <a class="tab active" href="index.html">ข้อมูล</a>
      </nav>
      <button class="theme-toggle" id="reportBtn" type="button" aria-label="Export report" title="Export เป็นรูปภาพ" style="margin-left:auto">📄</button>
      <button class="theme-toggle" id="themeToggle" type="button" aria-label="สลับโหมดสี" style="margin-left:6px">🌙</button>
    </div>

    <div class="page-head">
      <h1 class="page-title">รายงานข้อมูลไม่ครบถ้วน</h1>
      <p class="page-sub" id="scopeSub">{esc(period.get("label", ""))}</p>
      <p class="scope-note" id="provNote">คำนวณสดจากทะเบียนผ่าตัด ณ {esc(as_of)} {esc(data.get("generated_at", ""))}</p>
      <p class="section-sub warn-sub" id="unfinishedNote" style="display:none"></p>
    </div>

    <div class="audit-filters">
      <div class="filter-field">
        <label class="filter-label" for="fySelect">ปีงบประมาณ</label>
        <select id="fySelect" class="audit-select"></select>
      </div>
      <div class="filter-field">
        <label class="filter-label" for="monthSelect">เดือน</label>
        <select id="monthSelect" class="audit-select"></select>
      </div>
      <div class="filter-field grow">
        <label class="filter-label" for="caseSearch">ค้นหา (HN / ชื่อ / แผนก / การผ่าตัด)</label>
        <input id="caseSearch" class="audit-input" type="search" placeholder="พิมพ์เพื่อกรอง">
      </div>
      <div class="filter-field">
        <label class="filter-label" for="pageSize">แสดง</label>
        <select id="pageSize" class="audit-select">
          <option value="25">25 แถว</option>
          <option value="50" selected>50 แถว</option>
          <option value="100">100 แถว</option>
          <option value="0">ทั้งหมด</option>
        </select>
      </div>
    </div>
    <div class="filter-chips" id="activeFilters"></div>

    <div class="panel" id="progress">
      <div class="panel-body">
        <p class="section-title">ความคืบหน้าการแก้ไข</p>
        <p class="section-sub" id="progressCaption"></p>
        <div class="progress-stats">
          <div class="progress-stat">
            <p class="progress-stat-label">เคสทั้งหมด</p>
            <p class="progress-stat-value" id="progTotal">0</p>
          </div>
          <div class="progress-stat">
            <p class="progress-stat-label progress-warn">รอแก้ไข</p>
            <p class="progress-stat-value progress-warn" id="progPending">0</p>
          </div>
          <button class="progress-stat progress-stat-button" id="resolvedHistoryToggle" type="button" aria-expanded="false" aria-controls="resolvedHistoryPanel">
            <span class="progress-stat-label progress-ok">แก้ไขแล้ว</span>
            <span class="progress-stat-value progress-ok" id="progResolved">0</span>
          </button>
        </div>
        <div class="progress-track">
          <div class="progress-fill-rest" id="progFillRest" style="width:0%"></div>
          <div class="progress-fill-resolved" id="progFillResolved" style="width:0%"></div>
          <div class="progress-fill-pending" id="progFillPending" style="width:0%"></div>
        </div>
        <p class="progress-pct" id="progPct">—</p>
        <div class="resolved-history" id="resolvedHistoryPanel" role="region" aria-label="ประวัติเคสที่แก้ไขแล้ว" hidden></div>
      </div>
    </div>

    <div class="panel" id="chart">
      <div class="panel-body">
        <p class="section-sub" id="chartCaption"></p>
        <div id="chartHost"></div>
      </div>
    </div>

    <div class="panel" id="cases">
      <div class="panel-body">
        {table_html}
      </div>
    </div>

    <footer>อัปเดตอัตโนมัติทุกชั่วโมง · ระบบติดตามข้อมูลทะเบียนผ่าตัด</footer>
  </div>

  <script src="assets/audit_ui.js?v={ver}"></script>
  <script>
    (function() {{
      var btn = document.getElementById('themeToggle');
      var root = document.documentElement;
      function syncTheme() {{
        btn.textContent = root.getAttribute('data-theme') === 'light' ? '☀️' : '🌙';
      }}
      syncTheme();
      btn.addEventListener('click', function() {{
        var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        root.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        syncTheme();
      }});
    }})();
    var AUDIT_DATA = {audit_json};
    (function() {{
      var data = AUDIT_DATA;
      var scopeSub = document.getElementById('scopeSub');
      var unfinishedNote = document.getElementById('unfinishedNote');
      var chartHost = document.getElementById('chartHost');
      var chartCaption = document.getElementById('chartCaption');
      var progressCaption = document.getElementById('progressCaption');
      var progTotal = document.getElementById('progTotal');
      var progPending = document.getElementById('progPending');
      var progResolved = document.getElementById('progResolved');
      var progFillRest = document.getElementById('progFillRest');
      var progFillResolved = document.getElementById('progFillResolved');
      var progFillPending = document.getElementById('progFillPending');
      var progPct = document.getElementById('progPct');
      var lastSel = null;

      function renderSelection(sel) {{
        lastSel = sel;
        var b = AuditUI.block(data, sel) || {{}};
        var scope = AuditUI.scopeLabel(data, sel);
        scopeSub.textContent = scope + ' · อัปเดตล่าสุด ' + (data.generated_at || '');
        unfinishedNote.style.display = b.unfinished ? '' : 'none';
        if (b.unfinished) {{
          unfinishedNote.textContent = 'เคสยังไม่ลงเวลาเสร็จ ' + b.unfinished + ' เคส — นับรวมตอนเช้า';
        }}
        var pr = AuditUI.progressHtml(data, sel);
        progTotal.textContent = pr.prog.total;
        progPending.textContent = pr.prog.pending;
        progResolved.textContent = pr.prog.resolved;
        progFillRest.style.width = pr.restPct + '%';
        progFillResolved.style.width = pr.resolvedPct + '%';
        progFillPending.style.width = pr.pendingPct + '%';
        progPct.textContent = pr.prog.ever
          ? Math.round((pr.prog.resolved / pr.prog.ever) * 1000) / 10 + '% แก้ไขแล้ว (' +
            pr.prog.resolved + '/' + pr.prog.ever + ' เคสที่เคยถูกแจ้งบนเว็บ)'
          : 'ยังไม่มีเคสที่เคยถูกแจ้งในเดือนนี้';
        progressCaption.textContent = scope;
        chartCaption.textContent = AuditUI.isFyScope(sel)
          ? 'ยอดเคส vs ข้อมูลไม่ครบ (รายเดือน) — ' + scope + ' · คลิกแท่งเพื่อดูเดือนนั้น'
          : 'ยอดเคส vs ข้อมูลไม่ครบ (รายวัน) — ' + scope + ' · คลิกแท่งเพื่อกรองวันนั้น';
        chartHost.innerHTML = AuditUI.chartHtml(data, sel);
        if (!b.finished) {{
          chartHost.innerHTML = '<p class="empty-state">' +
            (sel.month === AuditUI.FY_ALL
              ? 'ยังไม่มีเคสที่ลงเวลาผ่าตัดเสร็จในปีงบนี้'
              : 'ยังไม่มีข้อมูลสิ้นสุดวันในเดือนนี้ — ระบบจะนับเมื่อมีข้อมูลครบวัน') + '</p>';
        }}
      }}

      AuditUI.init(data, {{ tableBody: 'allCasesTable', onSelection: renderSelection }});

      document.getElementById('reportBtn').addEventListener('click', function() {{
        var sel = lastSel || {{ fy: data.current.fy, month: data.current.month, dept: '', col: '', day: '', q: '' }};
        var cases = AuditUI.sortCases(AuditUI.visibleCases(data, sel), sel.sort);
        var theme = document.documentElement.getAttribute('data-theme') || 'dark';
        var isLight = theme === 'light';
        var bg = isLight ? '#f5f5f6' : '#0b0b0c';
        var panelBg = isLight ? '#ffffff' : '#151517';
        var border = isLight ? '#d4d4d8' : '#27272b';
        var text = isLight ? '#18181b' : '#ededed';
        var textMuted = isLight ? '#52525b' : '#8b8b90';
        var warnBg = isLight ? 'rgba(180,83,9,0.12)' : 'rgba(251,191,36,0.13)';
        var warnText = isLight ? '#b45309' : '#fbbf24';
        var ok = isLight ? '#15803d' : '#4ade80';
        var filters = [];
        if (sel.dept) filters.push('แผนก: ' + sel.dept);
        if (sel.col) filters.push('ช่องที่ขาด: ' + sel.col);
        if (sel.day) filters.push('วันที่ ' + sel.day);
        if (sel.q) filters.push('ค้นหา: ' + sel.q);

        var W = 1000, pad = 32, rowH = 56;
        var H = 150 + Math.max(cases.length, 1) * rowH + 60;
        var canvas = document.createElement('canvas');
        var scale = 2;
        canvas.width = W * scale;
        canvas.height = H * scale;
        var ctx = canvas.getContext('2d');
        ctx.scale(scale, scale);
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, W, H);

        var y = pad;
        ctx.fillStyle = text;
        ctx.font = '700 22px -apple-system, "Segoe UI", sans-serif';
        ctx.fillText('รายงานข้อมูลไม่ครบถ้วน', pad, y + 22);
        y += 36;
        ctx.fillStyle = textMuted;
        ctx.font = '400 13px -apple-system, sans-serif';
        ctx.fillText(AuditUI.scopeLabel(data, sel) + (filters.length ? ' · กรอง: ' + filters.join(' · ') : '') +
                     ' · ' + cases.length + ' เคส · ส่งออก ' + new Date().toLocaleString('th-TH'), pad, y);
        y += 30;

        if (cases.length === 0) {{
          ctx.fillStyle = ok;
          ctx.font = '600 15px -apple-system, sans-serif';
          ctx.fillText('ไม่มีเคสข้อมูลไม่ครบในช่วงที่เลือก', pad, y + 10);
        }} else {{
          var colX = {{ date: pad, hn: pad + 80, name: pad + 150, dept: pad + 330, missing: pad + 430, days: W - pad - 60 }};
          ctx.fillStyle = textMuted;
          ctx.font = '600 11px -apple-system, sans-serif';
          ctx.fillText('วันที่', colX.date, y);
          ctx.fillText('HN', colX.hn, y);
          ctx.fillText('ชื่อ', colX.name, y);
          ctx.fillText('แผนก', colX.dept, y);
          ctx.fillText('ข้อมูลที่ขาด', colX.missing, y);
          ctx.fillText('รอแก้ไข', colX.days, y);
          y += 8;
          ctx.strokeStyle = border;
          ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(W - pad, y); ctx.stroke();
          y += 20;
          cases.forEach(function(c) {{
            ctx.fillStyle = panelBg;
            ctx.fillRect(pad - 8, y - 14, W - pad * 2 + 16, rowH - 6);
            ctx.fillStyle = text;
            ctx.font = '400 12px -apple-system, sans-serif';
            ctx.fillText(c.date, colX.date, y);
            ctx.fillText(c.hn, colX.hn, y);
            ctx.font = '600 12px -apple-system, sans-serif';
            ctx.fillText((c.name || '').slice(0, 22), colX.name, y);
            ctx.font = '400 12px -apple-system, sans-serif';
            ctx.fillText(c.dept, colX.dept, y);
            var mx = colX.missing;
            (c.missing || []).forEach(function(m) {{
              var w = ctx.measureText(m).width + 14;
              ctx.fillStyle = warnBg;
              ctx.fillRect(mx, y - 12, w, 16);
              ctx.fillStyle = warnText;
              ctx.font = '600 10px -apple-system, sans-serif';
              ctx.fillText(m, mx + 6, y);
              mx += w + 4;
            }});
            ctx.fillStyle = textMuted;
            ctx.font = '400 12px -apple-system, sans-serif';
            ctx.fillText(c.days_pending == null ? '-' : (c.days_pending + ' วัน'), colX.days, y);
            ctx.fillStyle = textMuted;
            ctx.font = '400 11px -apple-system, sans-serif';
            ctx.fillText((c.op || '').slice(0, 60) + (c.circ ? ' · Circ: ' + String(c.circ).slice(0, 40) : ''), colX.date, y + 18);
            y += rowH;
          }});
        }}

        canvas.toBlob(function(blob) {{
          var a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = 'missing-data-report-' + (AuditUI.isFyScope(sel) ? 'fy' + sel.fy : sel.month) + '.png';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }});
      }});
    }})();
  </script>
</body>
</html>
'''


def main() -> None:
    data = load_data()
    output = build_html(data)
    OUT_PATH.write_text(output, encoding="utf-8")
    print("DONE")


if __name__ == "__main__":
    main()
