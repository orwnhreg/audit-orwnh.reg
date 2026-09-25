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


def render_month_table(cases: list) -> str:
    if not cases:
        return '<p class="all-clear">ครบ ✅</p>'

    rows = []
    for case in cases:
        missing = case.get("missing", []) or []
        missing_html = "".join(
            f'<span class="chip chip-warn">{esc(m)}</span>' for m in missing
        )
        days = case.get("days_pending")
        days_html = f'{esc(days)} วัน' if days is not None else "-"
        circ_names = [n.strip() for n in (case.get("circ", "") or "").split(",") if n.strip()]
        circ_html = "".join(f'<span class="circ-name">{esc(n)}</span>' for n in circ_names)
        rows.append(
            f'''<tr>
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
      <table class="data-table">
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
    </div>'''


def build_html(data: dict) -> str:
    repo = data.get("repo", "")
    month = data.get("month", {}) or {}
    month_label = month.get("label", "")
    month_total = len(month.get("cases", []))
    month_unfinished = month.get("unfinished", 0)
    unfinished_note = (f'<p class="section-sub warn-sub">เคสยังไม่ลงเวลาเสร็จ {month_unfinished} เคส — นับรวมตอนเช้า</p>'
                       if month_unfinished else "")
    gen_time = datetime.datetime.now().strftime("%H:%M")
    blank_cols = data.get("blank_cols", {}) or {}

    month_cases = month.get("cases", []) or []
    month_table_html = render_month_table(month_cases)

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
  }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <span class="ws-pill"><span class="ws-dot">▣</span> ทะเบียนผ่าตัด</span>
      <nav class="tabs">
        <a class="tab active" href="#cases">ข้อมูลไม่ครบ</a>
      </nav>
      <button class="theme-toggle" id="themeToggle" type="button" aria-label="สลับโหมดสี">🌙</button>
    </div>

    <div class="page-head">
      <h1 class="page-title">รายงานข้อมูลไม่ครบถ้วน</h1>
      <p class="page-sub">{esc(month_label)} · อัปเดตล่าสุด {esc(gen_time)}</p>
      {unfinished_note}
    </div>

    <div class="stat-row">
      <div class="stat">
        <p class="stat-label">จำนวนเคสที่ข้อมูลไม่ครบ</p>
        <p class="stat-value">{esc(month_total)}</p>
      </div>
    </div>

    <div class="panel" id="cases">
      <div class="panel-body">
        <div id="month-view-table">{month_table_html}</div>
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
    output = build_html(data)
    OUT_PATH.write_text(output, encoding="utf-8")
    print("DONE")


if __name__ == "__main__":
    main()
