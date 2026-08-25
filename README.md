# Embodied World Judge — Data Pipeline

Tooling and specification for building **source datasets** for
[MLLM-as-Embodied-World-Judge](https://github.com/SiyuanMaCS/MLLM-as-Embodied-World-Judge):
manipulation video clips paired with grounded instructions, used to evaluate how
well video generators respect physics and follow instructions.

Use this repository to build a **new batch** of source data that is compatible
with the existing corpus.

---

## Contents

- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Data format](#data-format)
- [Command reference](#command-reference)
- [Repository layout](#repository-layout)
- [Current corpus](#current-corpus)
- [Limitations](#limitations)

---

## Quick start

**Requirements:** Python 3.9+, `ffmpeg` and `ffprobe` on `PATH`.

```bash
git clone https://github.com/SiyuanMaCS/embodied-world-judge-data-pipeline.git
cd embodied-world-judge-data-pipeline
pip install -r requirements.txt
```

Validate an existing dataset to confirm your setup:

```bash
export EWJ_DATA_ROOT=/path/to/data
python tools/validate_dataset.py "$EWJ_DATA_ROOT/robotwin" --spec v1
```

Expected output:

```text
dataset=robotwin  episodes=198  spec=v1

PASS  (0 failed, 0 warnings)
```

Build a new dataset by filling in `iter_source_episodes()` in
[`examples/ingest_template.py`](examples/ingest_template.py), which implements the
clip rules, then gate it before delivery:

```bash
python tools/validate_dataset.py data/my_dataset --spec v2 --strict-media
python tools/check_disjoint.py   data/my_dataset --against data/*/summary.json
```

Both exit non-zero on failure, so they can be used directly in CI.

---

## How it works

```text
  public corpus
       │
       │  1. select episodes, cut 5–10s clips, extract the conditioning frame
       ▼
  data/<dataset>/gt_data/          ──▶  2. write summary.json (11 fields)
       │
       │  3. generate videos with each model under test
       ▼
  data/<dataset>/generated_data/   ──▶  4. judge / annotate  →  train & test splits
```

Stages 1–2 are covered by this repository. Stage 3 is documented in
[`README_VIDEO_GENERATION.md`](https://github.com/SiyuanMaCS/MLLM-as-Embodied-World-Judge/blob/main/README_VIDEO_GENERATION.md)
in the main repository; stage 4 is out of scope here.

See [`docs/pipeline.md`](docs/pipeline.md) for the full specification of stages
1–2, including clip selection, the conditioning-frame filter, and how each
prompt field is produced.

---

## Data format

Every dataset is a directory:

```text
data/<dataset>/
├── summary.json
└── gt_data/
    └── <task_name>/<episode_name>/
        ├── prompt/
        │   ├── init_frame.png
        │   └── prompt.txt
        └── video.mp4
```

`summary.json` is a JSON array. Every record has all eleven fields:

| Field | Type | Description |
| --- | --- | --- |
| `gt_path` | string | Repo-relative path to `video.mp4` |
| `image` | string | Repo-relative path to `init_frame.png` |
| `task_name` | string | Unique within the dataset |
| `episode_name` | string | Unique within the task |
| `prompt` | array of string | The grounded instruction |
| `prompt_prefix` | string | Scene-stability preamble applied at generation time |
| `prompt_rewrite` | string | Image-grounded rephrasing of the instruction |
| `prefix_id` | string \| int | Which prefix variant was used |
| `rewrite_id` | string \| int | Which rewrite variant was used |
| `duration` | number | Clip length in seconds |
| `init_frame_offset_sec` | number | Timestamp `init_frame.png` was taken from |

Full specification, including the `item_id` convention used downstream:
[`docs/data-format.md`](docs/data-format.md).

---

## Command reference

### `validate_dataset.py`

Validates a dataset against the format specification.

```bash
python tools/validate_dataset.py <dataset_dir> [--strict-media]
```

| Option | Description |
| --- | --- |
| `--spec {v1,v2}` | Format version. `v2` (default) is for new batches: it requires `action_caption` and `speed_factor` and enforces the clip-duration policy. `v1` is the original eleven-field format used by the existing corpus. |
| `--strict-media` | Decode every video with `ffprobe`. Slower, but catches truncated files that a file-size check misses. |

Checks performed: required fields and their types, `(task_name, episode_name)`
uniqueness, existence of `video.mp4`, `prompt/init_frame.png` and
`prompt/prompt.txt`, and agreement between `gt_path` and the directory layout.

**Exit codes:** `0` valid, `1` invalid.

### `check_disjoint.py`

Checks that a new dataset does not overlap released data.

```bash
python tools/check_disjoint.py <dataset_dir> --against <summary.json|split.jsonl> ...
```

Compares on `(dataset, task_name, episode_name)` and on `gt_path`. Accepts both
`summary.json` files and released `.jsonl` splits.

**Exit codes:** `0` disjoint, `1` overlapping.

---

## Repository layout

```text
docs/
  pipeline.md        How source data is built: corpora, clips, prompts
  data-format.md     summary.json specification and directory layout
  generation.md      Pointer to the video generation stage in the main repo
  acceptance.md      Checklist a delivered batch must satisfy
examples/
  ingest_template.py         Reference implementation of the clip rules
  ingest_egodex_human.py     Working ingest script (EgoDex, human egocentric)
  ingest_egoscaler.py        Working ingest script (EgoScaler)
  ingest_epickitchens.py     Working ingest script (EPIC-KITCHENS)
  prompt_templates.json      Prefix and rewrite templates (v3)
tools/
  validate_dataset.py
  check_disjoint.py
```

---

## Current corpus

Eleven datasets, 1,391 episodes, built under spec v1. All pass
`validate_dataset.py --spec v1` with no failures and no warnings.

| Dataset | Episodes | Type |
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
| **Total** | **1,391** | |

---

## Limitations

- **Episode-selection code exists for 3 of the 11 datasets.** The scripts in
  `examples/` cover `egodex_human`, `egoscaler_human` and `epickitchens_human`.
  For the remaining eight, the prompt pipeline is shared and documented, but the
  logic that chose *which* episodes to include was not preserved. Treat a new
  batch as a fresh ingestion against the specification rather than a
  reproduction.
- Example scripts require a Gemini API key in `GEMINI_API_KEY` and read their
  output root from `EWJ_DATA_ROOT`.
- Source video licences follow the upstream corpora and are not redistributed by
  this repository.
