"""SARIF v2.1.0 report generator for LeakGuard.

Generates standard SARIF JSON compatible with GitHub Code Scanning, GitLab SAST,
and VS Code SARIF viewers. Every result includes exact source locations,
rule metadata, XAI confidence breakdowns, and counterfactual remediation suggestions.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from .scoring import ScoredSite

SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
TOOL_NAME = "LeakGuard"
TOOL_VERSION = "0.1.0"
TOOL_HOMEPAGE = "https://github.com/codegate/leakguard"


def _build_rule(rule_id: str, short_desc: str, full_desc: str) -> Dict[str, Any]:
    return {
        "id": rule_id,
        "name": rule_id.replace("-", ""),
        "shortDescription": {"text": short_desc},
        "fullDescription": {"text": full_desc},
        "defaultConfiguration": {"level": "error" if "LEAK" in rule_id else "warning"},
        "help": {
            "text": f"{full_desc}\nRemediation: Ensure resources are released on all exit paths using 'with' or 'finally'.",
            "markdown": f"### {short_desc}\n\n{full_desc}\n\n**Remediation:** Ensure resources are released on all exit paths using `with` or `finally`.",
        },
        "properties": {
            "tags": ["security", "reliability", "resource-leak", "cwe-775", "cwe-404"]
        },
    }


RULES = {
    "LG-LEAK-01": _build_rule(
        "LG-LEAK-01",
        "Deterministic Resource Leak",
        "A resource is acquired and provably never closed along one or more reachable execution paths.",
    ),
    "LG-LEAK-02": _build_rule(
        "LG-LEAK-02",
        "High Confidence Probabilistic Resource Leak",
        "Static path analysis and machine-learning confidence scoring indicate a high probability of resource leakage.",
    ),
    "LG-WARN-01": _build_rule(
        "LG-WARN-01",
        "Exception Path Resource Leak",
        "Resource is closed on normal execution paths but leaks if an unhandled exception is raised in between.",
    ),
}


def create_sarif_report(scored_sites: Sequence[ScoredSite], root_dir: str = "") -> Dict[str, Any]:
    """Assemble SARIF v2.1.0 log from a sequence of ScoredSites."""
    results: List[Dict[str, Any]] = []

    for item in scored_sites:
        if item.final_verdict == "SAFE":
            continue

        site = item.site
        if item.final_verdict == "DEFINITE_LEAK":
            rule_id = "LG-LEAK-01"
            level = "error"
        elif item.final_verdict == "LIKELY_LEAK":
            rule_id = "LG-LEAK-02"
            level = "error"
        else:  # POSSIBLE_LEAK
            rule_id = "LG-WARN-01"
            level = "warning"

        # Construct Markdown body containing XAI Explainability
        explanation_md = [
            f"**LeakGuard Verdict:** `{item.final_verdict}` (Rule: `{site.verdict}`)",
            f"- **Resource:** `{site.call}` (Type: `{site.resource_type}`)",
            f"- **Handle:** `{site.handle}`",
            f"- **Leak Probability P(leak):** `{item.p_leak:.1%}` | **Risk Score:** `{item.risk:.2f}` (Exposure: `{item.exposure:.1f}`)",
            "\n**Explainable AI Evidence & Attributions:**",
        ]
        for line in item.evidence_lines:
            explanation_md.append(f"- {line}")
        for attr in item.attributions[:4]:
            sign = "+" if attr.contribution > 0 else ""
            explanation_md.append(f"- *{attr.description}*: `{sign}{attr.contribution:.2f}` log-odds contribution")

        explanation_md.append(f"\n**Fix Suggestion:** {item.fix_suggestion}")
        explanation_md.append(
            f"- **Counterfactual Impact:** If wrapped in context manager, risk drops to `{item.counterfactual_risk:.2f}`."
        )

        message_text = f"Unclosed {site.resource_type} resource '{site.handle}' acquired via '{site.call}' (P(leak)={item.p_leak:.1%}, Risk={item.risk:.2f}). {item.fix_suggestion}"
        message_markdown = "\n".join(explanation_md)

        # File path formatting
        file_uri = item.filename.replace("\\", "/")
        if root_dir:
            file_uri = file_uri.replace(root_dir.replace("\\", "/") + "/", "")

        result = {
            "ruleId": rule_id,
            "ruleIndex": list(RULES.keys()).index(rule_id),
            "level": level,
            "message": {
                "text": message_text,
                "markdown": message_markdown,
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": file_uri,
                            "uriBaseId": "%SRCROOT%",
                        },
                        "region": {
                            "startLine": site.line,
                            "startColumn": 1,
                        },
                    }
                }
            ],
            "properties": {
                "verdict": item.final_verdict,
                "p_leak": item.p_leak,
                "risk": item.risk,
                "exposure": item.exposure,
                "resource_type": site.resource_type,
            },
        }
        results.append(result)

    sarif_log = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "version": TOOL_VERSION,
                        "informationUri": TOOL_HOMEPAGE,
                        "rules": list(RULES.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return sarif_log


def write_sarif(path: str, scored_sites: Sequence[ScoredSite], root_dir: str = "") -> None:
    report = create_sarif_report(scored_sites, root_dir=root_dir)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
