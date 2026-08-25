#!/usr/bin/env python3
"""Validate a source dataset against the format specification.

Usage:
    python tools/validate_dataset.py <dataset_dir> [--spec v2] [--strict-media]

Specs:
    v2  (default) for new batches: adds action_caption and speed_factor, and
        enforces the clip-duration policy.
    v1  the original eleven-field format, used by the existing corpus.

Exit codes: 0 valid, 1 invalid.
"""
import argparse
import collections
import json
import os
import subprocess
import sys

V1 = ["gt_path", "image", "task_name", "episode_name", "prompt",
      "prompt_prefix", "prompt_rewrite", "prefix_id", "rewrite_id",
      "duration", "init_frame_offset_sec"]
V2 = V1 + ["action_caption", "speed_factor"]

DURATION_MIN = 5.0
DURATION_MAX = 20.0
DURATION_PREFERRED = (5.0, 10.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="path to data/<dataset>")
    ap.add_argument("--spec", choices=["v1", "v2"], default="v2")
    ap.add_argument("--strict-media", action="store_true",
                    help="decode every video with ffprobe")
    args = ap.parse_args()

    root = args.root.rstrip("/")
    dataset = os.path.basename(root)
    required = V1 if args.spec == "v1" else V2
    fails, warns = [], []

    summary_path = os.path.join(root, "summary.json")
    if not os.path.exists(summary_path):
        print("FAIL  no summary.json at %s" % summary_path)
        sys.exit(1)

    rows = json.load(open(summary_path, encoding="utf-8"))
    if not isinstance(rows, list):
        print("FAIL  summary.json must be a JSON array, got %s"
              % type(rows).__name__)
        sys.exit(1)

    print("dataset=%s  episodes=%d  spec=%s" % (dataset, len(rows), args.spec))

    # Schema
    for i, row in enumerate(rows):
        missing = [k for k in required if k not in row]
        if missing:
            fails.append("row %d missing %s" % (i, missing))
        extra = [k for k in row if k not in required]
        if extra:
            warns.append("row %d has unrecognised fields %s" % (i, extra))
        if "prompt" in row and not isinstance(row["prompt"], list):
            fails.append("row %d: prompt must be an array" % i)
        for key in ("duration", "init_frame_offset_sec"):
            if key in row and not isinstance(row[key], (int, float)):
                fails.append("row %d: %s must be a number" % (i, key))
        if args.spec == "v2":
            caption = row.get("action_caption")
            if caption is not None and (not isinstance(caption, str)
                                        or not caption.strip()):
                fails.append("row %d: action_caption must be a non-empty string" % i)
            speed = row.get("speed_factor")
            if speed is not None and (not isinstance(speed, (int, float))
                                      or speed <= 0):
                fails.append("row %d: speed_factor must be a positive number" % i)

    # Clip duration policy (v2 only)
    if args.spec == "v2":
        short = [i for i, r in enumerate(rows)
                 if isinstance(r.get("duration"), (int, float))
                 and r["duration"] < DURATION_MIN]
        long_ = [i for i, r in enumerate(rows)
                 if isinstance(r.get("duration"), (int, float))
                 and r["duration"] > DURATION_MAX]
        if short:
            fails.append("%d clips shorter than %.0fs (rows %s)"
                         % (len(short), DURATION_MIN, short[:5]))
        if long_:
            fails.append("%d clips longer than %.0fs (rows %s)"
                         % (len(long_), DURATION_MAX, long_[:5]))
        lo, hi = DURATION_PREFERRED
        outside = sum(1 for r in rows
                      if isinstance(r.get("duration"), (int, float))
                      and not lo <= r["duration"] <= hi)
        if outside:
            warns.append("%d of %d clips outside the preferred %.0f-%.0fs band"
                         % (outside, len(rows), lo, hi))

    # Identifier uniqueness
    keys = [(r.get("task_name"), r.get("episode_name")) for r in rows]
    duplicates = [k for k, n in collections.Counter(keys).items() if n > 1]
    if duplicates:
        fails.append("duplicate (task_name, episode_name): %s" % duplicates[:5])

    # Files exist and agree with the layout
    missing_counts = collections.Counter()
    for row in rows:
        task, episode = row.get("task_name"), row.get("episode_name")
        episode_dir = os.path.join(root, "gt_data", str(task), str(episode))
        for rel in ("video.mp4", "prompt/init_frame.png", "prompt/prompt.txt"):
            if not os.path.exists(os.path.join(episode_dir, rel)):
                missing_counts[rel] += 1
        expected = "gt_data/%s/%s/video.mp4" % (task, episode)
        if row.get("gt_path") and not str(row["gt_path"]).endswith(expected):
            warns.append("gt_path does not match the layout for %s/%s: %s"
                         % (task, episode, row.get("gt_path")))
    for rel, n in missing_counts.items():
        fails.append("%d episodes missing %s" % (n, rel))

    # Media decodes
    if args.strict_media:
        undecodable = []
        for row in rows:
            video = os.path.join(root, "gt_data", str(row.get("task_name")),
                                 str(row.get("episode_name")), "video.mp4")
            if not os.path.exists(video):
                continue
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", video],
                capture_output=True, text=True)
            if probe.returncode != 0 or not probe.stdout.strip():
                undecodable.append(video)
        print("media: checked %d videos, %d undecodable"
              % (len(rows), len(undecodable)))
        if undecodable:
            fails.append("%d videos do not decode (e.g. %s)"
                         % (len(undecodable), undecodable[0]))

    for message in warns[:20]:
        print("WARN  " + message)
    if len(warns) > 20:
        print("WARN  ... and %d more" % (len(warns) - 20))
    for message in fails[:20]:
        print("FAIL  " + message)
    if len(fails) > 20:
        print("FAIL  ... and %d more" % (len(fails) - 20))

    print("\n%s  (%d failed, %d warnings)"
          % ("PASS" if not fails else "INVALID", len(fails), len(warns)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
