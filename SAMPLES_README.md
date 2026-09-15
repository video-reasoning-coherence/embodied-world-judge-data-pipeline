# `samples_real_913_assets.json` — real-capture source episodes

913 distinct source episodes, **real capture only**. Each entry holds three
Hugging Face URLs: instruction, conditioning frame, ground-truth reference video.
No generated video, no generation model, no scores, no labels.

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

## Why 913 and not 1,000

`robotwin` and `libero` are rendered simulation and were excluded. That leaves
**913 distinct real source episodes in the whole corpus** — 913 is the ceiling,
not a sampling choice. Going higher would mean repeating an episode's
instruction/frame/reference under a different generated video, which this file
does not carry.

| dataset | episodes | share | capture |
| --- | ---: | ---: | --- |
| agibot_world | 195 | 21.4% | real robot |
| droid | 185 | 20.3% | real robot |
| egodex_human | 141 | 15.4% | human egocentric |
| egoscaler_human | 93 | 10.2% | human egocentric |
| gr1_inlab | 92 | 10.1% | real robot |
| open_x_embodiment | 83 | 9.1% | real robot |
| epickitchens_human | 58 | 6.4% | human egocentric |
| dreamdojo_hv | 42 | 4.6% | real robot |
| egodex | 24 | 2.6% | human egocentric |

Every real episode in the corpus is included, so the distribution is the corpus
distribution.

## Excluded

| dataset | episodes | reason |
| --- | ---: | --- |
| robotwin | 122 | simulated — rendered scene, primitive props |
| libero | 44 | simulated — rendered scene |

Confirmed by inspecting one conditioning frame per dataset, not by name alone:
`dreamdojo_hv` and `gr1_inlab` are real lab footage despite the synthetic-sounding
names, and are kept.

Entries are sorted by `(dataset, task, episode)`.
Train/test membership was not used as a filter.
