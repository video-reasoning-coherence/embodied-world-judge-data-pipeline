# Revision request

The first delivery was reviewed. **Nothing is wrong with the scores** — every `main_score`,
every `sub_scores` object and all fifteen other fields came back byte-identical, across all
10,976 units. The problem is the prose, and it is one rule broken repeatedly rather than poor
judgement.

`needs_fix.jsonl` lists every affected unit: `unit_id`, `axis`, `defects` (the tags below) and
`evidence` (the offending span, so you do not have to search for it).

**No video is needed for this pass.** Every defect is a property of the text you already wrote.
You are removing scaffolding, not gathering new observations.

## What has to change

### 1. No numbers in the prose — 6,353 units

The score is already in the row, in its own JSON field. Writing it again puts two answers in one
row, and when they disagree the target teaches the model to contradict itself. Remove all of these:

| found | fix |
| --- | --- |
| `Agent match (2): ...` | `Agent match: ...` |
| `..., supporting an agent consistency score of 2.` | delete the clause; keep the observation |
| `..., so the goal completion score is 0.` | delete the clause |
| `These issues justify low sub-scores across ...` | rewrite without the word `sub-score` |
| `(IA2)` | delete |
| `This video earns an overall IA score of 2, with sub-scores of 0 for agent match, ...` | delete the whole sentence |
| `..., so the overall goal is not completed (goal_completed=1).` | `..., so the overall goal is not completed.` |
| `..., supporting the main score of 4.` | delete the clause |

Neither `main score`, nor `overall PA/IA score`, nor a field name with a number attached
(`goal_completed=1`) may appear either. The word **`sub-score` must not appear at all**. Sub-scores are not part of this target and never
have been — they are inputs you use to decide *what* to say about a silent axis, not something to
report.

### 2. Do not refer to anything the model cannot see — 668 units

At inference there is a video and a prompt. There is no annotator, no note, no other candidate
generations, no consensus. These all have to go:

```
"..., matching the annotator note"
"though some inputs note minor visual/warping artifacts"
"despite occasional minor visual distortions reported by a couple of candidates"
"aligned with the following consensus observations:"
```

Write the observation directly and drop the attribution.

### 3. Use the axis names exactly — 6,442 units

`Scene and object consistency` was written where the spec says `Scene & object consistency`, and
many rows use lower case. The exact strings, capitalised as shown:

| axis | names |
| --- | --- |
| `pa` | `Agent integrity` · `Scene & object consistency` · `Interaction realism` |
| `ia` | `Agent match` · `Object correctness` · `Goal completion` |

This one is mechanical, and we can normalise it on our side if you prefer — say so and we will.

### 4. Cover all three criteria — 591 units

591 units genuinely address only two of the three, most often omitting `Goal completion`. The
prompt says *"your reasoning must address each"*. For an axis with nothing to report, state its
verdict from the sub-score in general language, inventing no specifics.

### 5. English only — 35 units

35 units still contain Chinese.

### 6. The 85 you did not write

85 units came back with `reasoning_source: "original"` and no `reasoning` field at all (48 `pa`,
37 `ia`). They all have a note. Please write them, or say what blocked them.

## Before you deliver again

`check_rewrite.py` now enforces every rule above, including the ones it missed the first time —
numbers in prose, references to the annotator or to your own pipeline, and axis names in the wrong
form. Run it and fix everything it reports:

```bash
python check_rewrite.py units.jsonl delivery/rewritten.jsonl
```

## Please regenerate rather than patch

We tried repairing this with text substitution and it does not work. Deleting the score clause
leaves the sentence broken more often than not:

```
before  This video earns an overall IA score of 1, with sub-scores of 0 for agent match, ...
after   This videor agent match, 0 for object correctness, ...

before  ..., so there are no obvious issues, corresponding to a sub-score of 2.
after   ..., so there are no obvious issues, corresponding to a.

before  this warrants an interaction realism score of 1 and an overall PA score of 2.
after   thisof 2.
```

Only about **6% of the affected units have the score in a trailing clause that can be removed
safely**. In the other 94% the number is load-bearing inside the sentence, so the sentence has to
be written again. That is why we are asking for a regeneration and not sending you a patch list.

## One suggestion about how you generate

The defect rate is not uniform across the models you used:

| source | units | states a score in prose |
| --- | ---: | ---: |
| `seed2.1-lite` | 4,177 | **98–99%** |
| `gpt-5.5` | 5,568 | 28–32% |
| `gpt-5.2` | 1,146 | 33–35% |

The consensus selected `seed2.1-lite`'s text for 3,631 units, and that source breaks rule 1 almost
every time. **Voting across models optimises for agreement about the video; it is blind to whether
the output obeys the format.** Running `check_rewrite.py` on each candidate and regenerating the
failures would have caught all of this, and costs less than an N-way vote.
