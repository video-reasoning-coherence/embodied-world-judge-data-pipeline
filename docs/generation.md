# Video generation

The generation stage is documented in the main repository. This page is a
pointer, not a duplicate.

| Resource | Location |
| --- | --- |
| Full guide (10 sections, all model families) | [`README_VIDEO_GENERATION.md`](https://github.com/SiyuanMaCS/MLLM-as-Embodied-World-Judge/blob/main/README_VIDEO_GENERATION.md) |
| Per-model launchers | `scripts_inference/run_*.sh` |
| API route | `run_api_parallel.py` |
| Local route | `run_local.py`, `inference/` |

Covered model families: Wan2.2 TI2V-5B, Cosmos-Predict2.5, Cosmos3, CogVideoX,
WoW, GigaWorld, HunyuanVideo 1.5, LongCat-Video, Stable Video Diffusion (SVD-xt),
LingBot-Video, PhysisForcing PF_Wan, and the API models.

## Output location

```text
data/<dataset>/generated_data/<model>/<task_name>/<episode_name>/<seed>/<name>.mp4
```

## Two failure modes to plan for

**Frame count is not interchangeable across model families.** Record it in the
run name or the generation metadata; otherwise the setting that produced a clip
cannot be recovered afterwards.

**Task-name collisions.** If the source corpus reuses labels or `episode_0001`,
outputs overwrite each other and resume logic skips unrelated samples. Resolve
this at ingestion time — see [`data-format.md`](data-format.md#identifiers).
