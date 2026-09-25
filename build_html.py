#!/usr/bin/env python3
"""Generate a self-contained index.html Gist-style report from audit_data.json."""
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
        rows.append(
            f'''<tr>
        <td data-label="วันที่">{esc(case.get("date", ""))}</td>
        <td data-label="HN">{esc(case.get("hn", ""))}</td>
        <td data-label="ชื่อ">{esc(case.get("name", ""))}</td>
        <td data-label="แผนก">{esc(case.get("dept", ""))}</td>
        <td data-label="การผ่าตัด">{esc(case.get("op", ""))}</td>
        <td data-label="Circulating">{esc(case.get("circ", ""))}</td>
        <td data-label="ข้อมูลที่ขาด">{missing_html}</td>
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
          </tr>
        </thead>
        <tbody>
          {"".join(rows)}
        </tbody>
      </table>
    </div>'''


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
    month = data.get("month", {}) or {}
    month_label = month.get("label", "")
    month_total = month.get("total", 0)
    gen_time = datetime.datetime.now().strftime("%H:%M")
    blank_cols = data.get("blank_cols", {}) or {}

    month_cases = month.get("cases", []) or []
    month_table_html = render_month_table(month_cases)
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

  .gist-box {{
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 20px;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(15, 118, 110, 0.06);
  }}

  .gist-box-body {{
    padding: 16px;
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
    <div class="gist-box">
      <div class="gist-box-body">
        <p class="section-title">รายงานข้อมูลไม่ครบถ้วน — {esc(month_label)} เวลา: {esc(gen_time)}</p>
        <p class="section-sub">total: {esc(month_total)}</p>
        <div id="month-view-table">{month_table_html}</div>
      </div>
    </div>

    <div class="gist-box">
      <div class="gist-box-body">
        <p class="section-title">ช่องที่ว่าง</p>
        {blank_cols_html}
      </div>
    </div>

    <footer>อัปเดตอัตโนมัติ 07:52 · ระบบ guard ทะเบียนผ่าตัด</footer>
  </div>
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
