# `samples_1000_assets.json` — 1,000 asset bundles for annotation

A stratified sample of 1,000 items drawn from the existing corpus. Each entry
points at four Hugging Face URLs and nothing else: no scores, no labels.

## Entry format

```json
{
  "item_id": "data__<dataset>__generated_data__<model>__<task>__<episode>__1__<name>",
  "dataset": "droid",
  "task": "task_0031",
  "episode": "episode_0001",
  "generation_model": "kling_prefix",
  "init_frame_url":         ".../gt_data/<task>/<episode>/prompt/init_frame.png",
  "instruction_url":        ".../gt_data/<task>/<episode>/prompt/instruction.txt",
  "gt_reference_video_url": ".../gt_data/<task>/<episode>/video.mp4",
  "generated_video_url":    ".../generated_data/<model>/<task>/<episode>/1/video.mp4"
}
```

All four resolve on `huggingface.co/datasets/HuggingFriends/mllm-as-embodied-world-judge`.
Verified: 6 random entries × 4 URLs = 24/24 HTTP 200.

## How it was sampled

- **One item per distinct source episode.** The corpus holds 2,481 generated
  items over 1,079 source episodes; sampling one per episode gives 1,000
  *distinct* (init frame, instruction, reference video) bundles with no repeated
  source content.
- **Dataset proportions preserved** — each dataset's share matches its share of
  the source pool to within 0.1 pp.
- **Generation models balanced** — where an episode had several generations, the
  least-used model was taken, so 12 of the 15 models land within 72–79 items.

| dataset | n | share | pool share |
| --- | ---: | ---: | ---: |
| agibot_world | 181 | 18.1% | 18.1% |
| droid | 171 | 17.1% | 17.1% |
| egodex_human | 131 | 13.1% | 13.1% |
| robotwin | 101 | 10.1% | 10.1% |
| egoscaler_human | 86 | 8.6% | 8.6% |
| gr1_inlab | 85 | 8.5% | 8.5% |
| open_x_embodiment | 77 | 7.7% | 7.7% |
| epickitchens_human | 54 | 5.4% | 5.4% |
| libero | 53 | 5.3% | 5.3% |
| dreamdojo_hv | 39 | 3.9% | 3.9% |
| egodex | 22 | 2.2% | 2.2% |

`veo31_lite_*` (48 each) and `genie_prefix` (5) fall below the 72–79 band
because the corpus contains fewer of their generations.

## Notes

- Train/test membership was **not** used as a filter, so entries may overlap the
  released splits. Check `item_id` against `bench/` if disjointness is required.
- The reference video and instruction are **per source episode**, so items
  sharing a `(dataset, task, episode)` would share them — by construction no two
  entries here do.
