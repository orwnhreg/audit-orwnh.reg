#!/usr/bin/env python3
"""Seed cumulative missing-column history from prior published audit snapshots."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "missing_history.json"
if OUT.exists():
    raise SystemExit("Refusing to overwrite existing missing_history.json")
commits = subprocess.check_output(
    ["git", "log", "--format=%H", "--", "audit_data.json"], cwd=ROOT, text=True
).splitlines()
history = {}
VALID_COLUMNS = {"เวลาออกจากห้องผ่าตัด", "ชื่อ", "AN", "สิทธิ์", "First Dx", "Last Dx",
                 "Operation", "Type", "Risk", "Wound Type", "Surgeon", "Aneasthesia",
                 "เวร", "ชื่อซ้ำในทีม"}
for commit in reversed(commits):
    raw = subprocess.check_output(
        ["git", "show", f"{commit}:audit_data.json"], cwd=ROOT, text=True
    )
    data = json.loads(raw)
    for case in data.get("all_cases", []):
        month = case.get("month_key")
        if not month or not case.get("hn") or not case.get("date"):
            continue
        key = f"{case['hn']}|{case['date']}"
        entry = history.setdefault(key, {"month_key": month, "missing": []})
        entry["missing"] = sorted(set(entry["missing"]) | (set(case.get("missing", [])) & VALID_COLUMNS))
    # Earliest snapshots predate all_cases; their current-month case list is still useful.
    for case in data.get("month", {}).get("cases", []):
        if not case.get("hn") or not case.get("date"):
            continue
        parts = case["date"].split("/")
        if len(parts) != 3:
            continue
        month = f"{parts[2]}-{int(parts[1]):02d}"
        key = f"{case['hn']}|{case['date']}"
        entry = history.setdefault(key, {"month_key": month, "missing": []})
        entry["missing"] = sorted(set(entry["missing"]) | (set(case.get("missing", [])) & VALID_COLUMNS))
OUT.write_text(json.dumps(history, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
from collections import Counter
current = Counter(m for entry in history.values() if entry["month_key"] == "2569-09" for m in entry["missing"])
print(f"snapshots={len(commits)} tracked_cases={len(history)} september={dict(current)}")
