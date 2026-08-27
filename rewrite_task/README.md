# Note → reasoning synthesis

10,976 units that carry a human or pre-annotation **note** but no **reasoning**. The job is to
**write the reasoning**, using the note as source material.

**These are two different kinds of text, and the difference is the point of the task.**

| | `note` (what you are given) | `reasoning` (what you must produce) |
| --- | --- | --- |
| written for | an annotator's own record | a model to emit |
| form | terse per-axis fragments, often ungrammatical | complete, fluent sentences |
| covers | only the axes that had problems | all three axes |
| relation to the score | implicit | reads as the justification for it |

A note is raw material. The reasoning is the deliverable, and it goes straight into supervised
fine-tuning — so it has to read like a careful model answer explaining why this video earns its
score, not like a transcription of the note.

Input: [`units.jsonl`](units.jsonl) — one JSON object per line, one unit per line.
Output: `rewritten.jsonl` — `{"unit_id": ..., "reasoning": ...}` per line, same `unit_id` values.

| | count |
|---|---:|
| units | 10,976 |
| — physical adherence (`axis: "pa"`) | 5,689 |
| — instruction alignment (`axis: "ia"`) | 5,287 |
| distinct videos | 5,701 |
| notes written by a human annotator | 7,252 |
| notes from model pre-annotation | 3,724 |
| notes in Chinese | 10,930 |

---

## Input fields

| field | meaning |
| --- | --- |
| `unit_id` | `<item_id>\|<axis>` — echo this back unchanged |
| `axis` | `pa` (physical adherence) or `ia` (instruction alignment) |
| `note_zh` | the note to rewrite, usually Chinese |
| `note_source` | `human_annotator` or `model_preannotation` |
| `main_score` | the 1–5 score for this axis. **Do not change it and do not restate it in the text** |
| `sub_scores` | the three 0/1/2 per-axis verdicts — see [Silent axes](#silent-axes) |
| `video_url`, `init_frame_url`, `instruction_url` | the media, if you want to look |
| `agent_assisted` | `true` on 530 units whose note was drafted by an AI agent, not a person |

## Target form

Complete, fluent prose naming each axis in order, one to three sentences per axis, no bullet
points, no numbering, no score restated. It should be indistinguishable from the reasoning already
in the training set. This is a real example from that set:

> Agent integrity: the black robotic gripper remains mostly structurally consistent, with stable
> fingers and joints and no obvious melting or extra parts; the second gripper seen early simply
> moves out of view. Scene & object consistency: the kitchen background, toaster, carton, bottle,
> basket, and counter remain largely stable, but the bread contents in the basket are
> inconsistent — there appear to be multiple slices early, yet a single slice later. Interaction
> realism: the gripper approaches and lifts a slice in a broadly plausible way, though the grasp
> looks loose and the slice shifts without clear finger closure.

**Axis names, exactly these strings:**

| axis | order | names to use |
| --- | --- | --- |
| `pa` | 1, 2, 3 | `Agent integrity` · `Scene & object consistency` · `Interaction realism` |
| `ia` | 1, 2, 3 | `Agent match` · `Object correctness` · `Goal completion` |

**Source terms map to them like this:**

| Chinese | English |
| --- | --- |
| 机械手完整性 / 机械臂完整性 | Agent integrity |
| 背景物体一致性 | Scene & object consistency |
| 交互真实性 | Interaction realism |
| 动作主体匹配 | Agent match |
| 目标物正确 | Object correctness |
| 目标完成度 | Goal completion |

## Rules

**1. Invent no observations.** Specific claims — object names, failure modes, what moved where,
frame references — must come from `note_zh`. If the note does not say the gripper melted, do not
write that it melted.

This is not a ban on writing fluently. You may use the rubric's own vocabulary for what a verdict
*means* (a passing axis is consistent, stable, physically plausible; a violated one is not), because
that describes the grade rather than the clip. Write full sentences; just do not attach invented
specifics to them.

**2. <a name="silent-axes"></a>Silent axes come from `sub_scores`, not from imagination.** A note
usually names only the axes that had problems — on average 1.55 of 3. The target form covers all
three. For an axis the note does not mention, state the verdict its sub-score records:

| sub-score | write |
| --- | --- |
| `2` | that the axis is consistent / correct, with no visible issues |
| `1` | that there are minor problems on this axis, **without inventing what they were** |
| `0` | that this axis is clearly violated, **without inventing how** |

1,285 units have a silent axis whose sub-score is `0` or `1`. Write those in the rubric's general
language — "shows clear inconsistencies", "is only partly plausible" — and stop there. **General is
correct; specific-and-invented is not.** A reader should be able to tell that the annotator recorded
a problem without being told a fabricated detail about it.

**3. Keep the severity the note used.** 严重违反 / 严重不符 are severe; 存在问题 is a problem;
部分完成 is partial; 未完成 is not completed. Do not soften and do not sharpen.

**4. Drop annotator scaffolding.** Some notes carry frame markers (`f01`, `f05`), tick/warning
symbols (`✓`, `⚠`), or a prefix like `[AI agent Francis 代 masiyuan]`. Remove them; keep the
observation itself.

**5. English only**, and no `(PA3)`-style score verdicts in the text.

## Delivery checks

Your `rewritten.jsonl` must satisfy all of these:

```bash
# same unit_ids, no duplicates, none missing
python check_rewrite.py units.jsonl rewritten.jsonl
```

- every `unit_id` present exactly once
- no Chinese characters remain
- every one of the three axis names for that unit's axis appears
- no `(PA1)`–`(PA5)` / `(IA1)`–`(IA5)` verdicts
- no `f01`-style frame markers, no `✓`/`⚠`, no `代` prefix

Report, in the same message as the numbers: how many units you rewrote, how many you skipped and
why, and any unit where the note and its `sub_scores` contradicted each other — do not silently
pick one.
