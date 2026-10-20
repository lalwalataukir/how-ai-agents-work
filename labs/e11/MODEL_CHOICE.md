# Model choice: research assistant

**Decision:** Claude Haiku 5.5 (`claude-haiku-5-5`), at the default effort.
**Date:** 2026-10-20 · **Decided by:** you

## Options compared

Run with `compare_models.py` on the 20 cases in `eval_cases.json`, one judge for all.

| Model | Eval score | Per 1,000 questions | Median time |
|---|---|---|---|
| Claude Haiku 5.5 | 95% | $0.354 | 4.8 s |
| Claude Sonnet 5.5 | 100% | $7.075 | 7.9 s |
| Claude Opus 5.5 | 100% | $13.380 | 11.2 s |
| qwen3:8b on my laptop (RAG answers only) | not run on the full set | $0 | 19 s |

## Why

- Haiku clears our minimum score of 85% with room to spare, at about 1/20 of Sonnet's cost.
- Its one failure (`mccarthy-job`) was a wrong detail that a stronger model fixed. It isn't a pattern in our questions.
- Visitors see the first words in under 4 seconds, which matters more for the web app than the last 5%.

## What we gave up

- About one answer in twenty is less accurate than the bigger models would give.
- The local model keeps data on the laptop, but was slower and missed citations on several answers.

## Revisit when

- The eval score drops below 90% for two runs in a row.
- We add harder, multi-step questions to the eval set.
- A new model or a price change comes out.
