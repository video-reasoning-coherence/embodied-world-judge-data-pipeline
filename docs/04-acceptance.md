# 4. Acceptance — what a delivered batch must satisfy

Run these in order. A batch that fails any of them cannot be merged.

## 1. Contract

```bash
python tools/validate_dataset.py data/<dataset> --strict-media
```

Must exit 0. `--strict-media` decodes every video with `ffprobe`.

⚠️ **Include it.** A previous batch shipped 91 videos that were byte-truncated
(`moov atom not found`); a file-size threshold missed them because two of the
three truncation sizes were 256 KiB and 512 KiB. **The decode is the predicate;
size is only a proxy.**

## 2. No collision with existing data

```bash
python tools/check_disjoint.py data/<dataset> --against <existing summary.json ...>
```

New `item_id`s must not collide with anything already released, and the new
dataset must not silently duplicate episodes of an existing one.

## 3. Determinism

The ingest script must state its seed and target count, and a second run must
produce the same episode list. If it cannot, say so in the delivery note rather
than letting a future re-run quietly differ.

## 4. Delivery note

State, in the same message as the numbers:

- source corpus, its version/revision, and its licence;
- episode count and **the denominator it came from** (how many were considered);
- every filter applied, and **how many episodes each one dropped**;
- the seed;
- anything that did not work, including checks that returned no signal.

⚠️ A count without its denominator is not reviewable. "150 episodes" and
"150 of 4,000 considered, 610 dropped by the hand-visible filter" are different
claims, and only the second one can be checked.
