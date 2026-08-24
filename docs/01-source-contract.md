# 1. Source data contract

This is the **only** thing a new batch has to satisfy. Everything downstream
(video generation, judging, annotation) reads this and nothing else.

## Directory layout

```text
data/<dataset>/
├── summary.json                  # one record per episode, see below
├── gt_data/
│   └── <task_name>/<episode_name>/
│       ├── prompt/
│       │   ├── init_frame.png    # the conditioning image
│       │   └── prompt.txt        # the instruction, plain text
│       └── video.mp4             # the ground-truth clip
└── generated_data/               # written later by the generation stage
    └── <model>/<task_name>/<episode_name>/<seed>/<name>.mp4
```

`<dataset>`, `<task_name>` and `<episode_name>` become part of the `item_id`
used everywhere downstream, so they must be **stable and unique**:

```text
item_id = data__<dataset>__generated_data__<model>__<task_name>__<episode_name>__<seed>__<name>
```

⚠️ `task_name` must be unique **within the dataset**. Semantic labels repeat in
some source corpora and many rows reuse `episode_0001`; if you keep the semantic
label, generated outputs collide and resume silently skips unrelated samples.
Rewrite to a positional id (`task_0001`, `task_0002`, …) when in doubt.

## `summary.json`

A JSON **list**. Every record carries all 11 fields — this is verified across all
11 existing datasets (1,391 episodes), with no optional fields and no extras:

| field | type | meaning |
|---|---|---|
| `gt_path` | str | `data/<dataset>/gt_data/<task>/<episode>/video.mp4`, repo-relative |
| `image` | str | `.../prompt/init_frame.png`, repo-relative |
| `task_name` | str | unique within the dataset |
| `episode_name` | str | unique within the task |
| `prompt` | list[str] | the base instruction(s) |
| `prompt_prefix` | str | scene-stability preamble prepended at generation time |
| `prompt_rewrite` | str | an LLM-rewritten phrasing of the same instruction |
| `prefix_id` | str/int | which prefix variant was used |
| `rewrite_id` | str/int | which rewrite variant was used |
| `duration` | float | clip length in seconds |
| `init_frame_offset_sec` | float | where in the clip `init_frame.png` was taken |

**Why three prompt fields.** The benchmark generates from two conditions —
`prefix` (base instruction + stability preamble) and `rewrite` (LLM-rephrased) —
so each source episode yields two generated variants per model. Keep `prompt`
intact; never overwrite it with the prefixed or rewritten text.

## Acceptance

Run `tools/validate_dataset.py data/<dataset>` before handing a batch over.
It is the executable form of everything above; if it does not pass, the batch
cannot be merged.
