#!/usr/bin/env python3
"""Build the LLaMA-Factory SFT files from the units and their reasoning.

Emits two files, one per axis, because the benchmark evaluates the axes separately and the physical
prompt is explicit that the instruction must be ignored -- so the instruction cannot be in the
input. Training has to match evaluation.

  embodied_world_judge_sft_pa.json   <video> only, no init frame
  embodied_world_judge_sft_ia.json   <image><video> plus the instruction text

The prompts are the judge's own, verbatim, including the em dash in the criteria lines. The judge
and the training data must be the same byte string or the model is trained on one prompt and scored
on another.

Usage:
  python make_sft.py --units units.jsonl --reasoning reasoning.jsonl --out-dir sft/
"""
import argparse
import json
import os
import urllib.request

PA_SYSTEM = (
    "You are a strict, calibrated evaluator of the PHYSICAL REALISM of AI-generated "
    "embodied / robot-manipulation videos (a robot arm/gripper or a human hand acting "
    "on objects). You are shown uniformly-sampled frames of one generated video in "
    "temporal order. Judge the physics of the video itself. Be conservative: reserve 5 "
    "for clearly flawless physics and 1 for clearly broken physics."
)
PA_PROMPT = """\
<video>Task: Judge the PHYSICAL REALISM of this AI-generated robot / embodied-manipulation
video, from the video alone (ignore any task instruction).

Criteria (your reasoning must address each; you may also note other issues):
1. Agent integrity — the arm/gripper/hand stays structurally complete and consistent
   (no melting, fused/extra fingers, warping).
2. Scene & object consistency — background and objects stay temporally stable
   (no flicker, teleport, morphing, appear/disappear).
3. Interaction realism — contacts obey physics (grasps close and bear weight, no
   interpenetration, motion respects gravity/inertia).

Score (integer 1-5): 1 = gross violations throughout; 2 = major violations;
3 = noticeable local inconsistencies; 4 = minor issues only; 5 = no visible violation.

Reason first, then score. Output JSON only:
{"reasoning": "<assess agent integrity, scene & object consistency, and interaction realism, each with concrete visual evidence>", "physical_adherence": <1-5>}
"""

IA_SYSTEM = (
    "You are a strict, calibrated evaluator of whether an AI-generated "
    "embodied-manipulation video correctly performs a given task instruction. You "
    "are shown the instruction and uniformly-sampled frames of one generated video "
    "in temporal order; the FIRST frame is the initial scene the video was "
    "conditioned on. Judge task execution, not raw visual quality. Be conservative: "
    "reserve 5 for full, correct task completion and 1 for unrelated videos."
)
IA_PROMPT = """\
<image><video>Task: Judge whether this AI-generated video performs the instructed manipulation
task. The first frame is the initial scene the video was conditioned on.

Instruction: "{instruction}"

Criteria (your reasoning must address each; you may also note other issues):
1. Agent match — the task is done by the SAME manipulator shown in the first frame
   (not a different/new agent).
2. Object correctness — the manipulated object is the instruction's target object.
3. Goal completion — the instructed goal is actually achieved by the end
   (not merely approached).

Score (integer 1-5): 1 = unrelated or task not performed; 2 = major misalignment;
3 = partial completion; 4 = minor shortfalls only; 5 = full, correct completion.

Reason first, then score. Output JSON only:
{{"reasoning": "<assess agent match, object correctness, and goal completion, each with concrete evidence>", "instruction_alignment": <1-5>}}
"""


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def fetch_instruction(url, cache):
    if url in cache:
        return cache[url]
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            text = r.read().decode("utf-8").strip()
    except Exception as exc:
        raise SystemExit("could not fetch %s: %r" % (url, exc))
    cache[url] = text
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--units", required=True)
    ap.add_argument("--reasoning", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    units = {u["unit_id"]: u for u in load_jsonl(args.units)}
    text = {r["unit_id"]: r["reasoning"] for r in load_jsonl(args.reasoning)}

    missing = set(units) - set(text)
    if missing:
        print("WARNING: %d units have no reasoning and are skipped" % len(missing))

    cache, out = {}, {"pa": [], "ia": []}
    for uid, reasoning in text.items():
        u = units.get(uid)
        if u is None:
            raise SystemExit("unknown unit_id in reasoning file: %s" % uid)
        if u["axis"] == "pa":
            answer = {"reasoning": reasoning, "physical_adherence": u["main_score"]}
            row = {"messages": [
                {"role": "system", "content": PA_SYSTEM},
                {"role": "user", "content": PA_PROMPT},
                {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)}],
                "videos": [u["video_url"]]}
        else:
            instruction = fetch_instruction(u["instruction_url"], cache)
            answer = {"reasoning": reasoning, "instruction_alignment": u["main_score"]}
            row = {"messages": [
                {"role": "system", "content": IA_SYSTEM},
                {"role": "user", "content": IA_PROMPT.format(instruction=instruction)},
                {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)}],
                "videos": [u["video_url"]], "images": [u["init_frame_url"]]}
        out[u["axis"]].append(row)

    os.makedirs(args.out_dir, exist_ok=True)
    for axis, rows in out.items():
        path = os.path.join(args.out_dir, "embodied_world_judge_sft_%s.json" % axis)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)
        print("%-6s %5d rows -> %s" % (axis, len(rows), path))


if __name__ == "__main__":
    main()
