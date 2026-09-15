# `samples_real_1000_assets.json` — 1,000 real-capture source episodes

Each entry holds three Hugging Face URLs: instruction, conditioning frame,
ground-truth reference video. No generated video, no generation model, no
scores, no labels.

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

Verified: 10 random entries × 3 URLs = 30/30 HTTP 200.

## Pool

The dataset holds **1,391 source episodes**. Excluding the two rendered-simulation
corpora leaves **1,093 real ones**, from which 1,000 are sampled with each
dataset's share preserved to within 0.1 pp.

| dataset | n | share | capture |
| --- | ---: | ---: | --- |
| agibot_world | 184 | 18.4% | real robot |
| droid | 182 | 18.2% | real robot |
| gr1_inlab | 156 | 15.6% | real robot |
| egodex_human | 137 | 13.7% | human egocentric |
| open_x_embodiment | 130 | 13.0% | real robot |
| egoscaler_human | 91 | 9.1% | human egocentric |
| epickitchens_human | 55 | 5.5% | human egocentric |
| dreamdojo_hv | 43 | 4.3% | real robot |
| egodex | 22 | 2.2% | real robot (lab) |

Excluded: `robotwin` (198) and `libero` (100) — rendered simulation, confirmed by
inspecting conditioning frames rather than by name.

Every kept dataset was re-checked against sampled frames (3 each for
`dreamdojo_hv`, `gr1_inlab`, `open_x_embodiment`, `egodex`; 2 each for
`egodex_human`, `agibot_world`, `droid`). All are photographic capture.
`dreamdojo_hv` and `gr1_inlab` read as synthetic but are real lab footage.
`egodex` is listed as human egocentric in the pipeline docs, but its frames show
real robot hands in the same lab rig — the capture column here reflects the
frames, not the doc.

Entries are sorted by `(dataset, task, episode)`.
Train/test membership was not used as a filter.
