#!/usr/bin/env python3
"""Generate dashboard.html — insights page (completeness %, dept breakdown,
top missing columns, month-over-month trend) built from audit_data.json.

Same visual language as build_html.py (dark/light theme, sharp corners).
"""
import json
import html
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "audit_data.json"
OUT_PATH = BASE_DIR / "dashboard.html"


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def render_dept_bars(dept_breakdown: list) -> str:
    if not dept_breakdown:
        return '<p class="all-clear">ไม่มีข้อมูล</p>'
    max_total = max((d.get("total", 0) for d in dept_breakdown), default=0) or 1
    rows = []
    for d in dept_breakdown:
        dept = d.get("dept", "")
        total = d.get("total", 0)
        missing = d.get("missing", 0)
        pct = round((total / max_total) * 100, 1) if total else 0
        miss_pct = round((missing / total) * 100, 1) if total else 0
        rows.append(f'''<div class="dept-row">
        <div class="dept-name">{esc(dept)}</div>
        <div class="dept-track">
          <div class="dept-fill" style="width:{pct}%"></div>
        </div>
        <div class="dept-nums">{esc(total)} เคส · <span class="{"dept-warn" if missing else "dept-ok"}">{esc(missing)} ไม่ครบ ({esc(miss_pct)}%)</span></div>
      </div>''')
    return "".join(rows)


def render_top_missing(top_missing_cols: list) -> str:
    if not top_missing_cols:
        return '<p class="all-clear">ครบ ✅ ไม่มีช่องขาด</p>'
    max_count = max((c.get("count", 0) for c in top_missing_cols), default=0) or 1
    rows = []
    for c in top_missing_cols:
        col = c.get("col", "")
        count = c.get("count", 0)
        pct = round((count / max_count) * 100, 1) if count else 0
        rows.append(f'''<div class="col-row">
        <div class="col-name">{esc(col)}</div>
        <div class="col-track">
          <div class="col-fill" style="width:{pct}%"></div>
        </div>
        <div class="col-count">{esc(count)}</div>
      </div>''')
    return "".join(rows)


def render_trend(insights: dict) -> str:
    prev = insights.get("prev_completeness_pct")
    delta = insights.get("trend_delta")
    if prev is None or delta is None:
        return '<p class="page-sub">ไม่มีข้อมูลเดือนก่อนเปรียบเทียบ</p>'
    if delta > 0:
        arrow, cls, word = "▲", "trend-up", "ดีขึ้น"
    elif delta < 0:
        arrow, cls, word = "▼", "trend-down", "แย่ลง"
    else:
        arrow, cls, word = "■", "trend-flat", "เท่าเดิม"
    return f'''<p class="trend-line {cls}">{arrow} {esc(abs(delta))} จุด ({word}) — เดือนก่อนหน้า {esc(prev)}%</p>'''


