#!/usr/bin/env python3
"""Validate a source dataset against the contract in docs/01-source-contract.md.

Usage:  python tools/validate_dataset.py data/<dataset> [--strict-media]

Exit 0 = mergeable. Any FAIL = not mergeable.
--strict-media additionally decodes every video (slow, but catches the
truncated-file class that has bitten this project before).
"""
import argparse, collections, json, os, subprocess, sys

REQUIRED = ["gt_path", "image", "task_name", "episode_name", "prompt",
            "prompt_prefix", "prompt_rewrite", "prefix_id", "rewrite_id",
            "duration", "init_frame_offset_sec"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="path to data/<dataset>")
    ap.add_argument("--strict-media", action="store_true")
    a = ap.parse_args()
    root = a.root.rstrip("/")
    ds = os.path.basename(root)
    fails, warns = [], []

    def fail(m): fails.append(m)
    def warn(m): warns.append(m)

    sp = os.path.join(root, "summary.json")
    if not os.path.exists(sp):
        print("FAIL  no summary.json at %s" % sp); sys.exit(1)
    rows = json.load(open(sp, encoding="utf-8"))
    if not isinstance(rows, list):
        print("FAIL  summary.json must be a JSON list, got %s" % type(rows).__name__); sys.exit(1)
    print("dataset=%s  episodes=%d" % (ds, len(rows)))

    # --- schema ---
    for i, r in enumerate(rows):
        missing = [k for k in REQUIRED if k not in r]
        if missing: fail("row %d missing %s" % (i, missing))
        extra = [k for k in r if k not in REQUIRED]
        if extra: warn("row %d has extra fields %s" % (i, extra))
        if "prompt" in r and not isinstance(r["prompt"], list):
            fail("row %d: prompt must be a list" % i)
        for k in ("duration", "init_frame_offset_sec"):
            if k in r and not isinstance(r[k], (int, float)):
                fail("row %d: %s must be numeric" % (i, k))

    # --- uniqueness ---
    keys = [(r.get("task_name"), r.get("episode_name")) for r in rows]
    dup = [k for k, c in collections.Counter(keys).items() if c > 1]
    if dup: fail("duplicate (task_name, episode_name): %s" % dup[:5])

    # --- paths exist and agree with the layout ---
    missing_v = missing_i = missing_p = 0
    for r in rows:
        t, e = r.get("task_name"), r.get("episode_name")
        d = os.path.join(root, "gt_data", str(t), str(e))
        if not os.path.exists(os.path.join(d, "video.mp4")): missing_v += 1
        if not os.path.exists(os.path.join(d, "prompt", "init_frame.png")): missing_i += 1
        if not os.path.exists(os.path.join(d, "prompt", "prompt.txt")): missing_p += 1
        want = "data/%s/gt_data/%s/%s/video.mp4" % (ds, t, e)
        if r.get("gt_path") and not str(r["gt_path"]).endswith(want.split("data/", 1)[1]):
            warn("gt_path does not match layout for %s/%s: %s" % (t, e, r.get("gt_path")))
    for n, what in ((missing_v, "video.mp4"), (missing_i, "prompt/init_frame.png"),
                    (missing_p, "prompt/prompt.txt")):
        if n: fail("%d episodes missing %s" % (n, what))

    # --- media decodes (the truncated-file class) ---
    if a.strict_media:
        bad = []
        for r in rows:
            v = os.path.join(root, "gt_data", str(r.get("task_name")),
                             str(r.get("episode_name")), "video.mp4")
            if not os.path.exists(v): continue
            p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                "format=duration", "-of", "csv=p=0", v],
                               capture_output=True, text=True)
            if p.returncode != 0 or not p.stdout.strip():
                bad.append((v, (p.stderr or "").strip().splitlines()[:1]))
        if bad:
            fail("%d videos do not decode (e.g. %s)" % (len(bad), bad[0][0]))
        print("media: decoded %d videos, %d undecodable" % (len(rows), len(bad)))

    for w in warns[:20]: print("WARN  " + w)
    if len(warns) > 20: print("WARN  ... +%d more" % (len(warns) - 20))
    for f in fails[:20]: print("FAIL  " + f)
    if len(fails) > 20: print("FAIL  ... +%d more" % (len(fails) - 20))
    print("\n%s  (%d fail, %d warn)" % ("PASS" if not fails else "NOT MERGEABLE",
                                        len(fails), len(warns)))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
