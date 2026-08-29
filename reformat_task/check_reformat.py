#!/usr/bin/env python3
"""Validate a reformat delivery: three lines, in band, and no length signal for the score.

Usage:  python check_rewrite.py units_22568.jsonl rewritten.jsonl

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
# The reasoning is a plain-prose JSON string field. Markdown headings, bold and bullets teach the
# model to emit layout it should never produce.
MARKUP = re.compile(r"^[ \t]*#{1,6}[ \t]|\*\*|^[ \t]*[-*][ \t]|^[ \t]*\d+[.)][ \t]", re.M)
# The score lives in its own JSON field. Any number in the prose puts the same answer in the row
# twice, which is the defect this format exists to remove.
SCORE_IN_PROSE = re.compile(
    r"score of \d|score is \d|\bscore \d\b|\bsub[- ]?scores?\b|\(\s*[0-5]\s*\)\s*:|"
    r"\bmain score\b|overall\s+(?:PA|IA|physical|instruction)[^.]{0,25}score|"
    r"\b(?:agent_consistency|scene_consistency|interaction_realism|agent_match|object_correct|"
    r"goal_completed|physical_adherence|instruction_alignment)\s*=\s*\d", re.I)
# At inference the model sees a video and a prompt. It never sees an annotator, a note, or the
# other candidates in whatever pipeline produced this text.
PIPELINE_REF = re.compile(
    r"\bannotator|\bthe note (?:says|said|states|describes|mentions|records|gives|notes)\b|"
    r"\bper the note\b|\baccording to the note\b|\bhuman note\b|"
    r"\bcandidates?\b|some inputs|other inputs|\bconsensus\b|as reported|\breportedly\b", re.I)
# Accepted misspellings of an axis name, so the failure says "wrong form" instead of "missing".
AXIS_VARIANTS = {
    "Scene & object consistency": ("scene and object consistency", "scene/object consistency",
                                   "scene consistency", "agent consistency"),
    "Agent integrity": ("agent consistency",),
    "Object correctness": ("object correct",),
    "Goal completion": ("goal completed",),
}
VERDICT = re.compile(r"\((?:PA|IA)[1-5]\)")
FRAME = re.compile(r"\bf\d{2}\b")
SCAFFOLD = re.compile(r"[✓⚠]|代\s")
# Floors, not targets. One line per axis at the annotator's own density lands around 250-400 chars,
# and a unit where nothing went wrong is legitimately at the short end -- there is little to report
# beyond what the clip shows. These floors sit below that so a terse-but-complete answer passes and a
# stub does not. Deliberately NOT near the old prose corpus median: padding to that length would mean
# inventing.
# Anchored on 7.20_baseline_rephrased itself, once its header and verdict lines -- which we
# drop -- are removed: pa median 423, ia median 257. The 965 rows written from video already
# sit there (pa 402 / ia 300), so this band is the reference format's own length.
MIN_CHARS = {"pa": 300, "ia": 220}
MAX_CHARS = {"pa": 550, "ia": 450}


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
        axis = units[uid]["axis"]
        if len(text) > MAX_CHARS[axis]:
            fails.append("%s: reasoning is %d chars, over the %d ceiling for %s -- compress it"
                         % (uid, len(text), MAX_CHARS[axis], axis))
        if len(text) < MIN_CHARS[axis]:
            fails.append("%s: reasoning is %d chars, below the %d floor for %s -- three criteria "
                         "cannot be addressed in that space" % (uid, len(text), MIN_CHARS[axis], axis))
        if CJK.search(text):
            fails.append("%s: Chinese characters remain" % uid)
        if VERDICT.search(text):
            fails.append("%s: contains a (PAn)/(IAn) verdict" % uid)
        hit = SCORE_IN_PROSE.search(text)
        if hit:
            fails.append("%s: states a score in the prose (%r) -- the score is already in the "
                         "row's own field" % (uid, hit.group(0)))
        if MARKUP.search(text):
            fails.append("%s: contains markdown (heading, bold or bullet) -- the reasoning is plain "
                         "prose inside a JSON string" % uid)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) != 3:
            fails.append("%s: has %d non-empty lines, expected exactly 3 -- one line per axis"
                         % (uid, len(lines)))
        # Each line must OPEN with its axis name. A short verdict phrase may sit between the
        # name and the colon ("Interaction realism severely violated:"), which is what the
        # reference format does; what is not allowed is a line that does not start with the name.
        for i, name in enumerate(AXIS_NAMES[axis]):
            if i < len(lines) and not lines[i].startswith(name):
                fails.append("%s: line %d should open with '%s' but starts %r"
                             % (uid, i + 1, name, lines[i][:40]))
        if re.search(r"description\s*:", text, re.I):
            fails.append("%s: contains a 'description:' header -- start directly with the first axis"
                         % uid)
        hit = PIPELINE_REF.search(text)
        if hit:
            fails.append("%s: refers to something the model cannot see at inference (%r)"
                         % (uid, hit.group(0)))
        if FRAME.search(text) or SCAFFOLD.search(text):
            fails.append("%s: annotator scaffolding not removed" % uid)
        lowered = re.sub(r"\s+", " ", text.lower())
        for name in AXIS_NAMES[axis]:
            if name in text:
                continue
            variant = next((v for v in AXIS_VARIANTS.get(name, ()) if v in lowered), None)
            if variant:
                fails.append("%s: axis '%s' written as '%s' -- use the exact string"
                             % (uid, name, variant))
            elif name.lower() in lowered:
                fails.append("%s: axis '%s' has the wrong capitalisation" % (uid, name))
            else:
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
                print("chars %-3s : median %d  p10 %d  p90 %d"
                      % (axis, lens[len(lens) // 2], lens[len(lens) // 10],
                         lens[len(lens) * 9 // 10]))
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
    if seen:
        by_score = {}
        for uid, row in seen.items():
            u = units.get(uid)
            if not u:
                continue
            by_score.setdefault(u["main_score"], []).append(len(row.get("reasoning") or ""))
        print("\nmedian length by main_score -- these must not separate, or length leaks the score:")
        meds = {}
        for score in sorted(by_score):
            v = sorted(by_score[score])
            meds[score] = v[len(v) // 2]
            print("   score %d  n=%5d  median %4d" % (score, len(v), meds[score]))
        if len(meds) > 1:
            spread = max(meds.values()) - min(meds.values())
            print("   spread %d chars %s" % (spread, "OK" if spread <= 80 else "<-- TOO WIDE"))
            if spread > 80:
                fails.append("length still separates the scores: %d-char spread between score "
                             "medians (limit 80)" % spread)
    for message in fails[:25]:
        print("FAIL  " + message)
    if len(fails) > 25:
        print("FAIL  ... and %d more" % (len(fails) - 25))
    print("\n%s  (%d failures)" % ("PASS" if not fails else "INVALID", len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
