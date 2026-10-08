#!/usr/bin/env python3
"""Resolved-history cases must be live, previously flagged, and in the report window."""
import datetime as dt
import sys
import unittest

sys.path.insert(0, "/home/kttwatt/.hermes/scripts")
import register_site_update as site  # noqa: E402


def row(hn, date, finished=True, dept="Surgery"):
    values = [""] * 56
    values[2] = date
    values[4] = dept
    values[11] = "10:00:00" if finished else ""
    values[15] = hn
    return values


class TestResolvedHistory(unittest.TestCase):
    def test_includes_only_existing_previously_flagged_cases_no_longer_pending(self):
        ever_seen = {
            "101|1/10/2569": "2569-10",  # fixed, still in register
            "102|2/10/2569": "2569-10",  # still pending
            "103|1/10/2569": "2569-10",  # removed from register
            "104|2/10/2569": "2569-10",  # unfinished
            "105|3/10/2569": "2569-10",  # today's row, outside cutoff
            "106|1/10/2569": "2569-09",  # tracker month disagrees with live row
        }
        pending = {"102|2/10/2569"}
        history = {
            "101|1/10/2569": {"month_key": "2569-10", "missing": ["AN", "Risk"]},
            "102|2/10/2569": {"month_key": "2569-10", "missing": ["Address"]},
        }
        live_rows = [
            row("101", "1/10/2569", dept="Eye"),
            row("102", "2/10/2569"),
            row("104", "2/10/2569", finished=False),
            row("105", "3/10/2569"),
            row("106", "1/10/2569"),
        ]

        result = site.build_resolved_history(
            ever_seen, pending, history, live_rows, today=dt.date(2026, 10, 3)
        )

        self.assertEqual(result, [{
            "date": "1/10/2569",
            "hn": "101",
            "dept": "Eye",
            "missing": ["AN", "Risk"],
            "month_key": "2569-10",
        }])

    def test_orders_history_newest_first_within_month(self):
        ever_seen = {
            "101|1/10/2569": "2569-10",
            "102|2/10/2569": "2569-10",
        }
        live_rows = [row("101", "1/10/2569"), row("102", "2/10/2569")]

        result = site.build_resolved_history(ever_seen, set(), {}, live_rows, today=dt.date(2026, 10, 4))

        self.assertEqual([case["hn"] for case in result], ["102", "101"])


if __name__ == "__main__":
    unittest.main()
