#!/usr/bin/env python3
"""Rollover / fiscal-year rules for the audit pipeline (run: python3 -m unittest discover -s tests -v)."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, "/home/kttwatt/.hermes/scripts")
import report_period as rp  # noqa: E402


class TestPeriod(unittest.TestCase):
    def test_september_30_2026(self):
        p = rp.period_for(dt.date(2026, 9, 30))
        self.assertEqual(p["month_key"], "2569-09")
        self.assertEqual(p["day_to"], 29)
        self.assertFalse(p["empty"])
        self.assertEqual(p["fiscal_year"], 2569)
        self.assertEqual(p["label"], "วันที่ 1/09/69 ถึง 29/09/69")
        self.assertEqual(p["prev_month_key"], "2569-08")

    def test_october_1_starts_fiscal_2570_and_is_empty(self):
        p = rp.period_for(dt.date(2026, 10, 1))
        self.assertEqual(p["month_key"], "2569-10")
        self.assertEqual(p["fiscal_year"], 2570)
        self.assertEqual(p["month_label"], "ต.ค. 2569")
        self.assertTrue(p["empty"])
        self.assertEqual(p["day_to"], 0)
        self.assertEqual(p["label"], "ต.ค. 2569 · ยังไม่มีข้อมูลสิ้นสุดวัน")
        self.assertEqual(p["prev_month_key"], "2569-09")
        self.assertEqual(p["prev_fiscal_year"], 2569)
        self.assertNotIn("0/10", p["label"])

    def test_october_2_has_one_day(self):
        p = rp.period_for(dt.date(2026, 10, 2))
        self.assertEqual(p["day_to"], 1)
        self.assertFalse(p["empty"])
        self.assertEqual(p["fiscal_year"], 2570)
        self.assertEqual(p["label"], "วันที่ 1/10/69 ถึง 1/10/69")

    def test_january_2027_stays_in_fiscal_2570(self):
        p = rp.period_for(dt.date(2027, 1, 1))
        self.assertEqual(p["month_key"], "2570-01")
        self.assertEqual(p["fiscal_year"], 2570)
        self.assertTrue(p["empty"])
        self.assertEqual(p["prev_month_key"], "2569-12")

    def test_october_2027_starts_fiscal_2571(self):
        p = rp.period_for(dt.date(2027, 10, 1))
        self.assertEqual(p["fiscal_year"], 2571)
        self.assertEqual(p["prev_fiscal_year"], 2570)

    def test_fiscal_months_order(self):
        months = rp.fiscal_months(2570)
        self.assertEqual(len(months), 12)
        self.assertEqual(months[0], "2569-10")
        self.assertEqual(months[2], "2569-12")
        self.assertEqual(months[3], "2570-01")
        self.assertEqual(months[-1], "2570-09")
        self.assertEqual(rp.fiscal_months(2569)[0], "2568-10")

    def test_fiscal_labels(self):
        self.assertEqual(rp.fiscal_label(2570), "ปีงบ 2570 (ต.ค. 2569 – ก.ย. 2570)")


class TestCutoff(unittest.TestCase):
    def test_october_1_excludes_october_rows_includes_september(self):
        today = dt.date(2026, 10, 1)
        self.assertTrue(rp.month_within_cutoff("30/09/2569", today))
        self.assertFalse(rp.month_within_cutoff("01/10/2569", today))
        self.assertFalse(rp.in_period("01/10/2569", rp.period_for(today)))

    def test_october_2_admits_october_1(self):
        today = dt.date(2026, 10, 2)
        self.assertTrue(rp.month_within_cutoff("01/10/2569", today))
        self.assertFalse(rp.month_within_cutoff("02/10/2569", today))
        self.assertTrue(rp.in_period("01/10/2569", rp.period_for(today)))

    def test_future_month_excluded(self):
        self.assertFalse(rp.month_within_cutoff("01/11/2569", dt.date(2026, 10, 15)))

    def test_bad_date_ignored(self):
        self.assertIsNone(rp.month_key_of(""))
        self.assertFalse(rp.month_within_cutoff("", dt.date(2026, 10, 15)))
        self.assertEqual(rp.month_key_of("24/9/2569"), ("2569-09", 24))

    def test_elapsed_month_full_count(self):
        today = dt.date(2026, 10, 15)
        self.assertTrue(rp.month_is_elapsed("2569-09", today))
        self.assertFalse(rp.month_is_elapsed("2569-10", today))


class TestBangkokDate(unittest.TestCase):
    def test_utc_evening_is_next_day_in_bangkok(self):
        # 2026-10-01 18:30 UTC = 2026-10-02 01:30 (+07) -> the 2nd, not the 1st
        self.assertEqual(rp.today_bangkok(dt.datetime(2026, 10, 1, 18, 30, tzinfo=dt.timezone.utc)),
                         dt.date(2026, 10, 2))
        self.assertEqual(rp.today_bangkok(dt.datetime(2026, 9, 30, 17, 30, tzinfo=dt.timezone.utc)),
                         dt.date(2026, 10, 1))


if __name__ == "__main__":
    unittest.main()
