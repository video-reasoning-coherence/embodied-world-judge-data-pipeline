# Data format

Specification for a source dataset. A dataset that satisfies this can be used by
every downstream stage without modification.

## Directory layout

```text
data/<dataset>/
├── summary.json
├── gt_data/
│   └── <task_name>/<episode_name>/
│       ├── prompt/
│       │   ├── init_frame.png
│       │   └── prompt.txt
│       └── video.mp4
└── generated_data/                       # written by the generation stage
    └── <model>/<task_name>/<episode_name>/<seed>/<name>.mp4
```

## Identifiers

`<dataset>`, `<task_name>` and `<episode_name>` are concatenated into the
`item_id` used by every downstream stage:

```text
data__<dataset>__generated_data__<model>__<task_name>__<episode_name>__<seed>__<name>
```

`task_name` must be unique within a dataset. Some source corpora reuse semantic
labels, and many reuse `episode_0001` across tasks. If those labels are carried
over, generated outputs overwrite one another and resume logic skips unrelated
samples. Rewrite to positional identifiers (`task_0001`, `task_0002`, …) when the
source labels are not guaranteed unique.

## `summary.json`

A JSON array with one object per episode. There are two versions of the
specification:

- **v2** — used for new batches. Thirteen required fields, plus a clip-duration
  policy.
- **v1** — the original eleven-field format used by the existing corpus. Still
  accepted by the validator via `--spec v1`.

All fields are required; there are no optional fields.

| Field | Type | Description |
| --- | --- | --- |
| `gt_path` | string | Repo-relative path to `video.mp4` |
| `image` | string | Repo-relative path to `prompt/init_frame.png` |
| `task_name` | string | Unique within the dataset |
| `episode_name` | string | Unique within the task |
| `prompt` | array of string | The grounded instruction |
| `prompt_prefix` | string | Scene-stability preamble, prepended at generation time |
| `prompt_rewrite` | string | Image-grounded rephrasing of the instruction |
| `prefix_id` | string \| int | Index of the prefix variant used |
| `rewrite_id` | string \| int | Index of the rewrite variant used |
| `duration` | number | Clip length in seconds, measured with `ffprobe` |
| `init_frame_offset_sec` | number | Timestamp within the clip that `init_frame.png` was taken from |
| `action_caption` | string | v2 only. One or two sentences describing the complete action through to its completion state |
| `speed_factor` | number | v2 only. Playback rate applied when cutting; `1.0` if unmodified |

### Clip duration policy (v2)

| Rule | Value |
| --- | --- |
| Preferred band | 5–10 seconds |
| Hard minimum | 5 seconds |
| Hard maximum | 20 seconds |

Clips outside the preferred band produce a warning; clips outside the hard bounds
fail validation. A source segment that is too slow may be sped up to bring it
into band, provided the rate is recorded in `speed_factor` so the change is
traceable.

### Example

```json
{
  "gt_path": "data/robotwin/gt_data/task_0001/episode_0001/video.mp4",
  "image": "data/robotwin/gt_data/task_0001/episode_0001/prompt/init_frame.png",
  "task_name": "task_0001",
  "episode_name": "episode_0001",
  "prompt": ["Grab the red block with the black gripper and place it on the left."],
  "prompt_prefix": "In a fixed robotic workspace, a rigid and physically consistent embodied robotic arm with high stability and no deformation proceeds to",
  "prompt_rewrite": "A black robotic gripper reaches for the red block, closes around it, lifts it and sets it down on the left side of the table.",
  "prefix_id": 0,
  "rewrite_id": 2,
  "duration": 7.2,
  "init_frame_offset_sec": 0.0,
  "action_caption": "The gripper closes on the red block, lifts it clear of the table and sets it down on the left.",
  "speed_factor": 1.0
}
```

### The three prompt fields

They are produced by different processes and are not interchangeable.

- `prompt` is the instruction the task is judged against. Never overwrite it with
  a prefixed or rewritten variant.
- `prompt_prefix` is prepended to `prompt` to form one generation condition.
- `prompt_rewrite` is a standalone rephrasing used as the second generation
  condition.

Each source episode is therefore generated twice per model, and every generated
`item_id` carries a `prefix` or `rewrite` marker. See
[`pipeline.md`](pipeline.md) for how each field is produced.

## Validation

```bash
python tools/validate_dataset.py data/<dataset> --spec v2 --strict-media
```

The validator is the normative form of this document. Where the two disagree,
the validator is correct.
