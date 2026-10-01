#!/usr/bin/env python3
"""Generate dashboard.html — an interactive fiscal-year / month view.

Every panel is redrawn from a single shared selection through assets/audit_ui.js
(the same engine index.html uses), so no panel can keep stale numbers after the
user switches ปีงบ/เดือน. Scope with no finished cases shows
"ยังไม่มีข้อมูลสิ้นสุดวัน" instead of a fake 0-case 100% badge.

Visual design stays identical to build_html.py (dark/light, sharp corners).
"""
import json
import html
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "audit_data.json"
OUT_PATH = BASE_DIR / "dashboard.html"
ASSETS_DIR = BASE_DIR / "assets"


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def asset_version(name: str, fallback: str = "1") -> str:
    """Cache-busting token from the shared asset's mtime."""
    path = ASSETS_DIR / name
    try:
        return str(int(path.stat().st_mtime))
    except OSError:
        return fallback


def render_case_rows(all_cases: list) -> str:
    """Every currently-flagged case, tagged data-key="HN|date" for the engine."""
    rows = []
    for c in all_cases or []:
        missing = c.get("missing", []) or []
        missing_html = "".join(
            f'<span class="chip chip-warn" data-rule="{esc(m)}" title="กดเพื่อดูคำอธิบาย">{esc(m)}</span>' for m in missing
        )
        pair_html = "".join(
            f'<div class="pair-line">HN{esc(p.get("hn", ""))} วันที่ {esc(p.get("date", ""))} ({esc(p.get("tag", ""))} {esc(p.get("minutes", ""))} นาที)</div>'
            for p in (c.get("pair", []) or [])
        )
        times = c.get("times", []) or []
        time_html = (f'<div class="pair-line">เข้า {esc(times[0])} เริ่ม {esc(times[1])} เสร็จ {esc(times[2])} ออก {esc(times[3])}</div>'
                     if len(times) == 4 else "")
        days = c.get("days_pending")
        days_html = f"{esc(days)} วัน" if days is not None else "-"
        circ_names = [n.strip() for n in (c.get("circ", "") or "").split(",") if n.strip()]
        circ_html = '<div class="circ-names">' + "".join(
            f'<span class="circ-name">{esc(n)}</span>' for n in circ_names
        ) + "</div>"
        key = f'{c.get("hn", "")}|{c.get("date", "")}'
        rows.append(
            f'''<tr data-key="{esc(key)}" data-month="{esc(c.get("month_key", ""))}">
        <td data-label="วันที่">{esc(c.get("date", ""))}</td>
        <td data-label="HN">{esc(c.get("hn", ""))}</td>
        <td data-label="ชื่อ" class="name-cell">{esc(c.get("name", ""))}</td>
        <td data-label="แผนก">{esc(c.get("dept", ""))}</td>
        <td data-label="การผ่าตัด">{esc(c.get("op", ""))}</td>
        <td data-label="Circulating" class="circ-cell">{circ_html}</td>
        <td data-label="ข้อมูลที่ขาด">{missing_html}{pair_html}{time_html}</td>
        <td data-label="รอแก้ไข">{days_html}</td>
      </tr>'''
        )
    return "\n".join(rows)


def dataset_for_embedding(data: dict) -> dict:
    """Everything the engine needs; drop the legacy block to keep the page lean."""
    return {k: v for k, v in data.items() if k != "legacy"}


