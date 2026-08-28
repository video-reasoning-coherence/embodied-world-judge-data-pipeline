# Delivery directory

Put your output here. Nothing else in this repository should be modified.

| file | required | what |
| --- | --- | --- |
| `rewritten.jsonl` | yes | one `{"unit_id": ..., "reasoning": ...}` per line, 10,976 lines |
| `rewritten_no_note.jsonl` | if you did the second package | same shape, 472 lines |
| `REPORT.md` | yes | the four items listed under "What to report back" in [`../README.md`](../README.md) |

Both jsonl files must pass the gate before you deliver:

```bash
cd ..
python check_rewrite.py units.jsonl         delivery/rewritten.jsonl
python check_rewrite.py units_no_note.jsonl delivery/rewritten_no_note.jsonl
```

Expected sizes are roughly 7.6 MB and 0.3 MB. If yours is far smaller, you have dropped rows —
the gate will say so.

## How to get it here

Push a branch and open a pull request against `master` (this repository has no `main` branch). Do not push to `master` directly.

```bash
git checkout -b delivery/<your-name>
git add delivery/
git commit -m "note-to-reasoning delivery"
git push -u origin delivery/<your-name>
```

Paste the gate's output for both files into the pull request description. A delivery whose gate
output is not shown will be sent back without review.
