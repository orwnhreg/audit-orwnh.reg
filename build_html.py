#!/usr/bin/env python3
"""Generate a self-contained index.html report from audit_data.json.

Visual design: dark theme modelled on the OpenCode Console
(near-black page, soft dark panels, subtle borders, muted grey labels,
white monospace values, pill chips).
"""
import json
import html
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "audit_data.json"
OUT_PATH = BASE_DIR / "index.html"


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def render_month_table(cases: list, show_month: bool = False) -> str:
    if not cases:
        return '<p class="all-clear" data-empty-msg>ครบ ✅</p>'

    rows = []
    for case in cases:
        missing = case.get("missing", []) or []
        missing_html = "".join(
            f'<span class="chip chip-warn">{esc(m)}</span>' for m in missing
        )
        days = case.get("days_pending")
        days_html = f'{esc(days)} วัน' if days is not None else "-"
        circ_names = [n.strip() for n in (case.get("circ", "") or "").split(",") if n.strip()]
        circ_spans = "".join(f'<span class="circ-name">{esc(n)}</span>' for n in circ_names)
        circ_html = f'<div class="circ-names">{circ_spans}</div>'
        month_key = case.get("month_key", "")
        rows.append(
            f'''<tr data-month="{esc(month_key)}">
        <td data-label="วันที่">{esc(case.get("date", ""))}</td>
        <td data-label="HN">{esc(case.get("hn", ""))}</td>
        <td data-label="ชื่อ" class="name-cell">{esc(case.get("name", ""))}</td>
        <td data-label="แผนก">{esc(case.get("dept", ""))}</td>
        <td data-label="การผ่าตัด">{esc(case.get("op", ""))}</td>
        <td data-label="Circulating" class="circ-cell">{circ_html}</td>
        <td data-label="ข้อมูลที่ขาด">{missing_html}</td>
        <td data-label="รอแก้ไข">{days_html}</td>
      </tr>'''
        )

    return f'''<div class="table-wrap">
      <table class="data-table" id="allCasesTable">
        <thead>
          <tr>
            <th>วันที่</th>
            <th>HN</th>
            <th>ชื่อ</th>
            <th>แผนก</th>
            <th>การผ่าตัด</th>
            <th>Circulating</th>
            <th>ข้อมูลที่ขาด</th>
            <th>รอแก้ไข</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows)}
        </tbody>
      </table>
      <p class="all-clear" id="noCasesMsg" style="display:none">ครบ ✅ ไม่มีเคสไม่ครบในเดือนที่เลือก</p>
    </div>'''


def render_month_select(month_options: list, default_key: str = "all") -> str:
    opts = [f'<option value="all"{" selected" if default_key == "all" else ""}>ทั้งหมด</option>']
    for key, label in month_options:
        sel_attr = " selected" if key == default_key else ""
        opts.append(f'<option value="{esc(key)}"{sel_attr}>{esc(label)}</option>')
    return f'''<select id="monthSelect" class="month-select">
        {"".join(opts)}
      </select>'''


def render_bar_chart_js() -> str:
    """Client-side chart renderer (JS) so it can redraw on month-select change."""
    return r'''
    function renderBarChart(daily) {
      if (!daily || !daily.length) {
        return '<p class="all-clear">ไม่มีข้อมูล</p>';
      }
      var maxTotal = 0;
      daily.forEach(function(d) { if (d.total > maxTotal) maxTotal = d.total; });
      if (!maxTotal) maxTotal = 1;
      var bars = daily.map(function(d) {
        var total = d.total || 0;
        var missing = d.missing || 0;
        var ok = Math.max(total - missing, 0);
        var totalH = total ? (total / maxTotal * 100) : 0;
        var missingPct = totalH ? (missing / total * 100) : 0;
        var okPct = totalH ? (ok / total * 100) : 0;
        var title = d.day + ': ทั้งหมด ' + total + ', ไม่ครบ ' + missing;
        return '<div class="bar-col" title="' + title.replace(/"/g, '&quot;') + '">' +
          '<div class="bar-stack" style="height:' + totalH + '%">' +
            '<div class="bar-seg bar-missing" style="height:' + missingPct + '%"></div>' +
            '<div class="bar-seg bar-ok" style="height:' + okPct + '%"></div>' +
          '</div>' +
          '<span class="bar-label">' + d.day + '</span>' +
        '</div>';
      }).join('');
      return '<div class="chart-wrap">' +
        '<div class="chart-legend">' +
          '<span class="legend-item"><i class="legend-dot legend-ok"></i>ครบ</span>' +
          '<span class="legend-item"><i class="legend-dot legend-missing"></i>ไม่ครบ</span>' +
        '</div>' +
        '<div class="bar-chart">' + bars + '</div>' +
      '</div>';
    }
'''


