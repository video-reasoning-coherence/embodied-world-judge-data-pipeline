#!/usr/bin/env python3
"""Validate a note->reasoning rewrite delivery.

Usage:  python check_rewrite.py units.jsonl rewritten.jsonl

Exit codes: 0 valid, 1 invalid.
"""
import json
import re
import sys

AXIS_NAMES = {
    "pa": ["Agent integrity", "Scene & object consistency", "Interaction realism"],
    "ia": ["Agent match", "Object correctness", "Goal completion"],
}
CJK = re.compile(r"[一-鿿]")
VERDICT = re.compile(r"\((?:PA|IA)[1-5]\)")
FRAME = re.compile(r"\bf\d{2}\b")
SCAFFOLD = re.compile(r"[✓⚠]|代\s")


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    units = {u["unit_id"]: u for u in load(sys.argv[1])}
    out = load(sys.argv[2])

    fails = []
    seen = {}
    for row in out:
        uid = row.get("unit_id")
        if uid is None:
            fails.append("a row has no unit_id")
            continue
        if uid in seen:
            fails.append("duplicate unit_id: %s" % uid)
            continue
        seen[uid] = row
        if uid not in units:
            fails.append("unknown unit_id: %s" % uid)
            continue
        text = row.get("reasoning") or ""
        if not text.strip():
            fails.append("%s: empty reasoning" % uid)
            continue
        if CJK.search(text):
            fails.append("%s: Chinese characters remain" % uid)
        if VERDICT.search(text):
            fails.append("%s: contains a (PAn)/(IAn) verdict" % uid)
        if FRAME.search(text) or SCAFFOLD.search(text):
            fails.append("%s: annotator scaffolding not removed" % uid)
        for name in AXIS_NAMES[units[uid]["axis"]]:
            if name not in text:
                fails.append("%s: axis '%s' not covered" % (uid, name))

    missing = set(units) - set(seen)
    if missing:
        fails.append("%d units missing from the delivery (e.g. %s)"
                     % (len(missing), sorted(missing)[0]))

    print("units in  : %d" % len(units))
    print("units out : %d" % len(seen))
    for message in fails[:25]:
        print("FAIL  " + message)
    if len(fails) > 25:
        print("FAIL  ... and %d more" % (len(fails) - 25))
    print("\n%s  (%d failures)" % ("PASS" if not fails else "INVALID", len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
