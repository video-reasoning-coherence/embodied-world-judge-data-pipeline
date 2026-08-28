# The 965 units that could not be assembled

`units_965.jsonl` holds the units left over after
[`assemble_from_phase1.py`](../assemble_from_phase1.py) converted every usable phase-1 output.
Fields are exactly those of [`units.jsonl`](../units.jsonl).

**These are the most valuable units in the set, not the leftovers.** Read the next section before
deciding how much care to give them.

## Why they matter more than their count suggests

They are not a random 9%. They sit almost entirely at the top of the scale:

| main score | units in total | in this file | share of that score |
|---:|---:|---:|---:|
| 1 | 852 | 30 | 3.5% |
| 2 | 3,059 | 87 | 2.8% |
| 3 | 3,854 | 159 | 4.1% |
| 4 | 2,285 | 115 | 5.0% |
| **5** | **926** | **574** | **62.0%** |

`ia` is hit hardest: 500 of its 708 score-5 units, or 71%. Score 5 is already the rarest label in
the training set, and the trained judge under-predicts it — the training split has 3.0% at PA=5
against 16.5% in the benchmark. **Dropping this file would make that gap substantially worse.**

## Why the generators failed on them

These units carry an all-clear note. The most common values are 「指令达成」, 「指令完全符合」,
「任务完成」, 「没问题」, 「正确」 — a median of **6 characters**, against 73 across the whole set.
63% are 10 characters or shorter, and 604 of the 965 have all three sub-scores at `2`.

With no observed problem to relay, phase 1 had nothing to convert: its outputs for these units
padded with commentary, drifted off the three-criterion structure, or referred to the annotation
itself. All of those are rejected, so the unit came through as a gap rather than as bad text.

## What to write

**The note will not carry you here — the source is the video plus the sub-scores.**

1. Watch the clip at `video_url`; for an `ia` unit also read `instruction_url` and look at
   `init_frame_url`.
2. Write three lines in the standard form (see [`../README.md`](../README.md)), one per criterion,
   each opening with its criterion name.
3. For an axis whose sub-score is `2` — which is most of them — say what is *right*, concretely:
   which manipulator acts, which objects are handled, what the outcome is. `Agent match: the same
   two grippers shown in the initial frame carry out the task, with no other agent appearing.`
4. Do **not** manufacture faults to make the text look balanced. A clean axis reads clean. These
   units are mostly score 5 precisely because nothing went wrong, and inventing minor problems here
   is how a judge learns to be harsher than the humans it is imitating.
5. Where an axis does have a `0` or `1` — 361 units have at least one — describe that problem from
   the video. If you cannot see what the sub-score refers to, use the rubric's general language
   rather than inventing a specific failure.

The scores are given and are not yours to change.

## Delivery

Same shape and same gate as the main task:

```bash
python ../check_rewrite.py units_965.jsonl rewritten_965.jsonl
```

Report how many you wrote, how many you could not, and any unit where the video and the sub-scores
disagree — list those rather than resolving them silently.