def build_html(data: dict) -> str:
    repo = data.get("repo", "")
    month = data.get("month", {}) or {}
    month_label = month.get("label", "")
    month_unfinished = month.get("unfinished", 0)
    unfinished_note = (f'<p class="section-sub warn-sub">เคสยังไม่ลงเวลาเสร็จ {month_unfinished} เคส — นับรวมตอนเช้า</p>'
                       if month_unfinished else "")
    gen_time = datetime.datetime.now().strftime("%H:%M")
    blank_cols = data.get("blank_cols", {}) or {}

    all_cases = data.get("all_cases", []) or []
    month_options = data.get("month_options", []) or []
    current_month_key = month_options[0][0] if month_options else "all"
    all_cases_total = sum(1 for c in all_cases if c.get("month_key") == current_month_key)
    table_html = render_month_table(all_cases)
    month_select_html = render_month_select(month_options, default_key=current_month_key)
    daily_by_month = data.get("daily_by_month", {}) or {}
    daily_by_month_json = json.dumps(daily_by_month, ensure_ascii=False)
    month_progress = data.get("month_progress", {}) or {}
    month_progress_json = json.dumps(month_progress, ensure_ascii=False)
    chart_js = render_bar_chart_js()

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
  :root {{
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
  }}

  :root[data-theme="light"] {{
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
  }}

  html {{ scroll-behavior: smooth; }}

  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    padding: 0 12px 64px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Helvetica, Arial, sans-serif;
    font-size: 15px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }}

  .mono, .data-table td, .data-table th, .chip, .stat-value {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  }}

  .wrap {{
    max-width: 900px;
    margin: 0 auto;
  }}

  /* top bar — workspace switcher + active view tab, like the console */
  .topbar {{
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
  }}

  .ws-pill {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 0;
    padding: 5px 10px;
    font-size: 0.82rem;
    color: var(--text);
  }}

  .ws-dot {{
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
  }}

  .theme-toggle {{
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
  }}

  .theme-toggle:hover {{
    background: var(--bg-muted);
  }}

  .tabs {{
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
    margin-left: 4px;
  }}

  .tab {{
    padding: 8px 12px 9px;
    font-size: 0.88rem;
    color: var(--text-muted);
    white-space: nowrap;
    text-decoration: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
  }}

  .tab.active {{
    color: var(--accent);
    border-bottom-color: var(--accent);
  }}

  .page-head {{
    padding: 22px 2px 14px;
  }}

  .page-title {{
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 0 0 6px;
    color: var(--text);
  }}

  .page-sub {{
    color: var(--text-muted);
    font-size: 0.88rem;
    margin: 0;
  }}

  .warn-sub {{
    color: var(--warn);
    font-weight: 600;
    margin-top: 6px;
  }}

  .all-clear {{
    color: var(--ok);
    font-weight: 600;
    margin: 0;
  }}

  .stat-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 0 0 16px;
  }}

  .stat {{
    flex: 1 1 140px;
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    border-radius: 0;
    padding: 12px 14px;
  }}

  .stat-label {{
    font-size: 0.75rem;
    color: var(--text-muted);
    margin: 0 0 6px;
  }}

  .stat-value {{
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text);
    margin: 0;
    line-height: 1.2;
  }}

  .panel {{
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    border-radius: 0;
    margin-bottom: 18px;
    overflow: hidden;
  }}

  .panel-body {{
    padding: 16px 14px;
  }}

  .section-title {{
    font-size: 1.05rem;
    font-weight: 650;
    color: var(--text);
    margin: 0 0 4px;
  }}

  .section-sub {{
    color: var(--text-muted);
    font-size: 0.85rem;
    margin: 0 0 14px;
  }}

  .table-wrap {{
    overflow-x: auto;
  }}

  .progress-stats {{
    display: flex;
    gap: 10px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }}

  .progress-stat {{
    flex: 1 1 90px;
    text-align: center;
    background: var(--bg-elevated);
    border: 1px solid var(--border-soft);
    padding: 10px 8px;
  }}

  .progress-stat-label {{
    font-size: 0.72rem;
    color: var(--text-muted);
    margin: 0 0 4px;
  }}

  .progress-stat-value {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 1.4rem;
    font-weight: 650;
    color: var(--text);
    margin: 0;
  }}

  .progress-warn {{ color: var(--warn); }}
  .progress-ok {{ color: var(--ok); }}

  .progress-track {{
    width: 100%;
    height: 10px;
    background: var(--bg-muted);
    overflow: hidden;
    display: flex;
  }}

  .progress-fill {{
    height: 100%;
    background: var(--ok);
  }}

  .progress-fill-resolved {{
    height: 100%;
    background: repeating-linear-gradient(
      45deg,
      var(--ok) 0, var(--ok) 4px,
      transparent 4px, transparent 8px
    );
    background-color: var(--bg-muted);
  }}

  .progress-fill-pending {{
    height: 100%;
    background: var(--warn);
  }}

  .progress-pct {{
    margin: 8px 0 0;
    font-size: 0.82rem;
    color: var(--text-muted);
    text-align: right;
  }}

  .filter-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }}

  .filter-label {{
    font-size: 0.82rem;
    color: var(--text-muted);
  }}

  .month-select {{
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 10px;
    font-size: 0.85rem;
    font-family: inherit;
    cursor: pointer;
  }}

  .data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }}

  .data-table th {{
    background: var(--bg-elevated);
    color: var(--text-muted);
    font-weight: 600;
    text-align: left;
    padding: 9px 10px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    position: sticky;
    top: 0;
  }}

  .data-table td {{
    padding: 9px 10px;
    border-bottom: 1px solid var(--border-soft);
    vertical-align: top;
    color: var(--text);
  }}

  .data-table tbody tr:last-child td {{
    border-bottom: none;
  }}

  .data-table tbody tr:hover {{
    background: var(--bg-elevated);
  }}

  .name-cell {{
    white-space: nowrap;
  }}

  .circ-cell {{
    font-weight: 700;
    color: var(--accent);
  }}

  .circ-name {{
    display: block;
    white-space: nowrap;
  }}

  .chip {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 0;
    font-size: 0.7rem;
    font-weight: 600;
    margin: 2px 4px 2px 0;
    white-space: nowrap;
  }}

  .chip-warn {{
    background: rgba(251, 191, 36, 0.13);
    color: var(--warn);
    border: 1px solid rgba(251, 191, 36, 0.28);
  }}

  .chip-blank {{
    background: var(--bg-muted);
    color: var(--text-muted);
    border: 1px solid var(--border);
  }}

  .chip-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}

  footer {{
    text-align: center;
    color: var(--text-dim);
    font-size: 0.78rem;
    margin-top: 28px;
  }}

  @media (max-width: 640px) {{
    body {{ padding: 0 10px 56px; }}
    .page-title {{ font-size: 1.2rem; }}
    .stat {{ flex: 1 1 90px; }}
    .stat-value {{ font-size: 1.15rem; }}
    .data-table thead {{
      display: none;
    }}
    .data-table, .data-table tbody, .data-table tr, .data-table td {{
      display: block;
      width: 100%;
    }}
    .data-table tr {{
      border: 1px solid var(--border-soft);
      border-radius: 0;
      margin-bottom: 10px;
      padding: 8px 12px;
      background: var(--bg-elevated);
    }}
    .data-table td {{
      border-bottom: none;
      padding: 4px 0;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      text-align: right;
    }}
    .data-table td::before {{
      content: attr(data-label);
      font-weight: 600;
      color: var(--text-muted);
      text-align: left;
      flex: 0 0 auto;
    }}
    .data-table td.circ-cell {{
      align-items: flex-start;
      text-align: right;
    }}
    .data-table td.circ-cell::before {{
      padding-top: 1px;
    }}
    .circ-names {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }}
  }}

  .chart-wrap {{
    padding-top: 4px;
  }}

  .chart-legend {{
    display: flex;
    gap: 16px;
    margin-bottom: 12px;
    font-size: 0.78rem;
    color: var(--text-muted);
  }}

  .legend-item {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}

  .legend-dot {{
    width: 10px;
    height: 10px;
    display: inline-block;
  }}

  .legend-ok {{ background: var(--ok); }}
  .legend-missing {{ background: var(--warn); }}

  .bar-chart {{
    display: flex;
    align-items: flex-end;
    gap: 3px;
    height: 160px;
    overflow-x: auto;
    padding-bottom: 4px;
  }}

  .bar-col {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    flex: 1 0 18px;
    height: 100%;
    min-width: 18px;
  }}

  .bar-stack {{
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    background: var(--bg-muted);
    min-height: 2px;
  }}

  .bar-seg {{
    width: 100%;
  }}

  .bar-missing {{ background: var(--warn); }}
  .bar-ok {{ background: var(--ok); }}

  .bar-label {{
    font-size: 0.62rem;
    color: var(--text-dim);
    margin-top: 4px;
  }}
