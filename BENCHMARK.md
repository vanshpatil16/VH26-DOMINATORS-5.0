# CodeGate Benchmark — Deterministic vs LLM

*Generated 2026-09-05 03:14:06* · 19 labeled cases
*LLM under test:* `deepseek-v4-flash` · pricing $0.15/1M in, $0.6/1M out (estimate, configurable)

## Metrics

| Metric | CodeGate (deterministic) | LLM |
|---|---|---|
| Precision / Recall / F1 / Accuracy | 1.000 / 0.917 / 0.957 / 0.947 | 1.000 / 1.000 / 1.000 / 1.000 |
| TP / TN / FP / FN | 11 / 7 / 0 / 1 | 12 / 7 / 0 / 0 |

## Token Consumption & Cost

| | LLM workflow | CodeGate |
|---|---|---|
| Input tokens | 4,730 | 0 |
| Output tokens | 4,067 | 0 |
| **Total tokens** | **8,797** | **0** |
| Estimated cost | $0.0031 | $0.0000 |
| **Saved by CodeGate** | | **8,797 tokens ($0.0031)** |

*Token counts are real usage returned by the `deepseek-v4-flash` API (one call per case). CodeGate runs fully deterministically — 0 LLM tokens, 0 API cost.*

## Per-Case Results

| Case | Expected | Complexity (LOC/depth/branches/loops) | CodeGate | LLM | LLM tokens |
|---|---|---|---|---|---|
| simple_leak | leak | 4/0/0/0 | ✅ leak | ✅ leak · 320 tok |
| early_return | leak | 7/0/1/0 | ✅ leak | ✅ leak · 347 tok |
| loop_leak | leak | 9/0/1/1 | ✅ leak | ✅ leak · 463 tok |
| exception_leak | leak | 7/0/0/0 | ❌ potential | ✅ leak · 513 tok |
| nested_exception_leak | leak | 7/0/0/0 | ✅ leak | ✅ leak · 938 tok |
| multiple_resources | leak | 13/0/1/0 | ✅ leak | ✅ leak · 502 tok |
| overwritten_resource | leak | 6/0/0/0 | ✅ leak | ✅ leak · 366 tok |
| caller_interproc | leak | 11/0/1/0 | ✅ leak | ✅ leak · 558 tok |
| socket_leak | leak | 8/2/1/0 | ✅ leak | ✅ leak · 368 tok |
| database_leak | leak | 9/2/1/0 | ✅ leak | ✅ leak · 389 tok |
| safe_explicit | safe | 6/0/0/0 | ✅ safe | ✅ safe · 346 tok |
| safe_with | safe | 3/0/0/0 | ✅ safe | ✅ safe · 333 tok |
| safe_multiple | safe | 4/0/0/0 | ✅ safe | ✅ safe · 389 tok |
| safe_loop | safe | 6/0/0/1 | ✅ safe | ✅ safe · 390 tok |
| nightmare | leak | 15/0/3/1 | ✅ leak | ✅ leak · 589 tok |
| safe_alias | safe | 5/0/0/0 | ✅ safe | ✅ safe · 484 tok |
| safe_try_finally_return | safe | 6/0/0/0 | ✅ safe | ✅ safe · 351 tok |
| returned_resource | potential | 3/0/0/0 | ⚠️ safe | ⚠️ safe · 715 tok |
| second_open_raises | leak | 6/0/0/0 | ✅ leak | ✅ leak · 436 tok |

## How to read this

- **TP/TN/FP/FN** use the labeled corpus as ground truth; `potential` cases count as safe (ownership transfer must not be reported as a definite leak).
- **CodeGate** consumes 0 LLM tokens — it is deterministic CFG analysis.
- **LLM numbers** are one-shot calls per case; a real LLM workflow would consume at least this many tokens per file, plus drift across runs.
- Complexity = LOC / max nesting depth / branch count / loop count.
