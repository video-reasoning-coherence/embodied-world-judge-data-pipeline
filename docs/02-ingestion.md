# 2. Ingestion — turning a public corpus into a source dataset

## What the existing 11 datasets look like

| dataset | episodes | kind |
|---|---:|---|
| agibot_world | 200 | robot |
| droid | 199 | robot |
| robotwin | 198 | robot (sim) |
| gr1_inlab | 171 | robot |
| egodex_human | 150 | human egocentric |
| open_x_embodiment | 142 | robot |
| libero | 100 | robot (sim) |
| egoscaler_human | 100 | human egocentric |
| epickitchens_human | 60 | human egocentric |
| dreamdojo_hv | 47 | robot |
| egodex | 24 | human egocentric |
| **total** | **1,391** | |

All 11 pass `tools/validate_dataset.py` with zero failures and zero warnings —
that is the bar a new batch has to clear.

## The pattern

`examples/` holds three complete, working ingest scripts. They were written for
different source corpora but follow the same five steps:

1. **Pick a source corpus** and enumerate its episodes
   (`huggingface_hub` + `pyarrow` for LeRobot-style parquet shards).
2. **Sample episodes deterministically** — `random.seed(42)`, fixed target count.
   Determinism matters: a re-run must reproduce the same batch.
3. **Cut a clip** of the required length and pick `init_frame_offset_sec`;
   write `video.mp4` and `prompt/init_frame.png`.
4. **Filter on the conditioning frame.** `ingest_egodex_human.py` asks a VLM a
   single strict yes/no question (*is a human hand clearly visible, fingers or
   palm, not just a wrist*) and drops the episode if the answer is no.
   ⚠️ A bad `init_frame.png` poisons every downstream generation from it, so
   this filter is the highest-leverage step in the whole pipeline.
5. **Write `summary.json`** with all 11 fields, then run the validator.

## Worked examples in `examples/`

| script | source | target | filter |
|---|---|---|---|
| `ingest_egodex_human.py` | `yixuan-tan/EgoDex-LeRobot-v3.0` | 150, 5–10 s | VLM: hand visible in init frame |
| `ingest_egoscaler.py` | EgoScaler | 100 | see script header |
| `ingest_epickitchens.py` | EPIC-KITCHENS | 60 | see script header |

Each hard-codes its output root; change the `DATA` constant before running.

## ⚠️ What is NOT here

**Only 3 of the 11 datasets have a recoverable ingest script.** The other eight —
`agibot_world`, `droid`, `robotwin`, `gr1_inlab`, `open_x_embodiment`, `libero`,
`dreamdojo_hv`, `egodex` — were ingested earlier and their selection code is not
in this repository. For those, the **contract in `docs/01-source-contract.md` and
the validator are authoritative**; the original selection logic is not documented
and should not be assumed reproducible.

If a new batch needs to match one of those eight, treat it as a fresh ingestion
against the contract rather than as a re-run.

## Prompt fields

`prompt` is the base instruction. `prompt_prefix` is a fixed scene-stability
preamble; `prompt_rewrite` is an LLM rephrasing. Each source episode is generated
twice per model (`prefix` and `rewrite`), which is why every generated `item_id`
carries one of those two markers. Keep `prompt` untouched.