def build_dashboard(data: dict) -> str:
    repo = data.get("repo", "")
    month = data.get("month", {}) or {}
    month_label = month.get("label", "")
    insights = data.get("insights", {}) or {}
    gen_time = datetime.datetime.now().strftime("%H:%M")

    completeness_pct = insights.get("completeness_pct", 100.0)
    finished_total = insights.get("finished_total", 0)
    missing_total = insights.get("missing_total", 0)
    dept_html = render_dept_bars(insights.get("dept_breakdown", []))
    top_missing_html = render_top_missing(insights.get("top_missing_cols", []))
    trend_html = render_trend(insights)

    pct_class = "pct-good" if completeness_pct >= 97 else ("pct-warn" if completeness_pct >= 90 else "pct-bad")

    trend_text = "ไม่มีข้อมูลเดือนก่อนเปรียบเทียบ"
    trend_delta_val = insights.get("trend_delta")
    prev_pct = insights.get("prev_completeness_pct")
    if trend_delta_val is not None and prev_pct is not None:
        word = "ดีขึ้น" if trend_delta_val > 0 else ("แย่ลง" if trend_delta_val < 0 else "เท่าเดิม")
        trend_text = f"{abs(trend_delta_val)} จุด ({word}) — เดือนก่อนหน้า {prev_pct}%"

    all_cases = data.get("all_cases", []) or []
    month_options = data.get("month_options", []) or []
    current_month_key = month_options[0][0] if month_options else "all"
    current_month_cases = [c for c in all_cases if c.get("month_key") == current_month_key]

    report_data = {
        "month_label": month_label,
        "gen_time": gen_time,
        "as_of": data.get("as_of", ""),
        "completeness_pct": completeness_pct,
        "finished_total": finished_total,
        "missing_total": missing_total,
        "trend_delta": trend_delta_val if trend_delta_val is not None else 0,
        "trend_text": trend_text,
        "dept_breakdown": insights.get("dept_breakdown", []),
        "top_missing_cols": insights.get("top_missing_cols", []),
        "cases": current_month_cases,
    }
    report_data_json = json.dumps(report_data, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="dark">
<title>{esc(repo)} — Dashboard</title>
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
    --bad: #f87171;
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
    --bad: #b91c1c;
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

  .mono {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; }}

  .wrap {{ max-width: 900px; margin: 0 auto; }}

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
    padding: 5px 10px;
    font-size: 0.82rem;
    color: var(--text);
  }}

  .ws-dot {{
    width: 18px;
    height: 18px;
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

  .theme-toggle:hover {{ background: var(--bg-muted); }}

  .tabs {{ display: flex; gap: 4px; flex-wrap: wrap; margin-left: 4px; }}

  .tab {{
    padding: 8px 12px 9px;
    font-size: 0.88rem;
    color: var(--text-muted);
    white-space: nowrap;
    text-decoration: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
  }}

  .tab.active {{ color: var(--accent); border-bottom-color: var(--accent); }}

  .page-head {{ padding: 22px 2px 14px; }}

  .page-title {{
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 0 0 6px;
    color: var(--text);
  }}

  .page-sub {{ color: var(--text-muted); font-size: 0.88rem; margin: 0; }}

  .all-clear {{ color: var(--ok); font-weight: 600; margin: 0; }}

  .stat-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 0 0 16px; }}

  .stat {{
    flex: 1 1 140px;
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    padding: 12px 14px;
    text-align: center;
  }}

  .stat-label {{ font-size: 0.75rem; color: var(--text-muted); margin: 0 0 6px; }}
  .stat-value {{ font-size: 1.35rem; font-weight: 700; color: var(--text); margin: 0; line-height: 1.2; text-align: center; }}
  .pct-good {{ color: var(--ok); }}
  .pct-warn {{ color: var(--warn); }}
  .pct-bad {{ color: var(--bad); }}

  .panel {{
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    margin-bottom: 18px;
    overflow: hidden;
  }}

  .panel-body {{ padding: 16px 14px; }}

  .section-title {{ font-size: 1.05rem; font-weight: 650; color: var(--text); margin: 0 0 4px; }}
  .section-sub {{ color: var(--text-muted); font-size: 0.85rem; margin: 0 0 14px; }}

  .trend-line {{ font-size: 0.95rem; font-weight: 600; margin: 0; }}
  .trend-up {{ color: var(--ok); }}
  .trend-down {{ color: var(--bad); }}
  .trend-flat {{ color: var(--text-muted); }}

  .dept-row {{
    display: grid;
    grid-template-columns: 110px 1fr 170px;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border-soft);
    font-size: 0.85rem;
  }}

  .dept-row:last-child {{ border-bottom: none; }}

  .dept-name {{ color: var(--text); font-weight: 600; }}

  .dept-track {{
    background: var(--bg-muted);
    height: 10px;
    position: relative;
  }}

  .dept-fill {{ background: var(--accent); height: 100%; opacity: 0.85; }}

  .dept-nums {{ color: var(--text-muted); font-size: 0.78rem; text-align: right; }}
  .dept-warn {{ color: var(--warn); font-weight: 600; }}
  .dept-ok {{ color: var(--ok); font-weight: 600; }}

  .col-row {{
    display: grid;
    grid-template-columns: 160px 1fr 32px;
    align-items: center;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid var(--border-soft);
    font-size: 0.85rem;
  }}

  .col-row:last-child {{ border-bottom: none; }}
  .col-name {{ color: var(--text); }}

  .col-track {{ background: var(--bg-muted); height: 10px; }}
  .col-fill {{ background: var(--warn); height: 100%; }}
  .col-count {{ color: var(--text-muted); text-align: right; font-weight: 600; }}

  footer {{ text-align: center; color: var(--text-dim); font-size: 0.78rem; margin-top: 28px; }}

  @media (max-width: 640px) {{
    body {{ padding: 0 10px 56px; }}
    .page-title {{ font-size: 1.2rem; }}
    .stat {{ flex: 1 1 90px; }}
    .stat-value {{ font-size: 1.15rem; }}
    .dept-row {{ grid-template-columns: 84px 1fr; grid-template-areas: "name nums" "track track"; row-gap: 4px; }}
    .dept-name {{ grid-area: name; }}
    .dept-nums {{ grid-area: nums; }}
    .dept-track {{ grid-area: track; }}
    .col-row {{ grid-template-columns: 110px 1fr 28px; }}
  }}
