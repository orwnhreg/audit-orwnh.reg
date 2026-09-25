#!/usr/bin/env python3
"""Generate a self-contained index.html Gist-style report from audit_data.json."""
import json
import html
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "audit_data.json"
OUT_PATH = BASE_DIR / "index.html"


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def render_summary_cards(data: dict) -> str:
    col_a = data.get("colA", {}) or {}
    team = data.get("team", {}) or {}
    cards = [
        ("แถวทั้งหมด", data.get("rows", 0), ""),
        ("คอลัมน์ A ซ้ำ", col_a.get("dup", 0), "ซ้ำ"),
        ("คอลัมน์ A หาย", col_a.get("missing", 0), "หาย"),
        ("คอลัมน์ A เบี่ยง", col_a.get("offset", 0), "เบี่ยง"),
        ("ทีมซ้ำในชุด", team.get("dup_in_set", 0), "รวม"),
        ("ทีมซ้ำ (ล่าสุด)", team.get("dup_in_set_recent", 0), "recent"),
    ]
    items = []
    for label, value, tag in cards:
        tag_html = f'<span class="stat-tag">{esc(tag)}</span>' if tag else ""
        items.append(
            f'''<div class="stat-box">
        <div class="stat-value">{esc(value)}</div>
        <div class="stat-label">{esc(label)} {tag_html}</div>
      </div>'''
        )
    return "\n".join(items)


