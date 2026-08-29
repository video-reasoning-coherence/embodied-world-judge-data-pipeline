# The SFT format we want

This is the target every reasoning in the training set must reach. It is not a style preference —
each rule below exists because breaking it caused a measured problem.

## The row it ends up in

One training sample per **(video, axis)** pair. A video appears twice, once judged for physical
adherence and once for instruction alignment, independently.

```json
{
  "messages": [
    {"role": "system",    "content": "<the judge's system prompt for this axis>"},
    {"role": "user",      "content": "<the judge's user prompt for this axis>"},
    {"role": "assistant", "content": "{\"reasoning\": \"...\", \"physical_adherence\": 3}"}
  ],
  "videos": ["<video_url>"],
  "images": ["<init_frame_url>"]
}
```

| axis | media | answer key |
| --- | --- | --- |
| `pa` | `<video>` only, **no `images` key** | `physical_adherence` |
| `ia` | `<image><video>`, init frame plus video | `instruction_alignment` |

The prompts are the judge's own, copied byte for byte. **`pa` never receives the instruction** — its
prompt says to judge from the video alone, so putting the instruction in that input would train the
model on something evaluation never gives it.

The assistant turn is a **JSON string with exactly two keys**. Sub-scores never appear in it; they
are diagnostic inputs, not a training target.

## `reasoning` — exactly three lines

One line per criterion, in order, each opening with the criterion's name.

| `axis` | line 1 | line 2 | line 3 |
| --- | --- | --- | --- |
| `pa` | `Agent integrity:` | `Scene & object consistency:` | `Interaction realism:` |
| `ia` | `Agent match:` | `Object correctness:` | `Goal completion:` |

Those names are the judge prompt's own criteria. The prompt says *"your reasoning must address
each"*, so **all three lines are present even when a criterion has nothing to report** — a criterion
that holds takes one clause.

A short verdict phrase may sit between the name and the colon (`Interaction realism severely
violated:`), but the line must open with the name.

```
Agent match: A single right hand performs the action while the other plates are untouched.
Object correctness: It reaches the yellow plate rather than the red, green or blue ones.
Goal completion: The hand only slides and tilts the plate along the cloth; it never leaves the table surface, so the plate is not actually picked up.
```

## Length: `pa` 300–550 characters, `ia` 220–450

Not an arbitrary band. It is the length of the reference format itself: strip
`7.20_baseline_rephrased` of its `description:` header and its `(PAn)` verdict line — the two things
we drop — and the remainder has a median of 423 characters for `pa` and 257 for `ia`.

**Every row must land in the band, and this matters more than any single row's length.** Length is
currently correlated with the label: score 5 sits at a median of 537 characters while scores 1–4 sit
at 767–793, because the units where nothing went wrong were written separately and more briefly. Of
the rows under 350 characters, 74% are score 5 against a base rate of 8.4%. A model trained on that
can learn *short answer → score 5*, and since it emits the reasoning before the score, a short
generation drags the score upward — in the class it already predicts least often.

Aim for the middle of the band. Do not compress to the floor.

## Never present

| | why |
| --- | --- |
| any number offered as a score — `score of 2`, `sub-score`, `main score`, `(PA3)`, `goal_completed=1` | the score is already the row's own field; a second copy can disagree with the first, and did |
| a `Physical adherence description:` header | not part of the prompt |
| an overall verdict line, e.g. `Physically inconsistent.` | same as a score |
| `annotator`, `the note says`, `candidates`, `consensus` | at inference the model sees a video and a prompt, nothing else |
| markdown, bullets, numbered prefixes, blank lines, a fourth line | the field is plain text, three lines |
| Chinese | the target is English |

## Each line must agree with its `sub_scores`

`2` the criterion holds · `1` a minor problem · `0` clearly violated. The line's severity must match:
严重-level wording for `0`, measured wording for `1`, plain positive statement for `2`.

**No checker can verify this** — it is the one rule that needs a person. Where the existing text
already disagrees with its sub-score, report the unit rather than fixing it: changing it is a
judgement change and belongs to the data owner.

## Scores are given

`main_score` and `sub_scores` come with the data and are never edited, in either direction, for any
reason.
