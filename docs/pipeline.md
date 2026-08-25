# Source pipeline

How a public corpus becomes a source dataset: which corpora were used, how clips
are selected and cut, and how each prompt field is produced.

## 1. Source corpora

Eleven corpora were used, split into two families. The family determines which
prompt templates apply and how the instruction is worded.

| Dataset | Episodes | Family |
| --- | ---: | --- |
| `agibot_world` | 200 | Robot |
| `droid` | 199 | Robot |
| `robotwin` | 198 | Robot (simulated) |
| `gr1_inlab` | 171 | Robot |
| `egodex_human` | 150 | Human egocentric |
| `open_x_embodiment` | 142 | Robot |
| `libero` | 100 | Robot (simulated) |
| `egoscaler_human` | 100 | Human egocentric |
| `epickitchens_human` | 60 | Human egocentric |
| `dreamdojo_hv` | 47 | Robot |
| `egodex` | 24 | Human egocentric |

Robot datasets describe a gripper or arm; human datasets describe a hand. The
distinction propagates into the refinement rubric and the template family.

## 2. Clip selection

Reference implementation: [`examples/ingest_template.py`](../examples/ingest_template.py).
Supply `iter_source_episodes()` for your corpus; the four clip rules below are
already implemented. The scripts in `examples/ingest_*.py` are the original
per-corpus versions and predate these rules.

### Rules

| # | Rule |
| --- | --- |
| 1 | One complete action per clip. Preferred length 5–10s, hard minimum 5s, hard maximum 20s. |
| 2 | A source segment that is too slow may be sped up (1.5× or 2×) to bring it into band. Record the rate in `speed_factor`. |
| 3 | The conditioning frame must clearly show **both** the manipulator and the object the instruction refers to. |
| 4 | Every episode carries an `action_caption` describing the complete action through to its completion state. |

Enforced by `tools/validate_dataset.py --spec v2`; rules 1 and 4 fail the batch,
rule 2 is recorded rather than checked, rule 3 is applied at ingestion time.

### Procedure

1. Enumerate episodes from the source corpus. For LeRobot-format datasets, each
   parquet row carries `from_timestamp` and `to_timestamp` for its segment.
2. Apply the duration rule. Segments shorter than 5s are dropped: they cannot
   contain a complete action. Segments longer than the band are sped up if an
   allowed rate brings them into it, and dropped otherwise.
3. Cut the clip:

   ```bash
   ffmpeg -ss <from_timestamp> -i <source> -t <duration> <out>/video.mp4
   ```

   Add `-filter:v setpts=<1/speed>*PTS` when `speed_factor != 1.0`.

4. Extract the conditioning frame at `t = 0` of the cut clip:

   ```bash
   ffmpeg -ss 0 -i <out>/video.mp4 -frames:v 1 <out>/prompt/init_frame.png
   ```

5. Measure the real duration with `ffprobe` and write that value, not the
   requested one.
6. Use a fixed seed (`random.seed(42)`) and a fixed target count so that a re-run
   selects the same episodes.

## 3. Conditioning-frame filter

The conditioning frame is the input every generator is given, so an unusable
frame invalidates every video produced from that episode.

A vision-language model is asked two questions about the frame:

1. **manipulator_visible** — is the gripper or hand clearly visible? Requires
   recognizable structure, not just an edge or a sleeve.
2. **object_visible** — is the object the instruction refers to clearly visible?

Both must be true. If either fails, the pipeline retries at
`t = 0.3, 0.7, 1.2, 1.8` seconds and uses the first frame that passes; if none
passes, the episode is dropped.

Report how many episodes each filter removed, and the denominator it removed them
from.

## 4. Prompt construction

### 4.0 `action_caption` — the complete action

One or two sentences, third person present tense, describing the action from
start through to its completion state. This is a description, unlike `prompt`,
which is a command. Both are kept because they answer different questions: the
command is what the generator is asked to do, the caption is what a correct
result looks like.

### 4.1 `prompt` — the grounded instruction

The source corpus's own task label is re-grounded against the conditioning frame
by a vision-language model, producing a single imperative line. The rubric:

1. Imperative form, starting with a verb.
2. Name specific visible objects (colour, shape) and target locations.
3. Use *hand* or *left/right hand* for human datasets; *gripper* for robot
   datasets.
4. No meta-commentary and no scene description unless verifiable from the frame.
5. A task command, not a description of the image.

Two corpora required recovery because their native labels were unusable:

| Dataset | Recovery |
| --- | --- |
| `libero` | Each entry mapped to its true `task_index` in the source parquet, then the instruction read from the LIBERO benchmark package. |
| `gr1_inlab` | Conditioning frames classified by a VLM into one of ten hand-written task descriptions. |

Where a pre-refinement label existed it was preserved as `prompt_original`.

### 4.2 `prompt_prefix` — stability preamble

Selected from [`examples/prompt_templates.json`](../examples/prompt_templates.json):
five `robot_prefixes` and five `human_prefixes`. `prefix_id` records the choice.

```text
robot:  In a fixed robotic workspace, a rigid and physically consistent embodied
        robotic arm with high stability and no deformation proceeds to
human:  In a first-person egocentric video, a real human hand starts to
```

The preamble is prepended at generation time. `prompt` is not modified.

### 4.3 `prompt_rewrite` — image-grounded rephrasing

Produced by a multimodal call that receives both the conditioning frame and the
instruction, using one of five `robot_rewrite_templates` or
`human_rewrite_templates`. `rewrite_id` records the choice. The request is
assembled as:

```text
{wrapper_pre}       The attached image is the first frame of a {kind} manipulation video.
{rewrite_template}  <one of the five templates>
{wrapper_suf}       If the instruction conflicts with the image, prioritize the image.
                    Output ONLY the rewritten prompt.
Instruction:        {prompt}
```

Template set version **v3 (2026-06-16)**: action-focused, ≤128 tokens,
object-locked, ending in the completion state, minimal scene description.

Because the rewrite is grounded in the frame rather than in the instruction text,
it does not need regenerating when `prompt` is later edited.

## 5. Output

Write `summary.json` with all eleven fields (see
[`data-format.md`](data-format.md)) and validate before delivery:

```bash
python tools/validate_dataset.py data/<dataset> --strict-media
```

## 6. Coverage of this document

Sections 3 and 4 apply to all eleven datasets: the templates and the refinement
rubric are shared.

Section 2 — the logic that selected *which* episodes to include — is only
preserved for `egodex_human`, `egoscaler_human` and `epickitchens_human`, whose
scripts are in [`examples/`](../examples/). For `agibot_world`, `droid`,
`robotwin`, `gr1_inlab`, `open_x_embodiment`, `libero`, `dreamdojo_hv` and
`egodex`, that code was not preserved and those selections should not be assumed
reproducible.