# Plain (non-f-string) template so CSS/JS braces need no escaping.
TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="dark">
<title>__TITLE__</title>
<script>
(function () {
  var t = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', t);
})();
</script>
<style>
  :root {
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
    --bad: #f87171;
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
    --bad: #b91c1c;
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

  .mono, .stat-value { font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; }

  .wrap { max-width: 900px; margin: 0 auto; }

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

  .theme-toggle {
    margin-left: auto;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 0;
    color: var(--text);
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.95rem;
    cursor: pointer;
  }

  .theme-toggle:hover { background: var(--bg-muted); }

  .tabs { display: flex; gap: 4px; flex-wrap: wrap; margin-left: 4px; }

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
    border-radius: 0;
    margin-bottom: -1px;
    position: relative;
    top: 3px;
    transition: top 0.15s ease, color 0.15s ease;
  }

  .tab:hover { color: var(--text); top: 1px; }

  .tab.active {
    color: var(--accent);
    background: var(--bg);
    border-color: var(--border);
    top: 0;
    z-index: 1;
    box-shadow: 2px -2px 4px rgba(0, 0, 0, 0.15);
  }

  .page-head { padding: 22px 2px 14px; }

  .page-title {
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 0 0 6px;
    color: var(--text);
  }

  .page-sub { color: var(--text-muted); font-size: 0.88rem; margin: 0; }
  .scope-note { font-size: 0.74rem; color: var(--text-muted); margin: 6px 0 0; }

  .all-clear { color: var(--ok); font-weight: 600; margin: 0; }
  .warn-sub { color: var(--warn); font-weight: 600; margin: 6px 0 0; }

  .empty-state.empty-warn { color: var(--warn); border-color: rgba(251, 191, 36, 0.35); }
  .empty-state.empty-warn line-break { display: block; }

  .stat-row { display: flex; flex-wrap: wrap; gap: 10px; margin: 0 0 16px; }

  .stat {
    flex: 1 1 140px;
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    border-radius: 0;
    padding: 12px 14px;
    text-align: center;
  }

  .stat-label { font-size: 0.75rem; color: var(--text-muted); margin: 0 0 6px; }
  .stat-value { font-size: 1.35rem; font-weight: 700; color: var(--text); margin: 0; line-height: 1.2; text-align: center; }
  .pct-good { color: var(--ok); }
  .pct-warn { color: var(--warn); }
  .pct-bad { color: var(--bad); }

  .panel {
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    border-radius: 0;
    margin-bottom: 18px;
    overflow: hidden;
  }

  .panel-body { padding: 16px 14px; }

  .section-title { font-size: 1.05rem; font-weight: 650; color: var(--text); margin: 0 0 4px; }
  .section-sub { color: var(--text-muted); font-size: 0.85rem; margin: 0 0 14px; }

  .trend-line { font-size: 0.95rem; font-weight: 600; margin: 0; }
  .trend-up { color: var(--ok); }
  .trend-down { color: var(--bad); }
  .trend-flat { color: var(--text-muted); }

  .dept-row {
    display: grid;
    grid-template-columns: 110px 1fr 190px;
    align-items: center;
    gap: 10px;
    padding: 8px 4px;
    border-bottom: 1px solid var(--border-soft);
    font-size: 0.85rem;
  }

  .dept-row:last-child { border-bottom: none; }
  .dept-name { color: var(--text); font-weight: 600; }
  .dept-track { background: var(--bg-muted); height: 10px; position: relative; }
  .dept-fill { background: var(--accent); height: 100%; opacity: 0.85; }
  .dept-nums { color: var(--text-muted); font-size: 0.78rem; text-align: right; }
  .dept-warn { color: var(--warn); font-weight: 600; }
  .dept-ok { color: var(--ok); font-weight: 600; }

  .col-row {
    display: grid;
    grid-template-columns: 160px 1fr 32px;
    align-items: center;
    gap: 10px;
    padding: 7px 4px;
    border-bottom: 1px solid var(--border-soft);
    font-size: 0.85rem;
  }

  .col-row:last-child { border-bottom: none; }
  .col-name { color: var(--text); }
  .col-track { background: var(--bg-muted); height: 10px; }
  .col-fill { background: var(--warn); height: 100%; }
  .col-count { color: var(--text-muted); text-align: right; font-weight: 600; }

  .dept-row.dept-active, .col-row.col-active { outline: 1px solid var(--accent); background: var(--bg-elevated); }

  .table-wrap { overflow-x: auto; }

  .data-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }

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
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  }

  .data-table tbody tr:last-child td { border-bottom: none; }
  .data-table tbody tr:hover { background: var(--bg-elevated); }
  .name-cell { white-space: nowrap; }
  .circ-cell { font-weight: 700; color: var(--accent); }
  .circ-name { display: block; white-space: nowrap; }

  .chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 0;
    font-size: 0.7rem;
    font-weight: 600;
    margin: 2px 4px 2px 0;
    white-space: nowrap;
  }

  .chip-warn { background: rgba(251, 191, 36, 0.13); color: var(--warn); border: 1px solid rgba(251, 191, 36, 0.28); }
  .chip-blank { background: var(--bg-muted); color: var(--text-muted); border: 1px solid var(--border); }

  .progress-stats { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
  .progress-stat { flex: 1 1 90px; text-align: center; background: var(--bg-elevated); border: 1px solid var(--border-soft); border-radius: 0; padding: 10px 8px; }
  .progress-stat-label { font-size: 0.72rem; color: var(--text-muted); margin: 0 0 4px; }
  .progress-stat-value { font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 1.4rem; font-weight: 650; color: var(--text); margin: 0; }
  .progress-warn { color: var(--warn); }
  .progress-ok { color: var(--ok); }

  .progress-track { width: 100%; height: 14px; background: var(--bg-muted); overflow: hidden; display: flex; }
  .progress-fill-resolved {
    height: 100%;
    min-width: 8px;
    flex-shrink: 0;
    background: repeating-linear-gradient(45deg, var(--ok) 0, var(--ok) 4px, #ffffff88 4px, #ffffff88 8px);
    background-color: var(--ok);
  }
  .progress-fill-pending { height: 100%; min-width: 8px; flex-shrink: 0; background: var(--warn); }
  .progress-fill-rest { height: 100%; flex: 1 1 auto; background: var(--ok); }
  .progress-pct { margin: 8px 0 0; font-size: 0.82rem; color: var(--text-muted); text-align: right; }

  .chart-wrap { padding-top: 4px; }
  .chart-legend { display: flex; gap: 16px; margin-bottom: 12px; font-size: 0.78rem; color: var(--text-muted); }
  .legend-item { display: inline-flex; align-items: center; gap: 6px; }
  .legend-dot { width: 10px; height: 10px; display: inline-block; }
  .legend-ok { background: var(--ok); }
  .legend-missing { background: var(--warn); }

  .bar-chart { display: flex; align-items: flex-end; gap: 3px; height: 160px; overflow-x: auto; padding-bottom: 4px; }
  .bar-col { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; flex: 1 0 18px; height: 100%; min-width: 18px; }
  .bar-stack { width: 100%; display: flex; flex-direction: column; justify-content: flex-end; background: var(--bg-muted); min-height: 2px; }
  .bar-seg { width: 100%; }
  .bar-missing { background: var(--warn); }
  .bar-ok { background: var(--ok); }
  .bar-label { font-size: 0.62rem; color: var(--text-dim); margin-top: 4px; }

  footer { text-align: center; color: var(--text-dim); font-size: 0.78rem; margin-top: 28px; }

  @media (max-width: 640px) {
    body { padding: 0 10px 56px; }
    .page-title { font-size: 1.2rem; }
    .stat { flex: 1 1 90px; }
    .stat-value { font-size: 1.15rem; }
    .dept-row { grid-template-columns: 84px 1fr; grid-template-areas: "name nums" "track track"; row-gap: 4px; }
    .dept-name { grid-area: name; }
    .dept-nums { grid-area: nums; }
    .dept-track { grid-area: track; }
    .col-row { grid-template-columns: 110px 1fr 28px; }
    .data-table thead { display: none; }
    .data-table, .data-table tbody, .data-table tr, .data-table td { display: block; width: 100%; }
    .data-table tr { border: 1px solid var(--border-soft); border-radius: 0; margin-bottom: 10px; padding: 8px 12px; background: var(--bg-elevated); }
    .data-table td { border-bottom: none; padding: 4px 0; display: flex; justify-content: space-between; gap: 10px; text-align: right; }
    .data-table td::before { content: attr(data-label); font-weight: 600; color: var(--text-muted); text-align: left; flex: 0 0 auto; }
    .data-table td.circ-cell { align-items: flex-start; text-align: right; }
    .circ-names { display: flex; flex-direction: column; align-items: flex-end; }
  }
</style>
<link rel="stylesheet" href="assets/audit_ui.css?v=__UI_CSS_VER__">
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <nav class="tabs">
        <a class="tab active" href="dashboard.html">Dashboard</a>
        <a class="tab" href="index.html">ข้อมูล</a>
      </nav>
      <button class="theme-toggle" id="reportBtn" type="button" aria-label="Export report" title="Export เป็นรูปภาพ" style="margin-left:auto">📄</button>
      <button class="theme-toggle" id="themeToggle" type="button" aria-label="สลับโหมดสี" style="margin-left:6px">🌙</button>
    </div>

    <div class="page-head">
      <h1 class="page-title">Dashboard สรุปภาพรวม</h1>
      <p class="page-sub" id="pageSub">—</p>
      <p class="scope-note" id="scopeNote">—</p>
    </div>

    <!-- ONE filter row: drives every panel + the case table below -->
    <div class="audit-filters">
      <div class="filter-field">
        <label class="filter-label" for="fySelect">ปีงบประมาณ</label>
        <select id="fySelect" class="audit-select"></select>
      </div>
      <div class="filter-field">
        <label class="filter-label" for="monthSelect">เดือน</label>
        <select id="monthSelect" class="month-select"></select>
      </div>
      <div class="filter-field grow">
        <label class="filter-label" for="caseSearch">ค้นหาเคส (HN / ชื่อ / แผนก / การผ่าตัด)</label>
        <input id="caseSearch" class="audit-input" type="search" placeholder="พิมพ์เพื่อค้นหา…" autocomplete="off">
      </div>
      <div class="filter-field">
        <label class="filter-label" for="pageSize">ต่อหน้า</label>
        <select id="pageSize" class="audit-select">
          <option value="50">50</option>
          <option value="100">100</option>
          <option value="200">200</option>
          <option value="" selected>ทั้งหมด</option>
        </select>
      </div>
    </div>
    <div class="filter-chips" id="activeFilters"></div>

    <div id="emptyBanner" class="empty-state empty-warn" style="display:none;margin-bottom:16px"></div>

    <div class="stat-row">
      <div class="stat">
        <p class="stat-label">% ความครบถ้วน</p>
        <p class="stat-value pct-none" id="statPct">—</p>
      </div>
      <div class="stat">
        <p class="stat-label">เคสทั้งหมด</p>
        <p class="stat-value" id="statFinished">0</p>
      </div>
      <div class="stat">
        <p class="stat-label">เคสข้อมูลไม่ครบ</p>
        <p class="stat-value" id="statMissing">0</p>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <p class="section-title">แนวโน้มเทียบเดือนก่อน / ปีงบก่อน</p>
        <p class="section-sub" id="trendCaption"></p>
        <div id="trendHost"></div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <p class="section-title">ยอดเคส vs ข้อมูลไม่ครบ</p>
        <p class="section-sub" id="chartCaption"></p>
        <div id="chartHost"></div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <p class="section-title">แยกตามแผนก</p>
        <p class="section-sub" id="deptSub"></p>
        <div id="deptHost"></div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <p class="section-title">ช่องที่ขาดบ่อยสุด</p>
        <p class="section-sub" id="missingSub"></p>
        <div id="missingHost"></div>
      </div>
    </div>

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
          <div class="progress-stat">
            <p class="progress-stat-label progress-ok">แก้ไขแล้ว</p>
            <p class="progress-stat-value progress-ok" id="progResolved">0</p>
          </div>
        </div>
        <div class="progress-track">
          <div class="progress-fill-rest" id="progFillRest" style="width:0%"></div>
          <div class="progress-fill-resolved" id="progFillResolved" style="width:0%"></div>
          <div class="progress-fill-pending" id="progFillPending" style="width:0%"></div>
        </div>
        <p class="progress-pct" id="progPct">—</p>
      </div>
    </div>

    <div class="panel" id="cases">
      <div class="panel-body">
        <p class="section-title">เคสข้อมูลไม่ครบในขอบเขตที่เลือก</p>
        <p class="section-sub" id="casesSub"></p>
        <div class="table-wrap">
          <table class="data-table" id="allCasesTable">
            <thead>
              <tr>
                <th data-sort="date">วันที่</th>
                <th data-sort="hn">HN</th>
                <th data-sort="name">ชื่อ</th>
                <th data-sort="dept">แผนก</th>
                <th data-sort="op">การผ่าตัด</th>
                <th>Circulating</th>
                <th>ข้อมูลที่ขาด</th>
                <th data-sort="days">รอแก้ไข</th>
              </tr>
            </thead>
            <tbody>
__CASE_ROWS__
            </tbody>
          </table>
          <p class="all-clear" id="noCasesMsg" style="display:none">ครบ ✅ ไม่มีเคสข้อมูลไม่ครบในขอบเขตที่เลือก</p>
        </div>
        <div class="audit-pager" id="pager" style="display:none"></div>
      </div>
    </div>

    <footer>อัปเดตอัตโนมัติทุกชั่วโมง · ระบบติดตามข้อมูลทะเบียนผ่าตัด</footer>
  </div>

  <script src="assets/audit_ui.js?v=__UI_JS_VER__"></script>
  <script>
  window.AUDIT_DATA = __DATA_JSON__;
  </script>
  <script>
  (function () {
    var DATA = window.AUDIT_DATA;
    var META = { gen: "__GEN_TIME__", as_of: "__AS_OF__", rows: __ROWS__ };
    var currentSel = null;

    function $(id) { return document.getElementById(id); }
    function pct1(x) { return Math.round(x * 10) / 10; }
    function setText(id, txt) { var el = $(id); if (el) el.textContent = txt; }
    function setHtml(id, html) { var el = $(id); if (el) el.innerHTML = html; }

    // ---- theme toggle ---------------------------------------------------
    (function () {
      var btn = $('themeToggle'), root = document.documentElement;
      function sync() { btn.textContent = root.getAttribute('data-theme') === 'light' ? '☀️' : '🌙'; }
      sync();
      btn.addEventListener('click', function () {
        var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        root.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        sync();
      });
    })();

    // ---- trend vs previous month / FY -----------------------------------
    function trendInfo(data, sel) {
      var b = AuditUI.block(data, sel) || {};
      var cur = b.completeness_pct;
      var isFy = AuditUI.isFyScope(sel);
      var prev = null, prevName = '', delta = null;
      if (isFy) {
        delta = b.trend_vs_prev;
        prevName = b.prev_label || '';
        if (cur == null || delta == null) {
          return { text: 'รอข้อมูล — ขอบเขตนี้ยังไม่มีเคสสิ้นสุดวันให้คำนวณ %', dir: 'none' };
        }
        prev = pct1(cur - delta);
      } else {
        var keys = Object.keys(data.periods || {}).sort();
        var i = keys.indexOf(sel.month);
        var pb = i > 0 ? (data.periods[keys[i - 1]] || null) : null;
        prevName = pb ? pb.label : '';
        if (cur == null) {
          return { text: 'รอข้อมูล — เดือนนี้ยังไม่มีเคสสิ้นสุดวันให้คำนวณ %', dir: 'none' };
        }
        if (!pb || pb.completeness_pct == null) {
          return { text: 'รอข้อมูล — ' + (prevName ? 'ยังไม่มีข้อมูลเดือนก่อนหน้า (' + prevName + ')' : 'ไม่มีเดือนก่อนหน้าให้เทียบ'), dir: 'none' };
        }
        prev = pb.completeness_pct;
        delta = pct1(cur - prev);
      }
      var dir = delta > 0 ? 'up' : (delta < 0 ? 'down' : 'flat');
      var arrow = delta > 0 ? '▲' : (delta < 0 ? '▼' : '■');
      var word = delta > 0 ? 'ดีขึ้น' : (delta < 0 ? 'แย่ลง' : 'เท่าเดิม');
      var who = isFy ? 'ปีงบก่อนหน้า' : 'เดือนก่อนหน้า';
      return {
        text: arrow + ' ' + pct1(Math.abs(delta)) + ' จุด (' + word + ') — เทียบ' + who + ' ' +
              (prevName || '-') + ' (' + prev + '%) · ปัจจุบัน ' + cur + '%',
        dir: dir
      };
    }

    function renderTrend(data, sel) {
      var t = trendInfo(data, sel);
      var cls = t.dir === 'up' ? 'trend-up' : (t.dir === 'down' ? 'trend-down' : 'trend-flat');
      return '<p class="trend-line ' + cls + '">' + AuditUI.esc(t.text) + '</p>';
    }

    // ---- department breakdown (drill-down) ------------------------------
    function renderDepts(data, sel, empty) {
      var b = AuditUI.block(data, sel) || {};
      var rows = b.dept_breakdown || [];
      if (!rows.length) return '<p class="scope-note">' + (empty ? 'ยังไม่มีข้อมูลสิ้นสุดวัน' : 'ไม่มีข้อมูล') + '</p>';
      var max = 0;
      rows.forEach(function (d) { if ((d.total || 0) > max) max = d.total; });
      if (!max) max = 1;
      return rows.map(function (d) {
        var total = d.total || 0, missing = d.missing || 0;
        var w = Math.round((total / max) * 1000) / 10;
        var mp = total ? Math.round((missing / total) * 1000) / 10 : 0;
        var cls = missing ? 'dept-warn' : 'dept-ok';
        var active = sel.dept === d.dept ? ' dept-active' : '';
        return '<div class="dept-row' + active + '" data-drill="dept" data-value="' + AuditUI.esc(d.dept) + '" title="คลิกเพื่อกรองเฉพาะแผนก ' + AuditUI.esc(d.dept) + '">' +
          '<div class="dept-name">' + AuditUI.esc(d.dept) + '</div>' +
          '<div class="dept-track"><div class="dept-fill" style="width:' + w + '%"></div></div>' +
          '<div class="dept-nums">' + total + ' เคส · <span class="' + cls + '">' + missing + ' ไม่ครบ (' + mp + '%)</span></div>' +
        '</div>';
      }).join('');
    }

    // ---- top missing columns (drill-down) -------------------------------
    function renderMissing(data, sel, empty) {
      var b = AuditUI.block(data, sel) || {};
      var cols = b.top_missing_cols || [];
      if (!cols.length) {
        return '<p class="' + (empty ? 'scope-note' : 'all-clear') + '">' + (empty ? 'ยังไม่มีข้อมูลสิ้นสุดวัน' : 'ครบ ✅ ไม่มีช่องขาด') + '</p>';
      }
      var max = 0;
      cols.forEach(function (c) { if ((c.count || 0) > max) max = c.count; });
      if (!max) max = 1;
      return cols.map(function (c) {
        var w = Math.round(((c.count || 0) / max) * 1000) / 10;
        var active = sel.col === c.col ? ' col-active' : '';
        return '<div class="col-row' + active + '" data-drill="col" data-value="' + AuditUI.esc(c.col) + '" title="คลิกเพื่อกรองเคสที่ขาด ' + AuditUI.esc(c.col) + '">' +
          '<div class="col-name">' + AuditUI.esc(c.col) + '</div>' +
          '<div class="col-track"><div class="col-fill" style="width:' + w + '%"></div></div>' +
          '<div class="col-count">' + (c.count || 0) + '</div>' +
        '</div>';
      }).join('');
    }

    // The engine's bar markup has data-day/data-month but no data-drill, so we
    // add the drill attributes here (engine's click handler picks them up).
    function injectDrill(html) {
      return String(html)
        .replace(/class="bar-col" data-day="(\d+)"/g, 'data-drill="day" data-value="$1" class="bar-col" data-day="$1"')
        .replace(/class="bar-col" data-month="([^"]+)"/g, 'data-drill="month" data-value="$1" class="bar-col" data-month="$1"');
    }

    // ---- progress (same semantics as index.html) ------------------------
    function renderProgress(data, sel, scope) {
      var p = AuditUI.progressHtml(data, sel);
      var g = p.prog || { total: 0, pending: 0, resolved: 0, ever: 0 };
      setText('progTotal', g.total || 0);
      setText('progPending', g.pending || 0);
      setText('progResolved', g.resolved || 0);
      $('progFillResolved').style.width = p.resolvedPct + '%';
      $('progFillPending').style.width = p.pendingPct + '%';
      $('progFillRest').style.width = p.restPct + '%';
      setText('progressCaption', scope + (AuditUI.isFyScope(sel) ? ' (ทั้งปีงบ)' : ''));
      $('progPct').textContent = g.ever
        ? (pct1((g.resolved / g.ever) * 100) + '% แก้ไขแล้ว (' + (g.resolved || 0) + '/' + g.ever + ' เคสที่เคยถูกแจ้งบนเว็บ)')
        : '— ยังไม่มีเคสที่เคยถูกแจ้งบนเว็บในขอบเขตนี้';
    }

    // ---- main render: every panel is regenerated from (data, sel) -------
    function render(sel, data, res) {
      currentSel = sel;
      var b = AuditUI.block(data, sel) || {};
      var isFy = AuditUI.isFyScope(sel);
      var scope = AuditUI.scopeLabel(data, sel);
      var finished = b.finished || 0;
      var missing = b.missing || 0;
      var empty = finished <= 0;

      setText('pageSub', scope + ' · อัปเดตล่าสุด ' + META.gen);
      setHtml('scopeNote', 'คำนวณสดจากทะเบียน ณ ' + AuditUI.esc(META.gen) + ' · ข้อมูล ณ ' + AuditUI.esc(META.as_of) +
        ' · ' + (isFy ? 'ภาพรวมทั้งปีงบ (สะสมทุกเดือน)' : 'ภาพรวมรายเดือน') + ' · ทะเบียน ' + META.rows + ' แถว');

      var banner = $('emptyBanner');
      if (empty) {
        banner.style.display = '';
        banner.innerHTML = '⚠ ยังไม่มีข้อมูลสิ้นสุดวันสำหรับ' + (isFy ? 'ปีงบนี้' : 'เดือนนี้') +
          (b.unfinished ? ' — มีเคสยังไม่ลงเวลาเสร็จ ' + b.unfinished + ' เคส' : '') +
          '<br>ยังไม่นับ % ความครบถ้วน (ไม่รายงานว่า “ครบ 100%” เมื่อยังไม่มีเคส)';
      } else {
        banner.style.display = 'none';
        banner.innerHTML = '';
      }

      var ct = AuditUI.completenessText(data, sel);
      var pctEl = $('statPct');
      pctEl.textContent = ct.text;
      pctEl.className = 'stat-value ' + ct.cls;
      setText('statFinished', finished);
      setText('statMissing', missing);

      setText('trendCaption', isFy
        ? ('เทียบกับ ' + ((b.prev_label) || 'ปีงบก่อนหน้า'))
        : 'เทียบกับเดือนก่อนหน้าตามปฏิทินการติดตาม');
      setHtml('trendHost', renderTrend(data, sel));

      setText('chartCaption', isFy
        ? 'ยอดเคสรายเดือน vs ข้อมูลไม่ครบ — ' + scope + ' · คลิกแท่งเพื่อเจาะดูเดือนนั้น'
        : 'ยอดเคสรายวัน vs ข้อมูลไม่ครบ — ' + scope + ' · คลิกแท่งเพื่อกรองวันนั้น');
      setHtml('chartHost', injectDrill(AuditUI.chartHtml(data, sel)));

      setText('deptSub', 'ความยาวแท่ง = สัดส่วนจำนวนเคส · ป้าย = % ข้อมูลไม่ครบ · คลิกแผนกเพื่อกรอง');
      setHtml('deptHost', renderDepts(data, sel, empty));

      setText('missingSub', 'สะสม' + (isFy ? 'ทั้งปีงบ' : 'ทั้งเดือน') + ' รวมเคสที่แก้ไขแล้ว · คลิกช่องเพื่อกรองเฉพาะช่องนั้น');
      setHtml('missingHost', renderMissing(data, sel, empty));

      renderProgress(data, sel, scope);

      var shown = res ? res.total : 0;
      setText('casesSub', 'เคสที่ถูกแจ้งในขอบเขตนี้ ' + shown + ' เคส' +
        (sel.dept ? ' · แผนก ' + sel.dept : '') +
        (sel.col ? ' · ขาด ' + sel.col : '') +
        (sel.day ? ' · วันที่ ' + sel.day : '') +
        (sel.q ? ' · ค้นหา “' + sel.q + '”' : '') +
        (shown === 0 ? (empty ? ' · ยังไม่มีข้อมูลสิ้นสุดวัน' : ' · ไม่มีเคสค้าง') : ''));

      var noMsg = $('noCasesMsg');
      if (noMsg) {
        noMsg.textContent = empty
          ? 'ยังไม่มีข้อมูลสิ้นสุดวันในขอบเขตนี้ — ยังไม่มีเคสให้ตรวจ'
          : 'ครบ ✅ ไม่มีเคสข้อมูลไม่ครบในขอบเขตที่เลือก';
      }
    }

    // ---- PNG export (pure canvas, current theme, current selection) -----
    function exportPng() {
      var sel = currentSel, data = DATA;
      if (!sel) return;
      var isLight = (document.documentElement.getAttribute('data-theme') || 'dark') === 'light';
      var C = {
        bg: isLight ? '#f5f5f6' : '#0b0b0c',
        panel: isLight ? '#ffffff' : '#151517',
        track: isLight ? '#e4e4e7' : '#1f1f23',
        border: isLight ? '#d4d4d8' : '#27272b',
        text: isLight ? '#18181b' : '#ededed',
        textMuted: isLight ? '#52525b' : '#8b8b90',
        ok: isLight ? '#15803d' : '#4ade80',
        warn: isLight ? '#b45309' : '#fbbf24',
        bad: isLight ? '#b91c1c' : '#f87171',
        accent: isLight ? '#000000' : '#ffffff',
        warnBg: isLight ? 'rgba(180,83,9,0.12)' : 'rgba(251,191,36,0.13)'
      };
      var b = AuditUI.block(data, sel) || {};
      var scope = AuditUI.scopeLabel(data, sel);
      var isFy = AuditUI.isFyScope(sel);
      var ct = AuditUI.completenessText(data, sel);
      var tr = trendInfo(data, sel);
      var pr = AuditUI.progressHtml(data, sel);
      var depts = b.dept_breakdown || [];
      var cols = b.top_missing_cols || [];
      var chartData = isFy ? (b.monthly || []) : (b.daily || []);

      var visRows = Array.prototype.filter.call(
        document.querySelectorAll('#allCasesTable tbody tr'),
        function (row) { return row.style.display !== 'none'; }
      );
      var cases = visRows.map(function (row) {
        var td = row.querySelectorAll('td');
        return {
          date: td[0].textContent.trim(), hn: td[1].textContent.trim(), name: td[2].textContent.trim(),
          dept: td[3].textContent.trim(), op: td[4].textContent.trim(),
          circ: Array.prototype.map.call(td[5].querySelectorAll('.circ-name'), function (n) { return n.textContent; }).join(', '),
          missing: Array.prototype.map.call(td[6].querySelectorAll('.chip'), function (n) { return n.textContent; }),
          days: td[7].textContent.trim()
        };
      });
      var chips = Array.prototype.map.call(
        document.querySelectorAll('#activeFilters .filter-chip'),
        function (c) { return c.textContent.replace(/\s*✕\s*$/, ''); }
      );

      var W = 1000, pad = 32, scale = 2, statH = 68, rowH = 50, chartH = 120;
      var H = pad + 28 + 22 + 26
        + statH + 26
        + (ct.empty ? 26 : 0)
        + 22 + 26
        + 22 + chartH + 26
        + 22 + Math.max(depts.length, 1) * 28 + 14
        + 22 + Math.max(cols.length, 1) * 24 + 14
        + 22 + 22
        + 26 + Math.max(cases.length, 1) * rowH
        + 56;
      var canvas = document.createElement('canvas');
      canvas.width = W * scale;
      canvas.height = H * scale;
      var ctx = canvas.getContext('2d');
      ctx.scale(scale, scale);
      ctx.fillStyle = C.bg;
      ctx.fillRect(0, 0, W, H);

      function label(txt, x, y, font, color, align) {
        ctx.font = font;
        ctx.fillStyle = color;
        ctx.textAlign = align || 'left';
        ctx.fillText(txt, x, y);
        ctx.textAlign = 'left';
      }
      function heading(txt, y) { label(txt, pad, y, '650 15px "Segoe UI",sans-serif', C.text); }

      var y = pad + 26;
      label('Dashboard สรุปภาพรวม', pad, y, '700 24px "Segoe UI",sans-serif', C.text);
      y += 22;
      label(scope + ' · ส่งออก ' + META.as_of + ' ' + META.gen, pad, y, '400 13px "Segoe UI",sans-serif', C.textMuted);
      y += 20;
      label('คำนวณสดจากทะเบียน ณ ' + META.gen, pad, y, '400 12px "Segoe UI",sans-serif', C.textMuted);
      if (chips.length) {
        y += 18;
        label('กรองอยู่: ' + chips.join(' · '), pad, y, '600 12px "Segoe UI",sans-serif', C.warn);
      }
      y += 26;

      var statW = (W - pad * 2 - 20) / 3;
      var pctColor = ct.empty ? C.textMuted : (b.completeness_pct >= 97 ? C.ok : (b.completeness_pct >= 90 ? C.warn : C.bad));
      function card(x, lab, val, color) {
        ctx.fillStyle = C.panel;
        ctx.strokeStyle = C.border;
        ctx.fillRect(x, y, statW, statH);
        ctx.strokeRect(x, y, statW, statH);
        ctx.textAlign = 'center';
        ctx.fillStyle = C.textMuted;
        ctx.font = '400 12px "Segoe UI",sans-serif';
        ctx.fillText(lab, x + statW / 2, y + 24);
        ctx.fillStyle = color || C.text;
        ctx.font = '700 23px "Segoe UI",sans-serif';
        ctx.fillText(String(val), x + statW / 2, y + 52);
        ctx.textAlign = 'left';
      }
      card(pad, '% ความครบถ้วน', ct.text, pctColor);
      card(pad + statW + 10, 'เคสทั้งหมด', b.finished || 0, C.text);
      card(pad + (statW + 10) * 2, 'เคสข้อมูลไม่ครบ', b.missing || 0, C.text);
      y += statH + 26;

      if (ct.empty) {
        label('⚠ ยังไม่มีข้อมูลสิ้นสุดวัน — ยังไม่นับ % ความครบถ้วน', pad, y, '600 13px "Segoe UI",sans-serif', C.warn);
        y += 26;
      }

      heading('แนวโน้ม', y); y += 22;
      label(tr.text, pad, y, '600 13px "Segoe UI",sans-serif',
        tr.dir === 'up' ? C.ok : (tr.dir === 'down' ? C.bad : C.textMuted));
      y += 26;

      heading(isFy ? 'ยอดเคสรายเดือน (ครบ / ไม่ครบ)' : 'ยอดเคสรายวัน (ครบ / ไม่ครบ)', y); y += 18;
      var maxT = 0;
      chartData.forEach(function (d) { if ((d.total || 0) > maxT) maxT = d.total; });
      if (!maxT) maxT = 1;
      if (!chartData.length) {
        label('ไม่มีข้อมูล', pad, y + 40, '400 13px "Segoe UI",sans-serif', C.textMuted);
        y += chartH + 26;
      } else {
        var n = chartData.length;
        var gap = 5;
        var bw = Math.max(6, Math.min(34, (W - pad * 2 - gap * n) / n));
        var top = y, baseY = y + chartH - 18;
        chartData.forEach(function (d, i) {
          var total = d.total || 0, miss = d.missing || 0;
          var h = total / maxT * (chartH - 22);
          var mh = miss / maxT * (chartH - 22);
          var x = pad + i * (bw + gap);
          ctx.fillStyle = C.track; ctx.fillRect(x, top, bw, chartH - 18);
          ctx.fillStyle = C.ok; ctx.fillRect(x, baseY - h, bw, h);
          if (mh > 0) { ctx.fillStyle = C.warn; ctx.fillRect(x, baseY - h, bw, mh); }
          ctx.fillStyle = C.textMuted; ctx.font = '400 10px "Segoe UI",sans-serif'; ctx.textAlign = 'center';
          ctx.fillText(String(d.label != null ? d.label : d.day), x + bw / 2, baseY + 13);
          ctx.textAlign = 'left';
        });
        label('■ ครบ  ■ ไม่ครบ', W - pad, top - 2, '400 11px "Segoe UI",sans-serif', C.textMuted, 'right');
        y += chartH + 26;
      }

      heading('แยกตามแผนก', y); y += 16;
      var maxDept = 0;
      depts.forEach(function (d) { if ((d.total || 0) > maxDept) maxDept = d.total; });
      if (!maxDept) maxDept = 1;
      if (!depts.length) {
        label(ct.empty ? 'ยังไม่มีข้อมูลสิ้นสุดวัน' : 'ไม่มีข้อมูล', pad, y + 16, '400 13px "Segoe UI",sans-serif', C.textMuted);
        y += 30;
      } else {
        depts.forEach(function (d) {
          y += 20;
          label(d.dept, pad, y, '600 13px "Segoe UI",sans-serif', C.text);
          var tx = pad + 110, tw = W - pad * 2 - 110 - 210;
          ctx.fillStyle = C.track; ctx.fillRect(tx, y - 10, tw, 10);
          ctx.fillStyle = C.accent; ctx.globalAlpha = 0.85;
          ctx.fillRect(tx, y - 10, tw * ((d.total || 0) / maxDept), 10);
          ctx.globalAlpha = 1;
          var mp = d.total ? Math.round((d.missing / d.total) * 1000) / 10 : 0;
          label(d.total + ' เคส · ' + d.missing + ' ไม่ครบ (' + mp + '%)', W - pad, y, '400 12px "Segoe UI",sans-serif', C.textMuted, 'right');
        });
      }
      y += 20;

      heading('ช่องที่ขาดบ่อยสุด', y); y += 16;
      var maxCol = 0;
      cols.forEach(function (c) { if ((c.count || 0) > maxCol) maxCol = c.count; });
      if (!maxCol) maxCol = 1;
      if (!cols.length) {
        label(ct.empty ? 'ยังไม่มีข้อมูลสิ้นสุดวัน' : 'ครบ ✅ ไม่มีช่องขาด', pad, y + 16, '600 13px "Segoe UI",sans-serif', ct.empty ? C.textMuted : C.ok);
        y += 30;
      } else {
        cols.forEach(function (c) {
          y += 18;
          label(c.col, pad, y, '400 13px "Segoe UI",sans-serif', C.text);
          var tx = pad + 160, tw = W - pad * 2 - 160 - 40;
          ctx.fillStyle = C.track; ctx.fillRect(tx, y - 10, tw, 10);
          ctx.fillStyle = C.warn; ctx.fillRect(tx, y - 10, tw * ((c.count || 0) / maxCol), 10);
          label(String(c.count), W - pad, y, '600 12px "Segoe UI",sans-serif', C.textMuted, 'right');
        });
      }
      y += 22;

      heading('ความคืบหน้าการแก้ไข', y); y += 20;
      var pctLine = pr.prog.ever
        ? (pct1((pr.prog.resolved / pr.prog.ever) * 100) + '% แก้ไขแล้ว (' + pr.prog.resolved + '/' + pr.prog.ever + ' เคสที่เคยถูกแจ้ง)')
        : '— ยังไม่มีเคสที่เคยถูกแจ้งในขอบเขตนี้';
      label('ทั้งหมด ' + (pr.prog.total || 0) + ' · รอแก้ไข ' + (pr.prog.pending || 0) + ' · แก้ไขแล้ว ' + (pr.prog.resolved || 0) + ' · ' + pctLine,
        pad, y, '400 12px "Segoe UI",sans-serif', C.textMuted);
      y += 22;

      heading('เคสที่แสดงตามตัวกรอง (' + cases.length + ' เคส)', y); y += 20;
      if (!cases.length) {
        label(ct.empty ? 'ยังไม่มีข้อมูลสิ้นสุดวัน' : 'ครบ ✅ ไม่มีเคสข้อมูลไม่ครบตามตัวกรอง',
          pad, y + 10, '600 13px "Segoe UI",sans-serif', ct.empty ? C.textMuted : C.ok);
        y += 30;
      } else {
        var cx = { date: pad, hn: pad + 82, name: pad + 152, dept: pad + 340, missing: pad + 452, days: W - pad - 56 };
        label('วันที่', cx.date, y, '600 11px "Segoe UI",sans-serif', C.textMuted);
        label('HN', cx.hn, y, '600 11px "Segoe UI",sans-serif', C.textMuted);
        label('ชื่อ', cx.name, y, '600 11px "Segoe UI",sans-serif', C.textMuted);
        label('แผนก', cx.dept, y, '600 11px "Segoe UI",sans-serif', C.textMuted);
        label('ข้อมูลที่ขาด', cx.missing, y, '600 11px "Segoe UI",sans-serif', C.textMuted);
        label('รอแก้ไข', cx.days, y, '600 11px "Segoe UI",sans-serif', C.textMuted, 'right');
        y += 6;
        ctx.strokeStyle = C.border;
        ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(W - pad, y); ctx.stroke();
        y += 18;
        cases.forEach(function (c) {
          ctx.fillStyle = C.panel;
          ctx.fillRect(pad - 6, y - 14, W - pad * 2 + 12, rowH - 6);
          label(c.date, cx.date, y, '400 12px "Segoe UI",sans-serif', C.text);
          label(c.hn, cx.hn, y, '400 12px "Segoe UI",sans-serif', C.text);
          label(c.name.slice(0, 20), cx.name, y, '600 12px "Segoe UI",sans-serif', C.text);
          label(c.dept, cx.dept, y, '400 12px "Segoe UI",sans-serif', C.text);
          var mx = cx.missing;
          c.missing.forEach(function (m) {
            var w = ctx.measureText(m).width + 14;
            ctx.fillStyle = C.warnBg; ctx.fillRect(mx, y - 12, w, 16);
            ctx.fillStyle = C.warn; ctx.font = '600 10px "Segoe UI",sans-serif';
            ctx.fillText(m, mx + 6, y);
            mx += w + 4;
          });
          label(c.days || '-', cx.days, y, '400 12px "Segoe UI",sans-serif', C.textMuted, 'right');
          label(c.op.slice(0, 58) + (c.circ ? ' · Circ: ' + c.circ.slice(0, 34) : ''), cx.date, y + 17, '400 11px "Segoe UI",sans-serif', C.textMuted);
          y += rowH;
        });
      }

      y += 10;
      label('ระบบติดตามข้อมูลทะเบียนผ่าตัด · ' + META.as_of, W / 2, y, '400 11px "Segoe UI",sans-serif', C.textMuted, 'center');

      var fname = ('dashboard-' + scope + '-' + META.as_of).replace(/[^A-Za-z0-9\u0E00-\u0E7F._-]+/g, '-');
      canvas.toBlob(function (blob) {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = fname + '.png';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
      });
    }

    $('reportBtn').addEventListener('click', exportPng);

    // ---- boot: the engine owns selection, URL sync and table filtering --
    AuditUI.init(DATA, { onSelection: render, tableBody: 'allCasesTable' });
  })();
  </script>
</body>
</html>
"""


def build_dashboard(data: dict) -> str:
    gen_time = str(data.get("generated_at") or "")
    as_of = str(data.get("as_of") or "")
    rows = data.get("rows", 0)
    title = data.get("title") or "ทะเบียนผ่าตัด — Audit"
    data_json = json.dumps(dataset_for_embedding(data), ensure_ascii=False).replace("</", "<\\/")

    out = TEMPLATE
    out = out.replace("__TITLE__", esc(title + " — Dashboard"))
    out = out.replace("__DATA_JSON__", data_json)
    out = out.replace("__CASE_ROWS__", render_case_rows(data.get("all_cases", [])))
    out = out.replace("__GEN_TIME__", esc(gen_time))
    out = out.replace("__AS_OF__", esc(as_of))
    out = out.replace("__ROWS__", esc(rows))
    out = out.replace("__UI_CSS_VER__", asset_version("audit_ui.css", gen_time or "1"))
    out = out.replace("__UI_JS_VER__", asset_version("audit_ui.js", gen_time or "1"))
    return out


def main() -> None:
    data = load_data()
    OUT_PATH.write_text(build_dashboard(data), encoding="utf-8")
    print("DONE", OUT_PATH)


if __name__ == "__main__":
    main()
