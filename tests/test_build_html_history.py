#!/usr/bin/env python3
"""The data page must embed resolved history for the shared UI engine."""
import json
import re
import unittest

import build_html


class TestIndexResolvedHistoryEmbedding(unittest.TestCase):
    def test_build_html_includes_resolved_history_dataset(self):
        resolved = [{
            "date": "1/10/2569",
            "hn": "TEST-HN",
            "dept": "Eye",
            "missing": ["AN"],
            "month_key": "2569-10",
        }]
        html = build_html.build_html({
            "repo": "audit",
            "as_of": "08/10/2026",
            "generated_at": "14:33",
            "current": {"fy": "2570", "month": "2569-10"},
            "period": {},
            "fiscal_years": [],
            "periods": {},
            "fy_totals": {},
            "all_cases": [],
            "resolved_cases": resolved,
        })
        match = re.search(r"var AUDIT_DATA = (.*?);\s*\(function", html, re.S)
        self.assertIsNotNone(match)
        embedded = json.loads(match.group(1))
        self.assertEqual(embedded["resolved_cases"], resolved)


if __name__ == "__main__":
    unittest.main()
