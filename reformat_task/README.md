# Reformat the training reasoning — three batches, text only

Every reasoning in the training set already exists. **This task rewrites none of the judgements — it
brings them all to one shape.** No video is needed: the observations are already written down, and
the work is deleting restatement, not re-observing.

**Read [`SFT_FORMAT.md`](SFT_FORMAT.md) first.** It defines the target and why each rule exists.
Everything below is about which rows need what.

## The three batches

They are split into separate files so they can be worked independently. **The target is identical
for all three** — they differ only in how far from it they start.

| file | rows | already in target shape | what it needs |
| --- | ---: | ---: | --- |
| [`batch_A_ready.jsonl`](batch_A_ready.jsonl) | 965 | 951 (98.5%) | **nothing — copy through** |
| [`batch_B_compress.jsonl`](batch_B_compress.jsonl) | 10,011 | 13 (0.1%) | **compress only** — layout is already right |
| [`batch_C_relayout.jsonl`](batch_C_relayout.jsonl) | 11,592 | 65 (0.6%) | **relayout and compress** |

```
                     current length         current layout
batch A    pa  402 · ia  300  ✅        three lines, 100%
batch B    pa  752 · ia  673  ❌        three lines, 100%
batch C    pa 1035 · ia  673  ❌        three lines only 0.3%
```

Each row carries its text in `current_reasoning`, plus `axis`, `main_score` and `sub_scores`.
Output for each batch: `{"unit_id": ..., "reasoning": ...}` per line, same `unit_id` values.

### batch A — 965 rows, nothing to do

These were written to the target spec already. **Copy `current_reasoning` through unchanged.** They
are included so the delivery is complete and so the checker can measure length across the whole set;
14 of them sit just outside the band — the checker names them and they should be trimmed to fit; nothing else changes.

They are also the best examples of the target. Read a few before starting on B or C.

### batch B — 10,011 rows, compress only

Three lines with the right names already; every one is too long (pa 752 / ia 673 against a target of
about 420 / 300). Do not re-lay-out and do not re-judge. Cut:

- clauses that restate the verdict — *"so the instructed transfer is achieved"*, *"which indicates
  the interaction is not physically plausible"*, *"making the object persistence unreliable"*
- second sentences that repeat the first in other words
- *"with no other agent intervening"* and similar, where the criterion simply holds

```
before (349 chars, sub_score 2)
Agent integrity is generally stable: both robotic arms maintain coherent shapes, proportions,
gripper structure, and attachment points throughout the sequence, with no obvious limb duplication
or deformation. Their motions are plausible in broad kinematic terms, and the grippers remain
visually consistent as they approach, lift, and place the items.

after
Agent integrity: Both arms and grippers keep coherent shape and attachment throughout, with no
duplication or deformation.
```

### batch C — 11,592 rows, relayout and compress

The most work. Current shapes:

| shape | rows |
| --- | ---: |
| one flowing paragraph | 8,379 |
| three lines | 1,999 |
| four lines | 1,213 |
| *of the above*, numbered `1) Agent integrity: …` | 3,909 |

- **one paragraph** — split at each criterion name, then compress as for batch B
- **four lines** — the extra line is an overall verdict or summary; delete it and fold anything
  factual into the criterion it belongs to
- **numbered** — drop the `1) ` `2) ` `3) ` prefixes so each line opens with the criterion name
- 96.1% already use the canonical criterion names; fix the rest

## Rules that apply to all three

1. **Do not change any judgement.** If the current text says the grasp fails, the new text says the
   grasp fails. You are shortening and re-laying-out, not re-deciding.
2. **Every line must agree with its `sub_scores` entry.** The current text already does; keep it that
   way while compressing. **The checker cannot verify this** — it needs your attention.
3. **Do not drop a criterion to save space.** All three lines stay.
4. **Cut evidence last.** Remove restatement, hedging and summary first. If a line is still too long
   with two concrete observations, keep the more specific one.
5. Everything in the "Never present" table of [`SFT_FORMAT.md`](SFT_FORMAT.md) stays absent.
6. `main_score` and `sub_scores` are given and are never edited.

## Delivery

Per batch, or combined — the checker takes any units file and any output file:

```bash
python check_reformat.py batch_B_compress.jsonl reformatted_B.jsonl
```

It enforces the shape, the names, the band and the "never present" list, and prints the median
length per score.

**The per-score spread is only a failure on the combined delivery.** Run on one batch it is printed
for information and nothing more — a single batch is skewed (batch A is 59% score-5), so its
internal spread is not a target anyone can hit. Concatenate all three outputs and run it once more:
there, **medians spreading by more than 80 characters fails the delivery**, because that spread is
the label leaking through length and removing it is the point of this task.

```bash
cat reformatted_A.jsonl reformatted_B.jsonl reformatted_C.jsonl > reformatted_all.jsonl
cat batch_A_ready.jsonl batch_B_compress.jsonl batch_C_relayout.jsonl > units_all.jsonl
python check_reformat.py units_all.jsonl reformatted_all.jsonl
```

Report: how many rows you copied through, how many you compressed, and **any unit whose current text
contradicts its own `sub_scores`** — list those rather than fixing them.
