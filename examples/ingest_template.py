#!/usr/bin/env python3
"""Reference ingest script for a new source dataset (format spec v2).

Implements the four clip rules so a new corpus only has to supply
`iter_source_episodes()`:

  1. duration   5-10s preferred, 5s floor, 20s hard cap
  2. speed      retime clips that are too slow; record `speed_factor`
  3. init frame both the manipulator and the target object must be visible
  4. caption    every episode carries an `action_caption`

Usage:
    export EWJ_DATA_ROOT=/path/to/data
    export GEMINI_API_KEY=...
    python examples/ingest_template.py --dataset my_dataset --family robot --target 150
"""
import argparse
import json
import os
import random
import shutil
import subprocess
from pathlib import Path

MIN_S, MAX_S = 5.0, 20.0
PREFERRED = (5.0, 10.0)
RETRY_OFFSETS = (0.3, 0.7, 1.2, 1.8)
ALLOWED_SPEEDS = (1.0, 1.5, 2.0)


# --------------------------------------------------------------------------
# Supply this for your corpus.
# --------------------------------------------------------------------------
def iter_source_episodes():
    """Yield dicts: {'video': Path, 'start': float, 'end': float, 'label': str}.

    `label` is the corpus's own task text; it is refined against the
    conditioning frame later.
    """
    raise NotImplementedError("implement enumeration for your source corpus")


# --------------------------------------------------------------------------
def ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def choose_speed(raw_duration):
    """Pick the smallest allowed speed-up that brings the clip into band.

    Returns None if no allowed speed can do it, meaning the episode is dropped.
    """
    for speed in ALLOWED_SPEEDS:
        if PREFERRED[0] <= raw_duration / speed <= PREFERRED[1]:
            return speed
    for speed in ALLOWED_SPEEDS:
        if MIN_S <= raw_duration / speed <= MAX_S:
            return speed
    return None


def cut_clip(src, start, end, speed, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-i", str(src),
           "-t", str(end - start)]
    if speed != 1.0:
        # setpts slows/speeds video; 1/speed < 1 makes it faster
        cmd += ["-filter:v", "setpts=%.6f*PTS" % (1.0 / speed), "-an"]
    cmd += [str(dest)]
    return subprocess.run(cmd, capture_output=True, timeout=300).returncode == 0


def extract_frame(video, at, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", str(at), "-i", str(video),
         "-frames:v", "1", str(dest)],
        capture_output=True, timeout=60).returncode == 0


# --------------------------------------------------------------------------
# Vision-language calls. Replace `vlm()` with your provider.
# --------------------------------------------------------------------------
FRAME_CHECK = """The image is the first frame of a {family} manipulation video.
Task: "{label}"

Answer two questions about THIS frame:
1. manipulator_visible: is the {actor} clearly visible? Requires recognizable
   structure, not just an edge or a sleeve.
2. object_visible: is the object the task refers to clearly visible?

Reply with JSON only:
{{"manipulator_visible": true|false, "object_visible": true|false,
  "evidence": "<15 words or fewer>"}}"""

REFINE = """The image is the first frame of a {family} manipulation task.
Original label: "{label}"

Write a refined ONE-LINE imperative instruction grounded in this frame:
1. imperative form, start with a verb
2. name specific visible objects (colour, shape) and target locations
3. refer to the {actor}
4. no meta-commentary, no scene words unless verifiable from the frame
5. a task command, not a description

Reply with JSON only: {{"prompt": "<one line>"}}"""

CAPTION = """The image is the first frame; the instruction is "{prompt}".

Write an action_caption: one or two sentences describing the COMPLETE action
from start to completion state, in the third person present tense.

Reply with JSON only: {{"action_caption": "<text>"}}"""


def vlm(prompt, image_bytes):
    """Return the parsed JSON dict, or None."""
    raise NotImplementedError("wire up your VLM provider")


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--family", choices=["robot", "human"], required=True)
    ap.add_argument("--target", type=int, required=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    actor = "robotic gripper or arm" if args.family == "robot" else "human hand"
    root = Path(os.environ.get("EWJ_DATA_ROOT", "./data")) / args.dataset

    summary, dropped = [], {"duration": 0, "speed": 0, "frame": 0, "vlm": 0}
    considered = 0

    for episode in iter_source_episodes():
        if len(summary) >= args.target:
            break
        considered += 1
        raw = episode["end"] - episode["start"]
        if raw > MAX_S * max(ALLOWED_SPEEDS) or raw < MIN_S:
            dropped["duration"] += 1
            continue
        speed = choose_speed(raw)
        if speed is None:
            dropped["speed"] += 1
            continue

        task = "task_%04d" % (len(summary) + 1)
        episode_dir = root / "gt_data" / task / "episode_0001"
        video = episode_dir / "video.mp4"
        if not cut_clip(episode["video"], episode["start"], episode["end"],
                        speed, video):
            dropped["duration"] += 1
            continue

        init_frame = episode_dir / "prompt" / "init_frame.png"
        offset, ok = 0.0, False
        for candidate in (0.0,) + RETRY_OFFSETS:
            if not extract_frame(video, candidate, init_frame):
                continue
            check = vlm(FRAME_CHECK.format(family=args.family, actor=actor,
                                           label=episode["label"]),
                        init_frame.read_bytes())
            if check and check.get("manipulator_visible") and check.get("object_visible"):
                offset, ok = candidate, True
                break
        if not ok:
            shutil.rmtree(episode_dir.parent, ignore_errors=True)
            dropped["frame"] += 1
            continue

        refined = vlm(REFINE.format(family=args.family, actor=actor,
                                    label=episode["label"]),
                      init_frame.read_bytes())
        caption = vlm(CAPTION.format(prompt=(refined or {}).get("prompt", "")),
                      init_frame.read_bytes())
        if not refined or not caption:
            shutil.rmtree(episode_dir.parent, ignore_errors=True)
            dropped["vlm"] += 1
            continue

        (episode_dir / "prompt" / "prompt.txt").write_text(refined["prompt"])
        summary.append({
            "gt_path": "data/%s/gt_data/%s/episode_0001/video.mp4" % (args.dataset, task),
            "image": "data/%s/gt_data/%s/episode_0001/prompt/init_frame.png" % (args.dataset, task),
            "task_name": task,
            "episode_name": "episode_0001",
            "prompt": [refined["prompt"]],
            "prompt_prefix": "",        # fill from examples/prompt_templates.json
            "prompt_rewrite": "",       # fill from examples/prompt_templates.json
            "prefix_id": None,
            "rewrite_id": None,
            "duration": round(ffprobe_duration(video) or raw / speed, 3),
            "init_frame_offset_sec": offset,
            "action_caption": caption["action_caption"],
            "speed_factor": speed,
        })

    root.mkdir(parents=True, exist_ok=True)
    json.dump(summary, open(root / "summary.json", "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    # The delivery note wants every count with its denominator.
    print("considered %d, kept %d" % (considered, len(summary)))
    for reason, n in dropped.items():
        print("  dropped by %-9s %d" % (reason, n))
    print("seed=%d  speeds used: %s" % (
        args.seed,
        {s: sum(1 for r in summary if r["speed_factor"] == s)
         for s in ALLOWED_SPEEDS}))


if __name__ == "__main__":
    main()
