# Note → reasoning synthesis

**Handover for an external agent.** Everything needed to do the job is in this directory. Read this
file top to bottom before starting; the rules section is the part that decides whether a delivery is
accepted.

## The job in one paragraph

Our training set labels each video on two axes — **physical adherence (PA)** and **instruction
alignment (IA)** — with a 1–5 score, three 0/1/2 sub-scores, and free text. For most rows the free
text is a finished **`reasoning`**: fluent English prose that a model can be fine-tuned to emit. For
the rows in this package it is only a **`note`**: an annotator's terse, usually Chinese shorthand,
written for their own record. **Your job is to turn each note into a reasoning.** You are not
translating and you are not summarising; you are writing the justification the note stands for.

## What is in this directory

| file | what it is |
| --- | --- |
| `README.md` | this document |
| `units.jsonl` | **10,976 units** that have a note — the main job |
| `units_no_note.jsonl` | **472 units** with no note — reasoning must be written from the video, see [Second package](#second-package) |
| `example_unit.json` | two worked units — one `pa`, one `ia` — with acceptable output |
| `final_row_example.json` | the complete SFT row your text ends up in |
| `check_rewrite.py` | the delivery gate. Your output must pass it |

A **unit** is one (video, axis) pair, so a single video can appear twice — once as `pa`, once as
`ia`. They are independent: write each from its own note and its own sub-scores.

Input: `units.jsonl`, one JSON object per line.
Output: `rewritten.jsonl`, one `{"unit_id": ..., "reasoning": ...}` per line, same `unit_id` values.

## Why note and reasoning are different kinds of text

This is the point of the task, so it is worth being explicit.

| | `note` (what you are given) | `reasoning` (what you must produce) |
| --- | --- | --- |
| written for | an annotator's own record | a model to emit |
| form | terse per-axis fragments, often ungrammatical | complete, fluent sentences |
| covers | usually only the axes that had problems | all three axes |
| relation to the score | implicit | reads as the justification for it |

A note is raw material. The reasoning is the deliverable and goes straight into supervised
fine-tuning, so it must read like a careful model answer explaining why this video earns its score —
not like a transcription of the note.

## The data

| | count |
|---|---:|
| units | 10,976 |
| — physical adherence (`axis: "pa"`) | 5,689 |
| — instruction alignment (`axis: "ia"`) | 5,287 |
| distinct videos | 5,701 |
| notes in Chinese | 10,930 |
| notes already in English (still need reshaping into the target form) | 46 |

`main_score` distribution: 1 → 852 · 2 → 3,059 · 3 → 3,854 · 4 → 2,285 · 5 → 926.

Notes come from three kinds of writer, recorded per unit in `note_source` (and in more detail in
`provenance`):

| `note_source` | units | what it means |
| --- | ---: | --- |
| `human_annotator` | 6,722 | a person wrote or edited it |
| `model_preannotation` | 3,724 | a model pre-annotated it and no person revised it |
| `ai_agent_draft` | 530 | drafted by an AI agent filling a human's slot |

**Treat all three the same way.** The note is the source of record regardless of who wrote it; you
are not being asked to judge whether it is correct.

## Input fields

| field | meaning |
| --- | --- |
| `unit_id` | `<item_id>\|<axis>` — echo back unchanged |
| `axis` | `pa` or `ia` |
| `note` | the note to rewrite |
| `note_language` | `zh` or `en` |
| `note_source` | see the table above |
| `provenance` | six-way detail of where the label came from |
| `main_score` | the 1–5 score for this axis. **Do not change it and do not restate it in the text** |
| `sub_scores` | the three 0/1/2 per-axis verdicts — see [Silent axes](#silent-axes) |
| `axes_named_explicitly` | which axes the note names by name — **a hint, not ground truth**; see below |
| `data_report_issues` | non-null on 600 units — see [Flagged units](#flagged-units) |
| `agent_assisted` | `true` where the note was AI-drafted |
| `video_url`, `init_frame_url`, `instruction_url` | the media. All three resolve without auth |
| `dataset`, `model`, `task`, `episode` | provenance of the clip |

## The prompt your text will be trained under

This matters more than anything else in this document. Each unit becomes one supervised
fine-tuning example. The reasoning you write **is the assistant turn** — it is the answer to the
prompt below, verbatim, with no post-processing. Write it so that it reads as a direct answer to
this specific prompt.

**For `axis: "pa"` — system message:**

> You are a strict, calibrated evaluator of the PHYSICAL REALISM of AI-generated embodied /
> robot-manipulation videos (a robot arm/gripper or a human hand acting on objects). You are shown
> uniformly-sampled frames of one generated video in temporal order. Judge the physics of the video
> itself. Be conservative: reserve 5 for clearly flawless physics and 1 for clearly broken physics.

**and user message:**

```text
<video>Task: Judge the PHYSICAL REALISM of this AI-generated robot / embodied-manipulation
video, from the video alone (ignore any task instruction).

Criteria (your reasoning must address each; you may also note other issues):
1. Agent integrity - the arm/gripper/hand stays structurally complete and consistent
   (no melting, fused/extra fingers, warping).
2. Scene & object consistency - background and objects stay temporally stable
   (no flicker, teleport, morphing, appear/disappear).
3. Interaction realism - contacts obey physics (grasps close and bear weight, no
   interpenetration, motion respects gravity/inertia).

Score (integer 1-5): 1 = gross violations throughout; 2 = major violations;
3 = noticeable local inconsistencies; 4 = minor issues only; 5 = no visible violation.

Reason first, then score. Output JSON only:
{"reasoning": "<assess agent integrity, scene & object consistency, and interaction realism, each with concrete visual evidence>", "physical_adherence": <1-5>}
```

**For `axis: "ia"` — system message:**

> You are a strict, calibrated evaluator of whether an AI-generated embodied-manipulation video
> correctly performs a given task instruction. You are shown the instruction and uniformly-sampled
> frames of one generated video in temporal order; the FIRST frame is the initial scene the video
> was conditioned on. Judge task execution, not raw visual quality. Be conservative: reserve 5 for
> full, correct task completion and 1 for unrelated videos.

**and user message** (`{instruction}` is the text at `instruction_url`):

```text
<image><video>Task: Judge whether this AI-generated video performs the instructed manipulation
task. The first frame is the initial scene the video was conditioned on.

Instruction: "{instruction}"

Criteria (your reasoning must address each; you may also note other issues):
1. Agent match - the task is done by the SAME manipulator shown in the first frame
   (not a different/new agent).
2. Object correctness - the manipulated object is the instruction's target object.
3. Goal completion - the instructed goal is actually achieved by the end
   (not merely approached).

Score (integer 1-5): 1 = unrelated or task not performed; 2 = major misalignment;
3 = partial completion; 4 = minor shortfalls only; 5 = full, correct completion.

Reason first, then score. Output JSON only:
{"reasoning": "<assess agent match, object correctness, and goal completion, each with concrete evidence>", "instruction_alignment": <1-5>}
```

Three consequences, and they are the reason for the rules further down:

1. **"your reasoning must address each"** — the prompt demands all three criteria. That is why an
   axis the note is silent about still has to be written (rule 2), rather than omitted.
2. **The score is emitted separately**, in its own JSON field. Your text must therefore never
   restate it, and must never carry a `(PA3)`-style verdict — that would put the same answer in the
   row twice, and the two copies can disagree.
3. **The axis names in the criteria are the anchors.** Use them verbatim; they are what makes the
   output checkable.

### What the finished row looks like

Your reasoning is dropped into the assistant turn and nothing else changes.
[`final_row_example.json`](final_row_example.json) is the complete training row built from the `pa`
worked example:

```json
{
  "messages": [
    {"role": "system",    "content": "You are a strict, calibrated evaluator of the PHYSICAL REALISM ..."},
    {"role": "user",      "content": "<video>Task: Judge the PHYSICAL REALISM of this AI-generated ..."},
    {"role": "assistant", "content": "{\"reasoning\": \"Agent integrity: the arm and gripper stay ...\", \"physical_adherence\": 3}"}
  ],
  "videos": ["https://huggingface.co/datasets/.../task_0012_episode_0001.mp4"]
}
```

The assistant turn is a **JSON string with exactly two keys**. You supply `reasoning`; the score field
is filled from our data. That is the whole reason your text must not contain the score — it is already
in the row, once.


## Target form

Complete, fluent prose naming each axis in order, one to three sentences per axis, no bullet points,
no numbering, no score restated. It should be indistinguishable from the reasoning already in the
training set. This is a real example from that set:

> Agent integrity: the black robotic gripper remains mostly structurally consistent, with stable
> fingers and joints and no obvious melting or extra parts; the second gripper seen early simply
> moves out of view. Scene & object consistency: the kitchen background, toaster, carton, bottle,
> basket, and counter remain largely stable, but the bread contents in the basket are
> inconsistent — there appear to be multiple slices early, yet a single slice later. Interaction
> realism: the gripper approaches and lifts a slice in a broadly plausible way, though the grasp
> looks loose and the slice shifts without clear finger closure.

**Length: write what the note supports and stop.** One clause per fact, no meta-commentary
("this is where it breaks down"), no closing summary, no restating the score. The worked examples in
`example_unit.json` run 587 characters (`pa`) and 495 (`ia`).

For reference, the reasoning already in the training set is longer — `pa` median 1,044 characters,
`ia` 669. **Do not pad to match it.** Those rows were written from the video, which supports more
observations; yours are written from a short note, which bounds what can honestly be said. Reaching
1,044 characters from a two-line note would require exactly the invention rule 1 forbids.

**Axis names, exactly these strings, in this order:**

| axis | names to use |
| --- | --- |
| `pa` | `Agent integrity` · `Scene & object consistency` · `Interaction realism` |
| `ia` | `Agent match` · `Object correctness` · `Goal completion` |

**Source terms map to them like this.** Notes are inconsistent in wording; these are the common
forms, not an exhaustive list:

| Chinese | English |
| --- | --- |
| 机械手完整性 / 机械臂完整性 / 主体完整性 | Agent integrity |
| 背景物体一致性 / 场景一致性 | Scene & object consistency |
| 交互真实性 / 交互合理性 | Interaction realism |
| 动作主体匹配 / 主体匹配 | Agent match |
| 目标物正确 / 物体正确 | Object correctness |
| 目标完成度 / 任务完成度 | Goal completion |

Severity vocabulary, which you must preserve (rule 3):

| Chinese | strength |
| --- | --- |
| 严重违反 / 严重不符 / 严重形变 | severe — the axis is clearly violated |
| 存在问题 / 轻微 / 部分不符 | a problem, but not severe |
| 部分完成 | partially achieved |
| 未完成 / 未操作 | not achieved at all |
| 无明显问题 / 一致 | no visible issue |

## Rules

**1. Invent no observations.** Specific claims — object names, failure modes, what moved where,
frame references — must come from the `note`. If the note does not say the gripper melted, do not
write that it melted.

This is not a ban on writing fluently. You may use the rubric's own vocabulary for what a verdict
*means* (a passing axis is consistent, stable, physically plausible; a violated one is not), because
that describes the grade rather than the clip. Write full sentences; just do not attach invented
specifics to them.

**2. <a name="silent-axes"></a>Silent axes come from `sub_scores`, not from imagination.** A note
usually names only the axes that had problems — 1.53 of 3 on average, and on 2,323 units it names
none of them. The target form covers all three. For an axis the note does not discuss, state the
verdict its sub-score records:

| sub-score | write |
| --- | --- |
| `2` | that the axis is consistent / correct, with no visible issues |
| `1` | that there are minor problems on this axis, **without inventing what they were** |
| `0` | that this axis is clearly violated, **without inventing how** |

About 2,154 units have a silent axis whose sub-score is `0` or `1`. Write those in the rubric's
general language — "shows clear inconsistencies", "is only partly plausible" — and stop there.
**General is correct; specific-and-invented is not.** A reader should be able to tell that the
annotator recorded a problem without being told a fabricated detail about it.

⚠️ `axes_named_explicitly` is computed by matching the axis names above as literal strings. Notes
written free-form often discuss an axis without naming it, and those will not show up in the field.
**Read the note; use the field only as a hint.** Where the note plainly discusses an axis, that is
the source for it even if the field does not list it.

**3. Keep the severity the note used.** See the severity table. Do not soften and do not sharpen.
This is the single most common way a rewrite goes wrong: a note saying 严重违反 becomes "some minor
inconsistencies", and the text no longer justifies the score.

**4. Drop annotator scaffolding.** Some notes carry frame markers (`f01`, `f05`), tick/warning
symbols (`✓`, `⚠`), or a prefix like `[AI agent Francis 代 masiyuan]`. Remove them; keep the
observation itself.

**5. English only**, and no `(PA3)`-style score verdicts in the text.

## <a name="flagged-units"></a>Flagged units — read before you start

600 units carry a `data_report_issues` value, meaning an annotator reported a problem with the clip
itself rather than with the generated video:

| issue | units | what it means |
| --- | ---: | --- |
| `instruction_init_mismatch` | 498 | the written instruction does not match the initial frame |
| `init_no_agent` | 87 | no robot visible in the initial frame |
| `other` | 18 | free-form report |
| `video_static_black` | 6 | the video is static or black |
| `video_unplayable` | 5 | the file does not decode |

**Rewrite them anyway, from the note, exactly like any other unit** — the label and the note are
still what we are training on. Do **not** try to explain or mention the data problem in the
reasoning. Just be aware that on these units the media may not support the note, so if you look at
the video and it seems to disagree, **follow the note**.

## <a name="second-package"></a>Second package: `units_no_note.jsonl` (472 units)

**These need reasoning written for them too.** They carry a score and sub-scores but no note — 437
`ia` and 35 `pa`. Fields are identical to `units.jsonl` except that `note` is absent. Deliver them
in the same `rewritten.jsonl` format, as `rewritten_no_note.jsonl`.

The target form, the axis names and rules 3–5 are unchanged. What changes is **where the
observations come from**: with no note, the source is the video itself.

1. **Watch the clip** at `video_url`, and for an `ia` unit read `instruction_url` and look at
   `init_frame_url` — the instruction is what the video is being judged against.
2. **Write what you actually see**, per axis, in the target form. Rule 1 still holds and is now
   about the video: describe what is in the clip, not what the score implies must be there.
3. **The scores are fixed.** `main_score` and `sub_scores` are given and are not yours to change.
   Where an axis's sub-score records a problem, look for that problem in the video and describe it.
   If after watching you genuinely cannot see what the sub-score refers to, write that axis in the
   rubric's general language rather than inventing a specific failure — same as rule 2.

**If you cannot process video at all, say so before you start** rather than filling these from the
sub-scores alone — that would produce 472 rows of fluent invention, which is worse for us than 472
rows we know are still outstanding.

## Delivery

```bash
python check_rewrite.py units.jsonl          rewritten.jsonl           # exit 0 = accepted
python check_rewrite.py units_no_note.jsonl  rewritten_no_note.jsonl   # same gate, second package
```

The gate enforces:

- every `unit_id` present exactly once, none unknown, none missing
- non-empty reasoning, and long enough to plausibly cover three axes
- no Chinese characters remain
- all three axis names for that unit's axis appear
- no `(PA1)`–`(PA5)` / `(IA1)`–`(IA5)` verdicts
- no `f01`-style frame markers, no `✓`/`⚠`, no `代` prefix

**A passing gate is necessary, not sufficient** — it checks form, not faithfulness. Rules 1 and 3
are what a human will spot-check.

## What to report back

In the same message as the delivery:

1. how many units you rewrote, and how many you skipped, with the reason
2. **any unit where the note and its `sub_scores` contradict each other** — e.g. the note says
   严重违反 but the sub-score is `2`. Do not silently pick one; list them and say which you followed
3. for `units_no_note.jsonl`: confirm you watched the clips, and list any unit where you could not
   see what a sub-score refers to
4. anything the rules did not cover that you had to decide for yourself

Item 4 matters more than it sounds. If you had to invent a convention, we need to know, because
10,976 rows written under an undocumented convention are hard to audit later.
