# Acceptance checklist

Run these before delivering a batch. All must pass.

## 1. Format

```bash
python tools/validate_dataset.py data/<dataset> --strict-media
```

Must exit `0`.

Include `--strict-media`. It decodes every video with `ffprobe`. A previous batch
shipped 91 byte-truncated videos (`moov atom not found`) that a file-size
threshold missed, because two of the three truncation sizes were 256 KiB and
512 KiB. Decoding is the test; file size is only a proxy for it.

## 2. No overlap with released data

```bash
python tools/check_disjoint.py data/<dataset> --against data/*/summary.json
```

Must exit `0`. New identifiers must not collide with released data, and the new
dataset must not silently duplicate episodes of an existing one.

## 3. Reproducibility

The ingest script must state its random seed and target count, and a second run
must select the same episodes. If it cannot, say so in the delivery note rather
than leaving a future re-run to differ silently.

## 4. Delivery note

Report, alongside the numbers:

- source corpus, its revision, and its licence;
- episode count **and the denominator it came from** — how many were considered;
- every filter applied and how many episodes each one removed;
- the random seed;
- anything that did not work, including checks that produced no signal.

A count without its denominator cannot be reviewed. "150 episodes" and "150 of
4,000 considered, 610 removed by the hand-visibility filter" are different
claims, and only the second can be checked.
