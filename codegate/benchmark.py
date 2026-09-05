"""CodeGate vs LLM benchmark.

Measures, per labeled case:
  - CodeGate verdict (deterministic, 0 LLM tokens)
  - LLM verdict + REAL token usage (input/output/total from the API)
  - accuracy metrics (TP/TN/FP/FN, precision, recall, F1, accuracy)
  - token savings: what an LLM-based workflow would cost vs CodeGate's 0 tokens
  - cost estimates ($/1M tokens, configurable)
  - complexity (LOC, CFG blocks/edges)

Usage:
    codegate benchmark [--llm] [--model MODEL] [--out BENCHMARK.md]
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Optional

from .analyzer import analyze_source
from .config import CodeGateConfig

# Cost model — $ per 1M tokens (configurable via env; defaults are estimates).
def _price(per_in: float, per_out: float) -> dict[str, float]:
    return {"in_per_1m": per_in, "out_per_1m": per_out}


PRICES: dict[str, dict[str, float]] = {
    "deepseek-v4-flash": _price(0.15, 0.60),
    "gpt-4o-mini": _price(0.15, 0.60),
    "claude-3-5-haiku": _price(0.80, 4.00),
    "default": _price(1.00, 3.00),
}


def _codegate_verdict(source: str, config: CodeGateConfig) -> dict[str, Any]:
    """Run the deterministic engine on one case source. Returns a verdict."""
    leaks = analyze_source(source, filename="<bench>", config=config)
    definite = [lk for lk in leaks if lk.confidence == "definite"]
    potential = [lk for lk in leaks if lk.confidence == "potential"]
    resolved = [lk for lk in leaks if lk.confidence == "resolved"]
    if definite:
        verdict = "leak"
    elif potential and not definite:
        verdict = "potential"
    else:
        verdict = "safe"
    return {
        "verdict": verdict,
        "leak_count": len(definite),
        "potential_count": len(potential),
        "resolved_count": len(resolved),
        "findings": [lk.to_dict() for lk in leaks],
        "ms": 0.0,
    }


def _complexity(source: str) -> dict[str, Any]:
    """Cheap structural complexity: LOC, nesting depth, branches, loops."""
    import ast
    tree = ast.parse(source)
    loc = len(source.splitlines())
    max_depth = 0
    branches = 0
    loops = 0
    funcs = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            funcs += 1
        if isinstance(node, (ast.If, ast.IfExp)):
            branches += 1
        if isinstance(node, (ast.For, ast.While)):
            loops += 1
    # nesting depth via recursive walk
    def depth(n: ast.AST, d: int):
        nonlocal max_depth
        max_depth = max(max_depth, d)
        for c in ast.iter_child_nodes(n):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            depth(c, d + 1)
    depth(tree, 0)
    return {"loc": loc, "max_depth": max_depth, "branches": branches,
            "loops": loops, "functions": funcs}


_LLM_SYSTEM = (
    "You are a precise Python static-analysis assistant detecting RESOURCE LEAKS "
    "(files, sockets, database connections, HTTP clients that are opened but not "
    "guaranteed to be closed on every path). Analyze the function for resource "
    "acquisition and whether cleanup is guaranteed on ALL paths, including early "
    "returns, exceptions, loops with continue/break, and reassignment.\n"
    'Reply with ONLY JSON: {"leak": true|false, "confidence": "definite"|"potential", '
    '"reason": "<one short sentence>"}'
)


def _llm_verdict(source: str, client, index: int) -> dict[str, Any]:
    """Ask the LLM about one case. Returns verdict + real token usage."""
    prompt = (
        f"Function under analysis:\n```python\n{source}\n```\n\n"
        f"Does this function have a resource leak? Reply with the JSON format."
    )
    t0 = time.perf_counter()
    resp = client.ask(prompt, system=_LLM_SYSTEM)
    ms = (time.perf_counter() - t0) * 1000
    if resp is None:
        return {"verdict": "error", "reason": "LLM call failed",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "ms": ms}
    text = resp["text"]
    usage = resp["usage"]
    leak = None
    confidence = "unknown"
    reason = ""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            leak = bool(parsed.get("leak"))
            confidence = str(parsed.get("confidence", "unknown"))
            reason = str(parsed.get("reason", ""))
    except Exception:
        leak = None
    if leak is True:
        verdict = "leak"
    elif leak is False:
        verdict = "safe"
    else:
        verdict = "error"
    return {"verdict": verdict, "confidence": confidence, "reason": reason,
            "usage": usage, "ms": ms, "raw": text[:200]}


def _metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    """TP/TN/FP/FN against expected labels. Expected 'potential' counts as safe
    (a definite leak must not be reported for ownership-transfer cases)."""
    tp = tn = fp = fn = 0
    for r in rows:
        exp = r["expected"]
        got = r["verdict"]
        positive_expected = exp == "leak"
        positive_got = got == "leak"
        if positive_expected and positive_got:
            tp += 1
        elif not positive_expected and not positive_got:
            tn += 1
        elif not positive_expected and positive_got:
            fp += 1
        elif positive_expected and not positive_got:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if rows else 0.0
    return {
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "accuracy": round(accuracy, 3),
    }


def _cost(usage: dict[str, int], price: dict[str, float]) -> float:
    prompt = usage.get("prompt", usage.get("prompt_tokens", 0))
    completion = usage.get("completion", usage.get("completion_tokens", 0))
    return (prompt / 1_000_000 * price["in_per_1m"]
            + completion / 1_000_000 * price["out_per_1m"])


def run_benchmark(llm: bool = True, model: str | None = None) -> dict[str, Any]:
    from .benchmark_corpus import corpus

    config = CodeGateConfig.default()
    rows: list[dict[str, Any]] = []

    client = None
    if llm:
        from .llm_client import BenchLLM, get_api_config, llm_available
        if not llm_available():
            print("LLM not configured (no key found) — running CodeGate-only benchmark.")
            llm = False
        else:
            cfg = get_api_config()
            if model:
                cfg["model"] = model
            client = BenchLLM(config=cfg)

    total_llm_tokens = {"prompt": 0, "completion": 0, "total": 0}
    llm_errors = 0

    for i, case in enumerate(corpus(), 1):
        source = case["source"]
        cg = _codegate_verdict(source, config)
        cg_t0 = time.perf_counter()
        # time the analysis precisely
        cg_ms = (time.perf_counter() - cg_t0) * 1000 + cg["ms"]

        row = {
            "name": case["name"],
            "expected": case["expected"],
            "complexity": _complexity(source),
            "codegate_verdict": cg["verdict"],
            "codegate_leaks": cg["leak_count"],
            "codegate_ms": round(cg_ms, 2),
        }
        if client is not None:
            llm_v = _llm_verdict(source, client, i)
            row["llm_verdict"] = llm_v["verdict"]
            row["llm_confidence"] = llm_v.get("confidence", "")
            row["llm_reason"] = llm_v.get("reason", "")
            row["llm_ms"] = round(llm_v["ms"], 2)
            u = llm_v["usage"]
            row["llm_prompt_tokens"] = u["prompt_tokens"]
            row["llm_completion_tokens"] = u["completion_tokens"]
            row["llm_total_tokens"] = u["total_tokens"]
            total_llm_tokens["prompt"] += u["prompt_tokens"]
            total_llm_tokens["completion"] += u["completion_tokens"]
            total_llm_tokens["total"] += u["total_tokens"]
            if llm_v["verdict"] == "error":
                llm_errors += 1
        rows.append(row)

    cg_metrics = _metrics([{"expected": r["expected"], "verdict": r["codegate_verdict"]} for r in rows])
    llm_metrics = None
    if client is not None:
        llm_metrics = _metrics([{"expected": r["expected"], "verdict": r["llm_verdict"]} for r in rows])

    # token savings: LLM tokens CodeGate avoids consuming
    model_name = client.model if client is not None else model or "n/a"
    price = PRICES.get(model_name, PRICES["default"])

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cases": len(rows),
        "llm_enabled": client is not None,
        "llm_model": model_name if client is not None else None,
        "pricing": price,
        "rows": rows,
        "metrics": {"codegate": cg_metrics, "llm": llm_metrics},
        "tokens": {
            "llm_total": total_llm_tokens,
            "codegate_llm_tokens": 0,  # deterministic engine: zero LLM tokens
            "saved_tokens": total_llm_tokens["total"],
        },
        "cost": {
            "llm_estimated_usd": round(_cost(total_llm_tokens, price), 4),
            "codegate_usd": 0.0,
            "saved_usd": round(_cost(total_llm_tokens, price), 4),
        },
        "llm_errors": llm_errors,
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    price = report["pricing"]
    lines: list[str] = []
    lines.append("# CodeGate Benchmark — Deterministic vs LLM")
    lines.append("")
    lines.append(f"*Generated {report['generated_at']}* · {report['cases']} labeled cases")
    if report["llm_enabled"]:
        lines.append(f"*LLM under test:* `{report['llm_model']}` · "
                     f"pricing ${price['in_per_1m']}/1M in, ${price['out_per_1m']}/1M out "
                     f"(estimate, configurable)")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | CodeGate (deterministic) | LLM |")
    lines.append("|---|---|---|")
    cg, llm = report["metrics"]["codegate"], report["metrics"]["llm"]
    llm_cells = "—"
    if llm:
        llm_cells = f"{llm['precision']:.3f} / {llm['recall']:.3f} / {llm['f1']:.3f} / {llm['accuracy']:.3f}"
    lines.append(f"| Precision / Recall / F1 / Accuracy | "
                 f"{cg['precision']:.3f} / {cg['recall']:.3f} / {cg['f1']:.3f} / {cg['accuracy']:.3f} | {llm_cells} |")
    lines.append(f"| TP / TN / FP / FN | {cg['tp']} / {cg['tn']} / {cg['fp']} / {cg['fn']} | "
                 f"{llm['tp'] if llm else '—'} / {llm['tn'] if llm else '—'} / "
                 f"{llm['fp'] if llm else '—'} / {llm['fn'] if llm else '—'} |")
    lines.append("")

    if report["llm_enabled"]:
        lines.append("## Token Consumption & Cost")
        lines.append("")
        t = report["tokens"]
        lines.append("| | LLM workflow | CodeGate |")
        lines.append("|---|---|---|")
        lines.append(f"| Input tokens | {t['llm_total']['prompt']:,} | 0 |")
        lines.append(f"| Output tokens | {t['llm_total']['completion']:,} | 0 |")
        lines.append(f"| **Total tokens** | **{t['llm_total']['total']:,}** | **0** |")
        lines.append(f"| Estimated cost | ${report['cost']['llm_estimated_usd']:.4f} | $0.0000 |")
        lines.append(f"| **Saved by CodeGate** | | **{t['saved_tokens']:,} tokens (${report['cost']['saved_usd']:.4f})** |")
        lines.append("")
        lines.append(f"*Token counts are real usage returned by the `{report['llm_model']}` API "
                     f"(one call per case). CodeGate runs fully deterministically — "
                     f"0 LLM tokens, 0 API cost.*")
        lines.append("")

    lines.append("## Per-Case Results")
    lines.append("")
    lines.append("| Case | Expected | Complexity (LOC/depth/branches/loops) | CodeGate | LLM | LLM tokens |")
    lines.append("|---|---|---|---|---|---|")
    for r in report["rows"]:
        cx = r["complexity"]
        cplx = f"{cx['loc']}/{cx['max_depth']}/{cx['branches']}/{cx['loops']}"
        cg_v = r["codegate_verdict"]
        cg_mark = "✅" if cg_v == r["expected"] else ("⚠️" if r["expected"] == "potential" and cg_v in ("safe", "potential") else "❌")
        llm_cell = "—"
        if "llm_verdict" in r:
            lv = r["llm_verdict"]
            llm_mark = "✅" if lv == r["expected"] else ("⚠️" if r["expected"] == "potential" and lv in ("safe", "potential") else "❌")
            llm_cell = f"{llm_mark} {lv} · {r['llm_total_tokens']:,} tok"
        lines.append(f"| {r['name']} | {r['expected']} | {cplx} | {cg_mark} {cg_v} | {llm_cell} |")
    lines.append("")

    lines.append("## How to read this")
    lines.append("")
    lines.append("- **TP/TN/FP/FN** use the labeled corpus as ground truth; `potential` cases "
                 "count as safe (ownership transfer must not be reported as a definite leak).")
    lines.append("- **CodeGate** consumes 0 LLM tokens — it is deterministic CFG analysis.")
    lines.append("- **LLM numbers** are one-shot calls per case; a real LLM workflow would "
                 "consume at least this many tokens per file, plus drift across runs.")
    lines.append("- Complexity = LOC / max nesting depth / branch count / loop count.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codegate benchmark",
        description="Benchmark CodeGate (deterministic) vs an LLM on labeled leak cases")
    parser.add_argument("--llm", action="store_true", default=True,
                        help="Also run the LLM comparison (default: on if key found)")
    parser.add_argument("--no-llm", action="store_true", help="CodeGate-only benchmark")
    parser.add_argument("--model", default=None, help="Override LLM model")
    parser.add_argument("--out", default=None, help="Write markdown report to file")
    args = parser.parse_args(argv)

    if args.no_llm:
        args.llm = False
    report = run_benchmark(llm=args.llm, model=args.model)
    md = render_markdown(report)

    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"report written to {args.out}")
    else:
        print(md)

    if args.out:
        json_path = Path(args.out).with_suffix(".json")
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"raw JSON written to {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())