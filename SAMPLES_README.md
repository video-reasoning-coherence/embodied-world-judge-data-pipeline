# `samples_1000_assets.json` — 1,000 source-episode asset bundles

1,000 distinct source episodes sampled from the corpus. Each entry holds three
Hugging Face URLs and nothing else — no generated video, no generation model, no
prompt, no scores, no labels.

## Entry format

```json
{
  "dataset": "droid",
  "task": "task_0031",
  "episode": "episode_0001",
  "instruction_url":        ".../gt_data/<task>/<episode>/prompt/instruction.txt",
  "init_frame_url":         ".../gt_data/<task>/<episode>/prompt/init_frame.png",
  "gt_reference_video_url": ".../gt_data/<task>/<episode>/video.mp4"
}
```

All three live under
`huggingface.co/datasets/HuggingFriends/mllm-as-embodied-world-judge`.
Verified: 8 random entries × 3 URLs = 24/24 HTTP 200.

## Sampling

- **One entry per source episode.** The corpus holds 1,079 distinct source
  episodes; 1,000 of them are sampled, so no two entries share an instruction,
  init frame or reference video.
- **Dataset proportions preserved**, matching the source pool to within 0.1 pp.

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

Entries are sorted by `(dataset, task, episode)`.

## Note

Train/test membership was not used as a filter, so these source episodes may
underlie items in the released splits.
