#!/usr/bin/env python3
"""07:52 GSheet report must follow the same period rule as the website (no 'วันที่ 1–0')."""
import datetime as dt
import json
import sys
import unittest

sys.path.insert(0, "/home/kttwatt/.hermes/scripts")
import report_period as rp  # noqa: E402
import register_gsheet_report as rep  # noqa: E402


def row(date, dept="Surgery", g="ในเวลา", hn="1", name="ทดสอบ", op="Appendectomy", missing=False):
    r = [""] * 60
    r[2], r[4], r[6], r[13], r[15], r[21] = date, dept, g, name, hn, op
    r[5], r[14] = "ศัลยกรรมชาย", "40"
    r[9], r[10], r[11], r[12] = "09:00:00", "09:10:00", "10:00:00", "10:10:00"
    for j in (16, 17, 18, 19, 20, 22, 23, 24, 25, 38, 40):
        r[j] = "x"
    for j, who in zip((26, 27, 28, 29), ("นาง ก", "นาง ข", "นาง ค", "นาง ง")):
        r[j] = who
    if missing:
        r[16] = ""            # AN ว่าง + ตึกผู้ป่วยใน = ขาดจริง
    return r


class TestGsheetReportPeriod(unittest.TestCase):
    def test_october_1_is_empty_window(self):
        data = [row("30/09/2569", hn="2"), row("01/10/2569", hn="3")]
        rows, blanks, cases = rep.month_cases(data, today=dt.date(2026, 10, 1))
        self.assertEqual((rows, cases), (0, []))
        period = rp.period_for(dt.date(2026, 10, 1))
        head = (f"{period['month_label']} · ยังไม่มีข้อมูลสิ้นสุดวัน · จำนวน 0 เคส · อัปเดต 01/10/2026")
        self.assertNotIn("1–0", head)
        self.assertIn("ยังไม่มีข้อมูลสิ้นสุดวัน", head)
        self.assertEqual(period["fiscal_year"], 2570)

    def test_october_2_counts_only_october_1(self):
        data = [row("30/09/2569", hn="2", missing=True), row("01/10/2569", hn="3", missing=True),
                row("02/10/2569", hn="4", missing=True)]
        rows, _blanks, cases = rep.month_cases(data, today=dt.date(2026, 10, 2))
        self.assertEqual(rows, 1)
        self.assertEqual([c[1] for c in cases], ["3"])

    def test_september_30_still_counts_september(self):
        data = [row("29/09/2569", hn="5"), row("30/09/2569", hn="6")]
        rows, _blanks, _cases = rep.month_cases(data, today=dt.date(2026, 9, 30))
        self.assertEqual(rows, 1)   # 30/9 = วันนี้ -> ตัดออก

    def test_complete_row_is_not_flagged(self):
        data = [row("01/10/2569", hn="7")]
        _rows, _blanks, cases = rep.month_cases(data, today=dt.date(2026, 10, 2))
        self.assertEqual(cases, [])


if __name__ == "__main__":
    unittest.main()
