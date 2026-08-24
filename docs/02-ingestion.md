# 2. Source pipeline — corpus → clip → prompt

This is the upstream half: **which corpora, how a clip is cut, and how each of the
three prompt fields is produced.** The generation stage is separate (`docs/03`).

## 2.1 Which datasets

| dataset | episodes | kind | prefix family |
|---|---:|---|---|
| agibot_world | 200 | robot | robot |
| droid | 199 | robot | robot |
| robotwin | 198 | robot (sim) | robot |
| gr1_inlab | 171 | robot | robot |
| egodex_human | 150 | human egocentric | human |
| open_x_embodiment | 142 | robot | robot |
| libero | 100 | robot (sim) | robot |
| egoscaler_human | 100 | human egocentric | human |
| epickitchens_human | 60 | human egocentric | human |
| dreamdojo_hv | 47 | robot | robot |
| egodex | 24 | human egocentric | human |
| **total** | **1,391** | | |

The robot/human split matters: it selects which prefix and rewrite template
family is used (§2.3), and it changes the wording of the refinement prompt
("gripper" vs "hand").

## 2.2 Clip selection and cutting

Worked example — `examples/ingest_egodex_human.py`, source
`yixuan-tan/EgoDex-LeRobot-v3.0`:

1. Enumerate episodes from the LeRobot parquet shards; each row carries
   `from_timestamp` / `to_timestamp` for its segment.
2. **Keep only segments of 5–10 s** (`if 5.0 <= dur <= 10.0`). Too short and there
   is no action to judge; too long and the generators cannot cover it.
3. Cut with `ffmpeg -ss <from> -i <src> -t <duration>` → `video.mp4`.
4. Extract `init_frame.png` at **t = 0** of the cut clip
   (`ffmpeg -ss <t> -frames:v 1`).
5. Record the real duration with `ffprobe` — **not** the requested duration, and
   write it plus `init_frame_offset_sec` into `summary.json`.
6. `random.seed(42)` and a fixed `TARGET_TOTAL`, so a re-run reproduces the batch.

### The conditioning-frame filter

The init frame is what every generator is conditioned on, so a bad frame poisons
every video made from it. For the human datasets a VLM is asked one strict
question:

> Is at least one HUMAN HAND clearly visible in this image (egocentric
> first-person view)? STRICT: needs recognizable fingers/palm; just a wrist or
> sleeve doesn't count.

If the answer is no, the pipeline **retries at t = 0.3, 0.7, 1.2, 1.8 s** and uses
the first frame that passes; if none passes the episode is dropped. Report how
many episodes each filter dropped, and out of what denominator.

## 2.3 The three prompt fields

Every record carries `prompt`, `prompt_prefix` and `prompt_rewrite`. They are
produced differently and must not be conflated.

### `prompt` — the refined instruction

Starts from the source corpus's own task label, then is **re-grounded against the
init frame by a VLM** into a one-line imperative:

> Write a refined ONE-LINE imperative task instruction grounded in this frame:
> 1. Imperative form, start with verb
> 2. Name SPECIFIC visible objects (color/shape) and target locations
> 3. Use "hand" or "left/right hand" (NOT gripper — this is human)
> 4. NO meta-commentary, NO scene words ("in a kitchen") unless verifiable
> 5. Real task command not description

Corpus-specific recovery was sometimes needed: `libero` prompts were re-derived
from the LIBERO benchmark package by mapping each entry to its true `task_index`;
`gr1_inlab` init frames were VLM-classified into one of 10 humanized task texts
because the source labels were unusable. The pre-refinement text was preserved as
`prompt_original` where it existed.

### `prompt_prefix` — a fixed stability preamble

Chosen from `visualizations/prompt_templates.json` in the main repo:
**5 `robot_prefixes` and 5 `human_prefixes`**; `prefix_id` records which one.
Example (robot):

> In a fixed robotic workspace, a rigid and physically consistent embodied
> robotic arm with high stability and no deformation proceeds to

Example (human):

> In a first-person egocentric video, a real human hand starts to

It is prepended at generation time. **`prompt` itself is never overwritten.**

### `prompt_rewrite` — an image-grounded LLM rephrasing

Produced by a **multimodal** call (init frame + instruction), using one of
5 `robot_rewrite_templates` / 5 `human_rewrite_templates`; `rewrite_id` records
which. The call is wrapped as:

```text
wrapper_pre:  "The attached image is the first frame of a {kind} manipulation video."
<one rewrite template>
wrapper_suf:  "If the instruction conflicts with the image, prioritize the image.
               Output ONLY the rewritten prompt."
Instruction:  <prompt>
```

Template family version: **v3 (2026-06-16) — action-focused, ≤128 tokens,
object-locked, completion-state, minimal scene.**

⭐ Because `prompt_rewrite` is image-grounded, it does **not** need regenerating
when `prompt` is later edited — it was derived from the frame, not from the text.

### Why two conditions

Each source episode is generated twice per model — once from `prompt_prefix` and
once from `prompt_rewrite` — which is why every generated `item_id` carries a
`prefix` or `rewrite` marker.

## 2.4 ⚠️ What is NOT here

**Only 3 of the 11 datasets have a recoverable ingest script** (`examples/`).
The other eight — `agibot_world`, `droid`, `robotwin`, `gr1_inlab`,
`open_x_embodiment`, `libero`, `dreamdojo_hv`, `egodex` — were ingested earlier
and their **selection** code is not in this repository. The prompt pipeline in
§2.3 applies to all of them (the templates and refinement are shared), but the
episode-selection logic is not documented and **should not be assumed
reproducible**. Treat a new batch as a fresh ingestion against the contract.
