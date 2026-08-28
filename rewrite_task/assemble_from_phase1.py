#!/usr/bin/env python3
"""Assemble the three-line SFT reasoning directly from the per-model phase-1 outputs.

Phase 1 wrote one flowing paragraph per unit. The target form is one line per axis. Those are the
same sentences in a different layout, so most units can be converted rather than regenerated:
split the paragraph at each axis name.

Per unit the models are tried in order and the first output that converts cleanly wins. This is a
fallback, not a vote: a vote selects the text the models agree on, which says nothing about whether
it obeys the format. Any unit no model can supply is reported, never invented.

Usage:
  python assemble_from_phase1.py --units units.jsonl \
      --phase1 gpt55=phase1_gpt55.jsonl --phase1 gpt52=phase1_gpt52.jsonl \
      --out delivery/rewritten.jsonl --gaps delivery/gaps.txt
"""
import argparse
import json
import re

AXIS_NAMES = {
    "pa": ["Agent integrity", "Scene & object consistency", "Interaction realism"],
    "ia": ["Agent match", "Object correctness", "Goal completion"],
}
# Content that must not survive into a training target. The score lives in its own field; the model
# never sees an annotator or the other candidates at inference.
REJECT = re.compile(
    r"score of \d|score is \d|\bscore \d\b|\bsub[- ]?scores?\b|\bmain score\b|\((?:PA|IA)[1-5]\)|"
    r"\bdescription\s*:|\bannotator|\bthe note\b|\bcandidates?\b|\bconsensus\b|\breportedly\b|"
    r"\bas reported\b|[一-鿿]", re.I)


def to_lines(text, axis):
    """Split one paragraph into exactly three axis lines, or return None if it does not fit.

    A line must OPEN with its axis name; a verdict phrase may sit between the name and the colon
    ("Interaction realism severely violated:"), which is what the reference format does.
    """
    text = re.sub(r"\s+", " ", text or "").strip()
    positions = []
    for name in AXIS_NAMES[axis]:
        m = re.search(r"(?<![A-Za-z])" + re.escape(name), text)
        if not m:
            return None
        positions.append((m.start(), name))
    if [p[0] for p in positions] != sorted(p[0] for p in positions):
        return None  # axes out of order
    if positions[0][0] != 0:
        return None  # paragraph does not begin with the first axis
    lines = []
    for k, (start, _) in enumerate(positions):
        end = positions[k + 1][0] if k + 1 < len(positions) else len(text)
        lines.append(text[start:end].strip().rstrip(" ,;"))
    return "\n".join(lines)


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--units", required=True)
    ap.add_argument("--phase1", action="append", required=True,
                    help="name=path, repeatable; tried in the order given")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gaps", required=True)
    args = ap.parse_args()

    units = {u["unit_id"]: u for u in load_jsonl(args.units)}
    sources = []
    for spec in args.phase1:
        name, _, path = spec.partition("=")
        rows = {}
        for r in load_jsonl(path):
            u = units.get(r["unit_id"])
            if not u:
                continue
            converted = to_lines(r.get("reasoning"), u["axis"])
            if converted and not REJECT.search(converted):
                rows[r["unit_id"]] = converted
        sources.append((name, rows))
        print("%-12s usable: %d" % (name, len(rows)))

    written, gaps, used = 0, [], {}
    with open(args.out, "w", encoding="utf-8") as fh:
        for uid in units:
            for name, rows in sources:
                if uid in rows:
                    fh.write(json.dumps({"unit_id": uid, "reasoning": rows[uid],
                                         "source_model": name}, ensure_ascii=False) + "\n")
                    used[name] = used.get(name, 0) + 1
                    written += 1
                    break
            else:
                gaps.append(uid)
    with open(args.gaps, "w", encoding="utf-8") as fh:
        fh.writelines(g + "\n" for g in gaps)

    print("\nassembled %d / %d (%.1f%%)" % (written, len(units), 100.0 * written / len(units)))
    for name, n in used.items():
        print("   from %-12s %d" % (name, n))
    print("gaps %d -> %s  (these must be generated; do not invent them)" % (len(gaps), args.gaps))


if __name__ == "__main__":
    main()
