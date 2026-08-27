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
| `units_no_note.jsonl` | **472 units** with no note at all — see [Second package](#second-package) |
| `example_unit.json` | one input unit and an acceptable output for it |
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

These have a score and sub-scores but **no note at all** — 437 `ia` and 35 `pa`. There is no text to
rewrite, so the reasoning has to be written from the sub-scores plus **watching the video**. Fields
are identical except that `note` is absent.

**Do this package only if you can actually watch the videos.** If you cannot, deliver
`units.jsonl` and say so; do not fill these in from the sub-scores alone, because rule 1 would have
nothing to stand on and the result would be 472 rows of fluent invention. Returning them untouched
is the correct outcome in that case.

## Delivery

```bash
python check_rewrite.py units.jsonl rewritten.jsonl     # exit 0 = accepted
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
3. whether you did `units_no_note.jsonl`, and if so how you sourced the observations
4. anything the rules did not cover that you had to decide for yourself

Item 4 matters more than it sounds. If you had to invent a convention, we need to know, because
10,976 rows written under an undocumented convention are hard to audit later.
