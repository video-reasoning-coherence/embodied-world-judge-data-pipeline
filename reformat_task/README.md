# Reformat the training reasoning to one uniform target

Every reasoning in the training set already exists. **This task rewrites none of the judgements — it
puts them all in one shape.** Right now the set is three different layouts at three different
lengths, and that inconsistency is doing measurable harm.

Input: [`units_22568.jsonl`](units_22568.jsonl) — one JSON object per line, one per **(video, axis)**
pair, each carrying its existing text in `current_reasoning`.
Output: `reformatted.jsonl` — `{"unit_id": ..., "reasoning": ...}` per line, same `unit_id` values.

### You need only this one file

**`units_22568.jsonl` already contains both halves of the training set.** There is nothing to fetch
or join. The `batch` field says which half a row came from:

| `batch` | rows | where it came from | typical shape |
| --- | ---: | --- | --- |
| `rewritten_v3` | 10,976 | already published as `final/reasoning_v3.jsonl` on the dataset | three lines, too long |
| `original_reasoning` | 11,592 | the `pa_reasoning` / `ia_reasoning` columns of `final/train.jsonl` | one paragraph, three lines, four lines, or numbered |

```bash
wc -l units_22568.jsonl                                            # 22568
jq -c 'select(.batch=="rewritten_v3")'      units_22568.jsonl | wc -l   # 10976
jq -c 'select(.batch=="original_reasoning")' units_22568.jsonl | wc -l   # 11592
```

**Process every row the same way.** The `batch` value is provenance, not an instruction — the target
is identical for both, and the whole point is that the two halves stop being distinguishable. Deliver
one `reformatted.jsonl` covering all 22,568.

> ### The target is not "make one batch look like the other"
>
> **Neither batch already meets it.** `rewritten_v3` has the right layout but is roughly twice the
> length it should be; `original_reasoning` is wrong on both counts.
>
> | | layout | length (pa / ia median) | already in the 250–400 band |
> | --- | --- | --- | ---: |
> | `rewritten_v3` | three lines ✅ | 748 / 649 ❌ | 825 of 10,976 — 7.5% |
> | `original_reasoning` | 1 / 3 / 4 lines, 3,909 numbered ❌ | 1,035 / 669 ❌ | 2 of 11,592 — 0.0% |
> | **target** | **three lines** | **250–400** | — |
>
> So `rewritten_v3` keeps its layout and gets compressed; `original_reasoning` gets both. Converting
> the second batch into the first batch's current form would leave the length untouched — and the
> length is the defect this task exists to remove.

## Why this is worth doing

**1. Three layouts are mixed together.**

| current shape | rows |
| --- | ---: |
| a single flowing paragraph | 8,379 |
| three lines, one per criterion | 12,975 |
| four lines | 1,213 |
| *of the above*, numbered as `1) Agent integrity: …` | 3,909 |

One row still contains Chinese. Nothing else carries a score, a `(PAn)` marker, markdown or a
reference to the annotation process — those classes are already clean and must stay clean.

**2. Length currently tells the model the score.**

| main score | rows | median characters |
|---:|---:|---:|
| 1 | 1,578 | 793 |
| 2 | 6,496 | 767 |
| 3 | 7,283 | 779 |
| 4 | 5,172 | 779 |
| **5** | **2,039** | **537** |

Score 5 is the only class that is visibly shorter, because the units where nothing went wrong were
written separately and more briefly. A model trained on this can learn *short answer → score 5*, and
since it emits the reasoning before the score, a short generation drags the score upward — in the
class it already predicts least often. **Making every row the same length band removes that signal.**
That is the point of the task; uniformity matters more than any particular length.

## The target

**Exactly three lines, one per criterion, each opening with the criterion's name, 250–400
characters in total.**

```
Agent match: The right gripper performs the task throughout.
Object correctness: It takes the slice of toast from the beige toaster.
Goal completion: The toast is lifted clear of the toaster and set down on the blue plate.
```

| `axis` | line 1 | line 2 | line 3 |
| --- | --- | --- | --- |
| `pa` | `Agent integrity:` | `Scene & object consistency:` | `Interaction realism:` |
| `ia` | `Agent match:` | `Object correctness:` | `Goal completion:` |

The names are the judge prompt's own criteria, copied exactly. A short verdict phrase may sit between
the name and the colon (`Interaction realism severely violated:`) but the line must open with the name.

## What to do, by shape

**Already three lines and inside the band** — leave it alone. Copy it through unchanged.

**Three lines but too long** (most of them) — compress. Keep the concrete observations: which
manipulator acts, which object is handled, what goes wrong or what is achieved. Cut the connective
padding — clauses like *"so the instructed transfer is achieved"*, *"with no other agent
intervening"*, *"which indicates that the interaction is not physically plausible"* restate the
verdict instead of adding evidence.

**One paragraph** — split it at each criterion name, then compress the same way.

**Four lines** — the extra line is usually an overall verdict or a summary. Delete it and fold
anything factual into the criterion it belongs to.

**Numbered** (`1) Agent integrity: …`) — drop the `1) ` `2) ` `3) ` prefixes so each line opens with
the criterion name itself. 3,909 rows look like this.

## Rules

1. **Do not change any judgement.** If the current text says the grasp fails, the new text says the
   grasp fails. You are shortening and re-laying-out, not re-deciding. Never look at the video and
   form a different opinion — that is a different task.
2. **Every line must agree with its `sub_scores` entry** — `2` holds, `1` a minor problem, `0`
   clearly violated. The current text already does; keep it that way while compressing. This is the
   one error class the checker cannot catch, so it needs your attention rather than the script's.
3. **Do not drop a criterion to save space.** All three lines stay, even when one has nothing to
   report; a criterion that holds needs one clause.
4. **Cut evidence last.** Remove restatement, hedging and summary first. If a line is still too long
   with two concrete observations, keep the more specific one.
5. **Never write** a number, a score, `sub-score`, `(PA3)`, a `description:` header, markdown, a
   blank line, a fourth line, Chinese, or any reference to an annotator, a note, or how the text was
   produced. At inference the model sees a video and a prompt and nothing else.
6. `main_score` and `sub_scores` are given. You never change them.

## Fields

| field | meaning |
| --- | --- |
| `unit_id` | `<item_id>\|<axis>` — echo back unchanged |
| `axis` | `pa` or `ia`, decides which three criteria apply |
| `current_reasoning` | **the text to reformat** |
| `main_score` | the 1–5 score for this axis; never appears in the prose |
| `sub_scores` | the three 0/1/2 verdicts your three lines must agree with |
| `batch` | `rewritten_v3` (already three lines, mostly needs compressing) or `original_reasoning` (mixed shapes) |
| `video_url`, `init_frame_url`, `instruction_url` | available, but this task does not need them |

## Delivery

```bash
python check_reformat.py units_22568.jsonl reformatted.jsonl
```

It enforces every rule above that a script can check, and prints the median length per score with a
**spread limit of 80 characters** — if the scores still separate by more than that, length is still
carrying the label and the delivery is not finished.

Report: how many rows you copied through unchanged, how many you compressed, and any unit where the
current text contradicts its own `sub_scores` — list those rather than quietly fixing them, since
that is a judgement change and belongs to us.
