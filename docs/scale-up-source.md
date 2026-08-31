# Scaling up the source set

**Audience:** an agent asked to add source episodes to this corpus.
**Scope:** the source layer only — episodes, conditioning frames, and the four prompt
fields. Video generation and annotation are downstream and are not covered here.

Everything else in the project is a multiple of this layer, so an error here is
multiplied too. Today: **1,389 source episodes across 11 corpora**, which fan out to
11,497 generated videos and 22,568 annotation units.

---

## 0. Read this before planning anything

**Only 3 of the 11 corpora can be extended by re-running code.**

| Can be extended by re-running | Must be re-ingested from the spec |
| --- | --- |
| `egodex_human` (150) · `egoscaler_human` (100) · `epickitchens_human` (60) | `agibot_world` (200) · `droid` (199) · `robotwin` (198) · `gr1_inlab` (171) · `open_x_embodiment` (142) · `libero` (100) · `dreamdojo_hv` (47) · `egodex` (24) |
| `examples/ingest_*.py` exist | **the logic that chose *which* episodes was not preserved** |

For the right-hand column, "raise the target from 200 to 500 and re-run" is not
available. Those are 1,079 of the 1,389 episodes. Treat them as a fresh ingestion
against the contract, and **do not describe the result as reproducing the original
selection** — it isn't, and claiming so would make the corpus look more controlled than
it is.

**Before starting, ask whether the original selection code exists somewhere.** Recovering
it is worth more than any amount of re-derivation.

---

## 1. What you implement

One function. The four clip rules are already implemented in the template.

```python
# examples/ingest_<new>.py   (start from examples/ingest_template.py)
def iter_source_episodes():
    """Yield dicts: {'video': Path, 'start': float, 'end': float, 'label': str}

    `label` is the corpus's own task text. It is re-grounded against the
    conditioning frame in stage 3; do not clean it up here.
    """
```

```bash
cp examples/ingest_template.py examples/ingest_<new>.py
export EWJ_DATA_ROOT="/path/to/data"
python examples/ingest_<new>.py
```

---

## 2. Stage 1 — clip selection

| # | Rule | Enforced by |
| --- | --- | --- |
| 1 | One complete action per clip. 5–10 s preferred, **hard min 5 s, hard max 20 s**. | `validate_dataset.py --spec v2` — fails the batch |
| 2 | A too-slow segment may be sped up 1.5× or 2× to reach the band. Record it in `speed_factor`. | recorded, not checked |
| 3 | The conditioning frame must clearly show **both** the manipulator and the instruction's target object. | applied at ingestion (stage 2) |
| 4 | Every episode carries an `action_caption` through to the completion state. | `--spec v2` — fails the batch |

```bash
ffmpeg -ss <from> -i <source> -t <dur> out/video.mp4          # + -filter:v setpts=<1/speed>*PTS when sped up
ffmpeg -ss 0 -i out/video.mp4 -frames:v 1 out/prompt/init_frame.png
```

- **Write the duration `ffprobe` measures, not the duration you requested.** They differ,
  and the validator reads the file.
- **Fix the seed (`random.seed(42)`) and the target count**, so a re-run selects the same
  episodes. This is the property the 8 corpora above lost.

## 3. Stage 2 — conditioning-frame filter

The conditioning frame is the only input every generator receives. **An unusable frame
invalidates every video later produced from that episode**, so this filter is not optional.

Ask a VLM two questions about the frame:

1. `manipulator_visible` — is the gripper or hand clearly visible? Recognizable structure,
   not just an edge or a sleeve.
2. `object_visible` — is the object the instruction refers to clearly visible?

Both must hold. On failure retry at `t = 0.3, 0.7, 1.2, 1.8 s` and take the first frame
that passes; if none passes, **drop the episode**.

**Report how many episodes this removed and the denominator it removed them from.** A
count without its denominator cannot be acted on.

## 4. Stage 3 — the four prompt fields

| Field | What it is |
| --- | --- |
| `action_caption` | One or two sentences, third person, the action through to its completion state. A *description*. |
| `prompt` | The corpus's own label re-grounded against the frame by a VLM into one imperative line. A *command*. |
| `prompt_prefix` | Stability preamble, one of 5 `robot_prefixes` / 5 `human_prefixes`; `prefix_id` records the choice. Prepended at generation time. |
| `prompt_rewrite` | Image-grounded rephrasing: a multimodal call given the frame **and** the instruction, using one of 5 rewrite templates; `rewrite_id` records the choice. |

Templates live in [`examples/prompt_templates.json`](../examples/prompt_templates.json)
(set **v3, 2026-06-16**: action-focused, ≤128 tokens, object-locked, ending in the
completion state, minimal scene description).

🔑 **These are three parallel fields, not three versions of one string.** Each episode is
generated twice per model — once from `prompt_prefix + prompt`, once from
`prompt_rewrite` — which is where the `_prefix` / `_rewrite` suffixes in `item_id` come
from. **Never overwrite `prompt` with a rewrite.**

`prompt` rubric: imperative, verb first · name visible objects by colour/shape and the
target location · *hand* for human corpora, *gripper* for robot corpora · nothing that
cannot be verified from the frame · a command, not a caption.

---

## 5. Gates — run both, they exit non-zero

```bash
python tools/validate_dataset.py data/<new> --spec v2 --strict-media
python tools/check_disjoint.py   data/<new> --against data/*/summary.json
```

- **`--spec v2` for every new batch.** v1 is the older contract the existing corpus was
  built under; v2 additionally requires `action_caption` and `speed_factor` and enforces
  the duration policy.
- **`--strict-media` is not optional.** It decodes every clip with `ffprobe`. It exists
  because 91 videos were once byte-truncated and a file-size threshold missed two of them
  — they were exactly 256 KiB and 512 KiB. **Decoding is the predicate; size is only a
  proxy for it.**
- `check_disjoint.py` compares on `(dataset, task_name, episode_name)` and on `gt_path`
  against every existing `summary.json`. **New episodes must not collide with released
  data**, or the test split stops being held out.

## 6. Deliver

`data/<dataset>/summary.json` plus the tree in
[`data-format.md`](data-format.md), and a short report stating:

1. episodes enumerated from the source corpus (the denominator),
2. dropped by the duration rule,
3. dropped by the conditioning-frame filter,
4. delivered,
5. both gate commands and their exit codes.

**Report the numbers that did not survive, not only the ones that did.** A batch of 500
with no attrition figures cannot be reviewed.

---

## 7. Two practical constraints

**Disk.** Check free space before writing. A full disk does not fail loudly here — it
produces zero-byte and truncated files, which is the failure mode `--strict-media` was
added to catch. At the time of writing one project drive is 100% full and the other has
~405 GB.

**Family determines wording.** Robot corpora describe a *gripper* or *arm*; human
egocentric corpora describe a *hand*. The choice propagates into both the `prompt` rubric
and the template family, so classify the corpus before generating any text.