def render_month_table(cases: list) -> str:
    if not cases:
        return '<p class="all-clear">ครบ ✅</p>'

    rows = []
    for case in cases:
        missing = case.get("missing", []) or []
        missing_html = "".join(
            f'<span class="chip chip-warn">{esc(m)}</span>' for m in missing
        )
        rows.append(
            f'''<tr>
        <td data-label="วันที่">{esc(case.get("date", ""))}</td>
        <td data-label="HN">{esc(case.get("hn", ""))}</td>
        <td data-label="ชื่อ">{esc(case.get("name", ""))}</td>
        <td data-label="แผนก">{esc(case.get("dept", ""))}</td>
        <td data-label="การผ่าตัด">{esc(case.get("op", ""))}</td>
        <td data-label="Circulating">{esc(case.get("circ", ""))}</td>
        <td data-label="ขาด">{missing_html}</td>
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
            <th>ขาด</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows)}
        </tbody>
      </table>
    </div>'''


def render_month_lines(cases: list) -> str:
    if not cases:
        return '<p class="all-clear">ครบ ✅</p>'

    lines = []
    for case in cases:
        missing = case.get("missing", []) or []
        missing_text = ", ".join(str(m) for m in missing) if missing else "-"
        segments = [
            esc(case.get("date", "")),
            f'HN{esc(case.get("hn", ""))}',
            esc(case.get("name", "")),
            esc(case.get("dept", "")),
            esc(case.get("op", "")),
            f'Circ {esc(case.get("circ", ""))}',
            f'ขาด {esc(missing_text)}',
        ]
        line = ' <span class="dot">·</span> '.join(segments)
        lines.append(f'<div class="case-line">{line}</div>')

    return f'<div class="lines-wrap">{"".join(lines)}</div>'


def render_blank_cols(blank_cols: dict) -> str:
    if not blank_cols:
        return '<p class="all-clear">✅</p>'
    chips = "".join(
        f'<span class="chip chip-blank">{esc(name)}: {esc(count)}</span>'
        for name, count in blank_cols.items()
    )
    return f'<div class="chip-row">{chips}</div>'


def build_html(data: dict) -> str:
    repo = data.get("repo", "")
    as_of = data.get("as_of", "")
    month = data.get("month", {}) or {}
    month_label = month.get("label", "")
    month_total = month.get("total", 0)
    blank_cols = data.get("blank_cols", {}) or {}

    month_cases = month.get("cases", []) or []
    summary_html = render_summary_cards(data)
    month_table_html = render_month_table(month_cases)
    month_lines_html = render_month_lines(month_cases)
    blank_cols_html = render_blank_cols(blank_cols)

    return f'''<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(repo)} — Audit</title>
<style>
  :root {{
    --teal: #0f766e;
    --teal-bright: #14b8a6;
    --green: #16a34a;
    --bg: #fbfdfc;
    --bg-panel: #ffffff;
    --bg-muted: #f2f7f5;
    --border: #d9e6e1;
    --text: #1f2d2a;
    --text-muted: #5c6f6a;
  }}

  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    padding: 24px 12px 60px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.5;
  }}

  code, .mono, .data-table td, .data-table th {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  }}

  .wrap {{
    max-width: 900px;
    margin: 0 auto;
  }}

  .gist-header {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    margin-bottom: 18px;
  }}

  .gist-title {{
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--teal);
    margin: 0;
    word-break: break-word;
  }}

  .badge {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--green);
    color: #fff;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 999px;
  }}

  .as-of {{
    width: 100%;
    color: var(--text-muted);
    font-size: 0.88rem;
  }}

  .gist-box {{
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 20px;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(15, 118, 110, 0.06);
  }}

  .gist-box-header {{
    background: var(--bg-muted);
    border-bottom: 1px solid var(--border);
    padding: 10px 16px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}

  .gist-caption {{
    font-size: 0.78rem;
    color: var(--text-muted);
  }}

  .gist-filename {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--teal);
  }}

  .gist-box-body {{
    padding: 16px;
  }}

  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }}

  @media (min-width: 560px) {{
    .stats-grid {{
      grid-template-columns: repeat(4, 1fr);
    }}
  }}

  .stat-box {{
    background: var(--bg-muted);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }}

  .stat-value {{
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--teal);
  }}

  .stat-label {{
    margin-top: 4px;
    font-size: 0.78rem;
    color: var(--text-muted);
  }}

  .stat-tag {{
    display: inline-block;
    background: var(--teal-bright);
    color: #fff;
    font-size: 0.66rem;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 999px;
    margin-left: 4px;
  }}

  .section-title {{
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--teal);
    margin: 0 0 4px;
  }}

  .section-sub {{
    color: var(--text-muted);
    font-size: 0.85rem;
    margin: 0 0 12px;
  }}

  .all-clear {{
    color: var(--green);
    font-weight: 600;
    font-size: 1rem;
  }}

  .view-toggle {{
    display: inline-flex;
    background: var(--bg-muted);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 3px;
    margin-bottom: 12px;
    gap: 2px;
  }}

  .view-btn {{
    border: none;
    background: transparent;
    color: var(--text-muted);
    font-size: 0.8rem;
    font-weight: 600;
    padding: 5px 14px;
    border-radius: 999px;
    cursor: pointer;
    font-family: inherit;
  }}

  .view-btn.active {{
    background: var(--teal);
    color: #fff;
  }}

  .view-btn:hover:not(.active) {{
    color: var(--teal);
  }}

  .lines-wrap {{
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}

  .case-line {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 0.82rem;
    padding: 8px 10px;
    background: var(--bg-muted);
    border: 1px solid var(--border);
    border-radius: 6px;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    line-height: 1.6;
  }}

  .case-line .dot {{
    color: var(--teal-bright);
    font-weight: 700;
    margin: 0 2px;
  }}

  .table-wrap {{
    overflow-x: auto;
  }}

  .data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }}

  .data-table th {{
    background: var(--bg-muted);
    color: var(--teal);
    text-align: left;
    padding: 8px 10px;
    border-bottom: 2px solid var(--border);
    white-space: nowrap;
  }}

  .data-table td {{
    padding: 8px 10px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
  }}

  .data-table tbody tr:hover {{
    background: var(--bg-muted);
  }}

  .chip {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    margin: 2px 4px 2px 0;
    white-space: nowrap;
  }}

  .chip-warn {{
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #fde68a;
  }}

  .chip-blank {{
    background: #e6f7f3;
    color: var(--teal);
    border: 1px solid var(--teal-bright);
  }}

  .chip-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}

  @media (max-width: 640px) {{
    .data-table thead {{
      display: none;
    }}
    .data-table, .data-table tbody, .data-table tr, .data-table td {{
      display: block;
      width: 100%;
    }}
    .data-table tr {{
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-bottom: 10px;
      padding: 6px 10px;
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
    }}
  }}

  footer {{
    text-align: center;
    color: var(--text-muted);
    font-size: 0.8rem;
    margin-top: 30px;
  }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="gist-header">
      <h1 class="gist-title">{esc(repo)}</h1>
      <span class="badge">🔎 Audit</span>
      <div class="as-of">as_of: {esc(as_of)}</div>
    </div>

    <div class="gist-box">
      <div class="gist-box-header">
        <span class="gist-caption">kttwatt / {esc(repo)}</span>
        <span class="gist-filename">summary.json</span>
      </div>
      <div class="gist-box-body">
        <div class="stats-grid">
          {summary_html}
        </div>
      </div>
    </div>

    <div class="gist-box">
      <div class="gist-box-header">
        <span class="gist-caption">kttwatt / {esc(repo)}</span>
        <span class="gist-filename">missing_data_this_month.csv</span>
      </div>
      <div class="gist-box-body">
        <p class="section-title">ข้อมูลไม่ครบ — เดือนนี้ ({esc(month_label)})</p>
        <p class="section-sub">total: {esc(month_total)}</p>
        <div class="view-toggle" role="tablist">
          <button type="button" class="view-btn active" data-view="table" onclick="setMonthView('table')">ตาราง</button>
          <button type="button" class="view-btn" data-view="lines" onclick="setMonthView('lines')">บรรทัด</button>
        </div>
        <div id="month-view-table">{month_table_html}</div>
        <div id="month-view-lines" style="display:none">{month_lines_html}</div>
      </div>
    </div>

    <div class="gist-box">
      <div class="gist-box-header">
        <span class="gist-caption">kttwatt / {esc(repo)}</span>
        <span class="gist-filename">blank_columns.txt</span>
      </div>
      <div class="gist-box-body">
        <p class="section-title">ช่องที่ว่าง</p>
        {blank_cols_html}
      </div>
    </div>

    <footer>อัปเดตอัตโนมัติ 07:52 · ระบบ guard ทะเบียนผ่าตัด</footer>
  </div>
<script>
  function setMonthView(view) {{
    var table = document.getElementById('month-view-table');
    var lines = document.getElementById('month-view-lines');
    var btns = document.querySelectorAll('.view-btn');
    table.style.display = (view === 'table') ? '' : 'none';
    lines.style.display = (view === 'lines') ? '' : 'none';
    btns.forEach(function (b) {{
      b.classList.toggle('active', b.getAttribute('data-view') === view);
    }});
  }}
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