</style>
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
      <p class="page-sub">{esc(month_label)} · อัปเดตล่าสุด {esc(gen_time)}</p>
      {unfinished_note}
    </div>

    <div class="stat-row">
      <div class="stat">
        <p class="stat-label">จำนวนเคสที่ข้อมูลไม่ครบ</p>
        <p class="stat-value" id="caseCountValue">{esc(all_cases_total)}</p>
      </div>
    </div>

    <div class="panel" id="progress">
      <div class="panel-body">
        <p class="section-title">ความคืบหน้าการแก้ไข</p>
        <p class="section-sub" id="progressCaption">เดือนนี้</p>
        <div class="progress-stats">
          <div class="progress-stat">
            <p class="progress-stat-label">เคสทั้งหมด</p>
            <p class="progress-stat-value" id="progTotal">0</p>
          </div>
          <div class="progress-stat">
            <p class="progress-stat-label progress-warn">รอแก้ไข</p>
            <p class="progress-stat-value progress-warn" id="progPending">0</p>
          </div>
          <div class="progress-stat">
            <p class="progress-stat-label progress-ok">แก้ไขแล้ว</p>
            <p class="progress-stat-value progress-ok" id="progResolved">0</p>
          </div>
        </div>
        <div class="progress-track">
          <div class="progress-fill-resolved" id="progFillResolved" style="width:0%"></div>
          <div class="progress-fill-pending" id="progFillPending" style="width:0%"></div>
        </div>
        <p class="progress-pct" id="progPct">0% แก้ไขแล้ว</p>
      </div>
    </div>

    <div class="panel" id="chart">
      <div class="panel-body">
        <p class="section-sub" id="chartCaption">ยอดเคสทั้งเดือน vs ข้อมูลไม่ครบ (รายวัน) — เดือนนี้</p>
        <div id="chartHost"></div>
      </div>
    </div>

    <div class="panel" id="cases">
      <div class="panel-body">
        <div class="filter-row">
          <label for="monthSelect" class="filter-label">เลือกเดือน:</label>
          {month_select_html}
        </div>
        <div id="month-view-table">{table_html}</div>
      </div>
    </div>

    <footer>อัปเดตอัตโนมัติทุกชั่วโมง · ระบบติดตามข้อมูลทะเบียนผ่าตัด</footer>
  </div>
  <script>
    (function() {{
      var btn = document.getElementById('themeToggle');
      var root = document.documentElement;
      function sync() {{
        btn.textContent = root.getAttribute('data-theme') === 'light' ? '☀️' : '🌙';
      }}
      sync();
      btn.addEventListener('click', function() {{
        var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        root.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        sync();
      }});
    }})();
    {chart_js}
    (function() {{
      var dailyByMonth = {daily_by_month_json};
      var monthLabels = {{}};
      var monthSelectEl = document.getElementById('monthSelect');
      Array.prototype.forEach.call(monthSelectEl.options, function(opt) {{
        monthLabels[opt.value] = opt.textContent;
      }});
      var sel = monthSelectEl;
      var rows = Array.prototype.slice.call(document.querySelectorAll('#allCasesTable tbody tr'));
      var noMsg = document.getElementById('noCasesMsg');
      var countEl = document.getElementById('caseCountValue');
      var chartHost = document.getElementById('chartHost');
      var chartCaption = document.getElementById('chartCaption');
      var monthProgress = {month_progress_json};
      var progTotal = document.getElementById('progTotal');
      var progPending = document.getElementById('progPending');
      var progResolved = document.getElementById('progResolved');
      var progFillResolved = document.getElementById('progFillResolved');
      var progFillPending = document.getElementById('progFillPending');
      var progPct = document.getElementById('progPct');
      var progressCaption = document.getElementById('progressCaption');
      function applyFilter() {{
        var val = sel.value;
        var visible = 0;
        rows.forEach(function(tr) {{
          var show = (val === 'all') || (tr.getAttribute('data-month') === val);
          tr.style.display = show ? '' : 'none';
          if (show) visible++;
        }});
        noMsg.style.display = visible === 0 ? '' : 'none';
        countEl.textContent = visible;
        var daily = dailyByMonth[val] || [];
        chartHost.innerHTML = renderBarChart(daily);
        var label = monthLabels[val] || val;
        chartCaption.textContent = val === 'all'
          ? 'ยอดเคสทั้งเดือน vs ข้อมูลไม่ครบ (รายเดือน) — ทั้งหมด'
          : 'ยอดเคสทั้งเดือน vs ข้อมูลไม่ครบ (รายวัน) — ' + label;
        var prog = monthProgress[val] || {{ total: 0, pending: 0, resolved: 0 }};
        progTotal.textContent = prog.total;
        progPending.textContent = prog.pending;
        progResolved.textContent = prog.resolved;
        var resolvedPct = prog.ever ? (prog.resolved / prog.ever) * 100 : 0;
        var pendingPct = prog.ever ? (prog.pending / prog.ever) * 100 : 0;
        progFillResolved.style.width = resolvedPct + '%';
        progFillPending.style.width = pendingPct + '%';
        var pctDisplay = prog.ever ? Math.round((prog.resolved / prog.ever) * 1000) / 10 : 100;
        progPct.textContent = pctDisplay + '% แก้ไขแล้ว (' + prog.resolved + '/' + prog.ever + ' เคสที่เคยไม่ครบ)';
        progressCaption.textContent = val === 'all' ? 'ทั้งหมด' : label;
      }}
      sel.addEventListener('change', applyFilter);
      applyFilter();

      document.getElementById('reportBtn').addEventListener('click', function() {{
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

        var visibleRows = rows.filter(function(tr) {{ return tr.style.display !== 'none'; }});
        var cases = visibleRows.map(function(tr) {{
          var tds = tr.querySelectorAll('td');
          var missing = Array.prototype.map.call(tds[6].querySelectorAll('.chip'), function(c) {{ return c.textContent; }});
          var circNames = Array.prototype.map.call(tds[5].querySelectorAll('.circ-name'), function(c) {{ return c.textContent; }});
          return {{
            date: tds[0].textContent.trim(),
            hn: tds[1].textContent.trim(),
            name: tds[2].textContent.trim(),
            dept: tds[3].textContent.trim(),
            op: tds[4].textContent.trim(),
            circ: circNames.join(', '),
            missing: missing,
            days: tds[7].textContent.trim()
          }};
        }});

        var monthLabel = monthLabels[sel.value] || sel.value;
        var W = 1000, pad = 32;
        var rowH = 56;
        var H = 140 + Math.max(cases.length, 1) * rowH + 60;
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
        ctx.fillText('เดือน: ' + monthLabel + ' · จำนวน ' + cases.length + ' เคส · ส่งออก ' + new Date().toLocaleString('th-TH'), pad, y);
        y += 30;

        if (cases.length === 0) {{
          ctx.fillStyle = ok;
          ctx.font = '600 15px -apple-system, sans-serif';
          ctx.fillText('ครบ ✅ ไม่มีเคสข้อมูลไม่ครบ', pad, y + 10);
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
            var rowTop = y - 14;
            ctx.fillStyle = panelBg;
            ctx.fillRect(pad - 8, rowTop, W - pad * 2 + 16, rowH - 6);
            ctx.fillStyle = text;
            ctx.font = '400 12px -apple-system, sans-serif';
            ctx.fillText(c.date, colX.date, y);
            ctx.fillText(c.hn, colX.hn, y);
            ctx.font = '600 12px -apple-system, sans-serif';
            ctx.fillText(c.name.slice(0, 22), colX.name, y);
            ctx.font = '400 12px -apple-system, sans-serif';
            ctx.fillText(c.dept, colX.dept, y);
            var mx = colX.missing;
            c.missing.forEach(function(m) {{
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
            ctx.fillText(c.days ? (c.days + ' วัน') : '-', colX.days, y);
            ctx.font = '400 11px -apple-system, sans-serif';
            ctx.fillStyle = textMuted;
            ctx.fillText(c.op.slice(0, 60) + (c.circ ? ' · Circ: ' + c.circ.slice(0, 40) : ''), colX.date, y + 18);
            y += rowH;
          }});
        }}

        canvas.toBlob(function(blob) {{
          var a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = 'missing-data-report-' + (sel.value === 'all' ? 'all' : sel.value) + '.png';
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
