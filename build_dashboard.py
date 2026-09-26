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
      <span class="ws-pill"><span class="ws-dot">▣</span> ทะเบียนผ่าตัด</span>
      <nav class="tabs">
        <a class="tab" href="index.html">ข้อมูลไม่ครบ</a>
        <a class="tab active" href="dashboard.html">Dashboard</a>
      </nav>
      <button class="theme-toggle" id="themeToggle" type="button" aria-label="สลับโหมดสี">🌙</button>
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

    <footer>อัปเดตอัตโนมัติทุกชั่วโมง · ระบบ guard ทะเบียนผ่าตัด</footer>
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
