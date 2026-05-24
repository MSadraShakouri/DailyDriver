#!/usr/bin/env python3
"""Assign a unique numeric ID to every calendar event that lacks one.
Processes files in order: Jalali → Hijri → Gregorian.
Safe to run multiple times – only new events will receive IDs."""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
FILES = ["events_jalali.json", "events_hijri.json", "events_gregorian.json"]

# ----- find the highest existing ID -----
max_id = 0
for fname in FILES:
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        continue
    with open(path, "r", encoding="utf-8") as f:
        events = json.load(f)
    for ev in events:
        if "id" in ev and isinstance(ev["id"], int):
            max_id = max(max_id, ev["id"])

next_id = max_id + 1
assigned = 0

# ----- assign IDs to events that are missing them -----
for fname in FILES:
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        continue
    with open(path, "r", encoding="utf-8") as f:
        events = json.load(f)

    changed = False
    for ev in events:
        if "id" not in ev:
            ev["id"] = next_id
            next_id += 1
            assigned += 1
            changed = True

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)

if assigned:
    print(f"Assigned {assigned} new ID(s). Next available ID: {next_id}")
else:
    print(f"All events already have IDs. Next available ID: {next_id}")
