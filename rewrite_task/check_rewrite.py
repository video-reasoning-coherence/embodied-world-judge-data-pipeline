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
# Floors, not targets. The reasoning already in the training set has a p10 of 878 chars for pa
# and 531 for ia; these sit well below that so that genuinely terse-but-complete answers pass,
# while a one-line stub cannot.
MIN_CHARS = {"pa": 400, "ia": 300}
# The reference medians, printed for comparison so length drift is visible without reading.
REFERENCE_MEDIAN = {"pa": 1044, "ia": 669}


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
        axis = units[uid]["axis"]
        if len(text) < MIN_CHARS[axis]:
            fails.append("%s: reasoning is %d chars, below the %d floor for %s -- three criteria "
                         "cannot be addressed in that space" % (uid, len(text), MIN_CHARS[axis], axis))
        if CJK.search(text):
            fails.append("%s: Chinese characters remain" % uid)
        if VERDICT.search(text):
            fails.append("%s: contains a (PAn)/(IAn) verdict" % uid)
        if FRAME.search(text) or SCAFFOLD.search(text):
            fails.append("%s: annotator scaffolding not removed" % uid)
        for name in AXIS_NAMES[axis]:
            if name not in text:
                fails.append("%s: axis '%s' not covered" % (uid, name))

    missing = set(units) - set(seen)
    if missing:
        fails.append("%d units missing from the delivery (e.g. %s)"
                     % (len(missing), sorted(missing)[0]))

    print("units in  : %d" % len(units))
    print("units out : %d" % len(seen))
    if seen:
        for axis in ("pa", "ia"):
            lens = sorted(len(r.get("reasoning") or "")
                          for uid, r in seen.items()
                          if uid in units and units[uid]["axis"] == axis)
            if lens:
                print("chars %-3s : median %d  p10 %d  p90 %d   (reference median %d)"
                      % (axis, lens[len(lens) // 2], lens[len(lens) // 10],
                         lens[len(lens) * 9 // 10], REFERENCE_MEDIAN[axis]))
        # A templated delivery repeats whole sentences. Not a failure, but worth seeing.
        sents = {}
        for row in seen.values():
            for part in re.split(r"(?<=[.!?])\s+", row.get("reasoning") or ""):
                part = part.strip()
                if len(part) > 40:
                    sents[part] = sents.get(part, 0) + 1
        if sents:
            top, n = max(sents.items(), key=lambda kv: kv[1])
            share = 100.0 * n / len(seen)
            print("repeats   : most common sentence appears in %d units (%.1f%%)" % (n, share))
            if share >= 5.0:
                print("            -> %s" % top[:110])
    for message in fails[:25]:
        print("FAIL  " + message)
    if len(fails) > 25:
        print("FAIL  ... and %d more" % (len(fails) - 25))
    print("\n%s  (%d failures)" % ("PASS" if not fails else "INVALID", len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
