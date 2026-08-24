# 3. Generation — from source dataset to generated videos

**This stage is already documented in the main repository. Do not re-derive it.**

| what | where |
|---|---|
| full guide, 10 sections, every model family | `MLLM-as-Embodied-World-Judge/README_VIDEO_GENERATION.md` |
| per-model launchers (18) | `MLLM-as-Embodied-World-Judge/scripts_inference/run_*.sh` |
| API route | `run_api_parallel.py` |
| unified local route | `run_local.py`, `inference/` |

That guide covers environment snapshots, checkpoints, the output contract and
resume behaviour for Wan2.2, Cosmos-Predict2.5, Cosmos3, CogVideoX, WoW,
GigaWorld, HunyuanVideo 1.5, LongCat, SVD-xt, LingBot-Video, PhysisForcing
PF_Wan, and the API models.

## The two things that break batches

**Frame count is not interchangeable across model families.** Record it in the
run name or the generation metadata, or you cannot tell later which setting
produced a clip.

**`task_name` collisions.** If a source corpus reuses semantic labels or
`episode_0001`, outputs overwrite each other and resume skips unrelated samples.
Rewrite to positional ids at ingestion time — see `docs/01-source-contract.md`.

## Output location

```text
data/<dataset>/generated_data/<model>/<task>/<episode>/<seed>/<name>.mp4
```

which yields the downstream `item_id`:

```text
data__<dataset>__generated_data__<model>__<task>__<episode>__<seed>__<name>
```
