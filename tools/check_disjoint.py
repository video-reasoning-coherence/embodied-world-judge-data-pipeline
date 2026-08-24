#!/usr/bin/env python3
"""Check a new source dataset does not collide with already-released data.

Usage:
  python tools/check_disjoint.py data/<new_dataset> --against <summary.json|jsonl> ...

Compares on two keys:
  * (task_name, episode_name) within the same dataset name
  * gt_path
and reports any overlap. Exit 0 = disjoint.
"""
import argparse, json, os, sys

def load_keys(path):
    """Return (dataset, task, episode) triples and gt_paths from a summary.json
    or from a released split (.jsonl with item_id/dataset/task/episode)."""
    trips, paths = set(), set()
    if path.endswith(".jsonl"):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line: continue
            r = json.loads(line)
            if r.get("dataset") and r.get("task") and r.get("episode"):
                trips.add((r["dataset"], str(r["task"]), str(r["episode"])))
    else:
        ds = os.path.basename(os.path.dirname(os.path.abspath(path)))
        for r in json.load(open(path, encoding="utf-8")):
            trips.add((ds, str(r.get("task_name")), str(r.get("episode_name"))))
            if r.get("gt_path"): paths.add(r["gt_path"])
    return trips, paths

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--against", nargs="+", required=True)
    a = ap.parse_args()
    new_t, new_p = load_keys(os.path.join(a.root.rstrip("/"), "summary.json"))
    print("new dataset: %d episodes" % len(new_t))
    bad = False
    for ref in a.against:
        t, p = load_keys(ref)
        ot, op = new_t & t, new_p & p
        print("  vs %-48s  key-overlap %4d   gt_path-overlap %4d" % (
            os.path.basename(ref), len(ot), len(op)))
        if ot:
            bad = True
            for x in list(ot)[:5]: print("      COLLIDES %s" % (x,))
        if op:
            bad = True
            for x in list(op)[:5]: print("      COLLIDES %s" % x)
    print("\n%s" % ("NOT DISJOINT" if bad else "PASS — disjoint"))
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