</style>
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
      <p class="page-sub">{esc(month_label)} · อัปเดตล่าสุด {esc(gen_time)}</p>
    </div>

    <div class="stat-row">
      <div class="stat">
        <p class="stat-label">% ความครบถ้วน</p>
        <p class="stat-value {pct_class}">{esc(completeness_pct)}%</p>
      </div>
      <div class="stat">
        <p class="stat-label">เคสทั้งหมด</p>
        <p class="stat-value">{esc(finished_total)}</p>
      </div>
      <div class="stat">
        <p class="stat-label">เคสข้อมูลไม่ครบ</p>
        <p class="stat-value">{esc(missing_total)}</p>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <p class="section-title">แนวโน้มเทียบเดือนก่อน</p>
        {trend_html}
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <p class="section-title">แยกตามแผนก</p>
        {dept_html}
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <p class="section-title">ช่องที่ขาดบ่อยสุด</p>
        <p class="section-sub">เรียงจากมากไปน้อย เดือนนี้</p>
        {top_missing_html}
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
    (function() {{
      var reportData = {report_data_json};
      document.getElementById('reportBtn').addEventListener('click', function() {{
        var theme = document.documentElement.getAttribute('data-theme') || 'dark';
        var isLight = theme === 'light';
        var bg = isLight ? '#f5f5f6' : '#0b0b0c';
        var panelBg = isLight ? '#ffffff' : '#151517';
        var border = isLight ? '#d4d4d8' : '#27272b';
        var text = isLight ? '#18181b' : '#ededed';
        var textMuted = isLight ? '#52525b' : '#8b8b90';
        var ok = isLight ? '#15803d' : '#4ade80';
        var warn = isLight ? '#b45309' : '#fbbf24';
        var bad = isLight ? '#b91c1c' : '#f87171';
        var accent = isLight ? '#000000' : '#ffffff';

        var W = 900, pad = 32;
        var deptRows = reportData.dept_breakdown.length;
        var colRows = reportData.top_missing_cols.length;
        var caseRows = reportData.cases.length;
        var caseRowH = 44;
        var H = 300 + deptRows * 36 + colRows * 30 + 120 + 50 + Math.max(caseRows, 1) * caseRowH;
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
        ctx.font = '700 24px -apple-system, "Segoe UI", sans-serif';
        ctx.fillText('Dashboard สรุปภาพรวม', pad, y + 24);
        y += 40;
        ctx.fillStyle = textMuted;
        ctx.font = '400 13px -apple-system, "Segoe UI", sans-serif';
        ctx.fillText(reportData.month_label + ' · ส่งออก ' + reportData.gen_time, pad, y);
        y += 30;

        function statCard(x, w, label, value, color) {{
          ctx.strokeStyle = border;
          ctx.fillStyle = panelBg;
          ctx.fillRect(x, y, w, 70);
          ctx.strokeRect(x, y, w, 70);
          ctx.fillStyle = textMuted;
          ctx.font = '400 12px -apple-system, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(label, x + w / 2, y + 24);
          ctx.fillStyle = color || text;
          ctx.font = '700 22px -apple-system, sans-serif';
          ctx.fillText(String(value), x + w / 2, y + 52);
          ctx.textAlign = 'left';
        }}
        var statW = (W - pad * 2 - 20) / 3;
        var pctColor = reportData.completeness_pct >= 97 ? ok : (reportData.completeness_pct >= 90 ? warn : bad);
        statCard(pad, statW, '% ความครบถ้วน', reportData.completeness_pct + '%', pctColor);
        statCard(pad + statW + 10, statW, 'เคสทั้งหมด', reportData.finished_total, text);
        statCard(pad + (statW + 10) * 2, statW, 'เคสข้อมูลไม่ครบ', reportData.missing_total, text);
        y += 100;

        ctx.fillStyle = text;
        ctx.font = '650 15px -apple-system, sans-serif';
        ctx.fillText('แนวโน้มเทียบเดือนก่อน', pad, y);
        y += 22;
        ctx.font = '600 14px -apple-system, sans-serif';
        ctx.fillStyle = reportData.trend_delta > 0 ? ok : (reportData.trend_delta < 0 ? bad : textMuted);
        ctx.fillText(reportData.trend_text, pad, y);
        y += 34;

        ctx.fillStyle = text;
        ctx.font = '650 15px -apple-system, sans-serif';
        ctx.fillText('แยกตามแผนก', pad, y);
        y += 16;
        var maxDeptTotal = 0;
        reportData.dept_breakdown.forEach(function(d) {{ if (d.total > maxDeptTotal) maxDeptTotal = d.total; }});
        if (!maxDeptTotal) maxDeptTotal = 1;
        reportData.dept_breakdown.forEach(function(d) {{
          y += 24;
          ctx.fillStyle = text;
          ctx.font = '600 13px -apple-system, sans-serif';
          ctx.fillText(d.dept, pad, y);
          var trackX = pad + 110, trackW = W - pad * 2 - 110 - 170;
          ctx.fillStyle = isLight ? '#e4e4e7' : '#1f1f23';
          ctx.fillRect(trackX, y - 10, trackW, 10);
          ctx.fillStyle = accent;
          ctx.globalAlpha = 0.85;
          ctx.fillRect(trackX, y - 10, trackW * (d.total / maxDeptTotal), 10);
          ctx.globalAlpha = 1;
          ctx.font = '400 12px -apple-system, sans-serif';
          ctx.fillStyle = textMuted;
          ctx.textAlign = 'right';
          var missPct = d.total ? Math.round((d.missing / d.total) * 1000) / 10 : 0;
          ctx.fillText(d.total + ' เคส · ' + d.missing + ' ไม่ครบ (' + missPct + '%)', W - pad, y);
          ctx.textAlign = 'left';
        }});
        y += 30;

        ctx.fillStyle = text;
        ctx.font = '650 15px -apple-system, sans-serif';
        ctx.fillText('ช่องที่ขาดบ่อยสุด', pad, y);
        y += 16;
        var maxColCount = 0;
        reportData.top_missing_cols.forEach(function(c) {{ if (c.count > maxColCount) maxColCount = c.count; }});
        if (!maxColCount) maxColCount = 1;
        if (reportData.top_missing_cols.length === 0) {{
          y += 20;
          ctx.fillStyle = ok;
          ctx.font = '600 13px -apple-system, sans-serif';
          ctx.fillText('ครบ ✅ ไม่มีช่องขาด', pad, y);
        }} else {{
          reportData.top_missing_cols.forEach(function(c) {{
            y += 22;
            ctx.fillStyle = text;
            ctx.font = '400 13px -apple-system, sans-serif';
            ctx.fillText(c.col, pad, y);
            var trackX = pad + 160, trackW = W - pad * 2 - 160 - 40;
            ctx.fillStyle = isLight ? '#e4e4e7' : '#1f1f23';
            ctx.fillRect(trackX, y - 10, trackW, 10);
            ctx.fillStyle = warn;
            ctx.fillRect(trackX, y - 10, trackW * (c.count / maxColCount), 10);
            ctx.fillStyle = textMuted;
            ctx.font = '600 12px -apple-system, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(String(c.count), W - pad, y);
            ctx.textAlign = 'left';
          }});
        }}
        y += 34;
        ctx.fillStyle = text;
        ctx.font = '650 15px -apple-system, sans-serif';
        ctx.fillText('รายการเคสข้อมูลไม่ครบ (' + reportData.month_label + ')', pad, y);
        y += 20;
        if (reportData.cases.length === 0) {{
          ctx.fillStyle = ok;
          ctx.font = '600 13px -apple-system, sans-serif';
          ctx.fillText('ครบ ✅ ไม่มีเคสข้อมูลไม่ครบ', pad, y);
          y += 20;
        }} else {{
          var caseColX = {{ date: pad, hn: pad + 78, name: pad + 148, dept: pad + 330, missing: pad + 420 }};
          ctx.fillStyle = textMuted;
          ctx.font = '600 10px -apple-system, sans-serif';
          ctx.fillText('วันที่', caseColX.date, y);
          ctx.fillText('HN', caseColX.hn, y);
          ctx.fillText('ชื่อ', caseColX.name, y);
          ctx.fillText('แผนก', caseColX.dept, y);
          ctx.fillText('ข้อมูลที่ขาด', caseColX.missing, y);
          y += 6;
          ctx.strokeStyle = border;
          ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(W - pad, y); ctx.stroke();
          y += 18;
          reportData.cases.forEach(function(c) {{
            var rowTop = y - 12;
            ctx.fillStyle = panelBg;
            ctx.fillRect(pad - 8, rowTop, W - pad * 2 + 16, caseRowH - 6);
            ctx.fillStyle = text;
            ctx.font = '400 11px -apple-system, sans-serif';
            ctx.fillText(c.date || '', caseColX.date, y);
            ctx.fillText(c.hn || '', caseColX.hn, y);
            ctx.font = '600 11px -apple-system, sans-serif';
            ctx.fillText((c.name || '').slice(0, 20), caseColX.name, y);
            ctx.font = '400 11px -apple-system, sans-serif';
            ctx.fillText(c.dept || '', caseColX.dept, y);
            var mx = caseColX.missing;
            (c.missing || []).forEach(function(m) {{
              var w = ctx.measureText(m).width + 12;
              ctx.fillStyle = isLight ? 'rgba(180,83,9,0.12)' : 'rgba(251,191,36,0.13)';
              ctx.fillRect(mx, y - 10, w, 14);
              ctx.fillStyle = warn;
              ctx.font = '600 9px -apple-system, sans-serif';
              ctx.fillText(m, mx + 5, y);
              mx += w + 4;
            }});
            ctx.fillStyle = textMuted;
            ctx.font = '400 10px -apple-system, sans-serif';
            var opLine = (c.op || '') + (c.circ ? ' · Circ: ' + c.circ : '');
            ctx.fillText(opLine.slice(0, 90), caseColX.date, y + 16);
            y += caseRowH;
          }});
        }}
        y += 20;
        ctx.fillStyle = textMuted;
        ctx.font = '400 11px -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('ระบบติดตามข้อมูลทะเบียนผ่าตัด', W / 2, y);
        ctx.textAlign = 'left';

        canvas.toBlob(function(blob) {{
          var a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = 'dashboard-report-' + reportData.as_of.replace(/\\//g, '-') + '.png';
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
    output = build_dashboard(data)
    OUT_PATH.write_text(output, encoding="utf-8")
    print("DONE")


if __name__ == "__main__":
    main()
