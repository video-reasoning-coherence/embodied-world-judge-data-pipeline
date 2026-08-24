# Embodied World Judge — data pipeline

How the **source data** for `MLLM-as-Embodied-World-Judge` is constructed, and
what a new batch has to satisfy to be usable.

This repository exists so an external agent can build **more** source data for
the next project without reverse-engineering the existing corpus.

## The three stages

```text
  public corpus  ──①ingest──▶  data/<dataset>/{summary.json, gt_data/}
                                        │
                                        ②generate
                                        ▼
                              data/<dataset>/generated_data/<model>/...
                                        │
                                        ③judge / annotate
                                        ▼
                                   train / test splits
```

| stage | where it is documented |
|---|---|
| ① ingest | `docs/02-ingestion.md` + `examples/` (3 working scripts) |
| ② generate | **already documented** — `README_VIDEO_GENERATION.md` in the main repo; see `docs/03-generation.md` |
| ③ judge / annotate | out of scope here — see `EXTERNAL_AGENT_REQUIREMENTS.md` in the annotation repo |

## Start here

1. **`docs/01-source-contract.md`** — the only thing a new batch must satisfy.
   11 fields, one directory layout. Verified against all 11 existing datasets
   (1,391 episodes), zero exceptions.
2. **`docs/02-ingestion.md`** — how episodes are selected, with three worked
   examples, and an explicit list of what is *not* recoverable.
3. **`docs/04-acceptance.md`** — the checks a delivered batch must pass.

## Tools

```bash
python tools/validate_dataset.py data/<dataset> [--strict-media]
python tools/check_disjoint.py   data/<dataset> --against <summary.json|split.jsonl> ...
```

Both exit non-zero on failure, so they can gate a delivery. They are the
executable form of the contract — if the prose and the validator ever disagree,
**the validator wins.**

Current state of the existing corpus:

```text
agibot_world 200 · droid 199 · robotwin 198 · gr1_inlab 171 · egodex_human 150
open_x_embodiment 142 · libero 100 · egoscaler_human 100 · epickitchens_human 60
dreamdojo_hv 47 · egodex 24                                    total 1,391
all 11 pass validate_dataset.py with 0 fail / 0 warn
```

## Known gaps

- **8 of the 11 datasets have no recoverable ingest script.** Their selection
  logic is not documented and should not be assumed reproducible. Treat a new
  batch as a fresh ingestion against the contract.
- The example scripts hard-code their output root and their API keys come from
  the environment; read the header before running one.
