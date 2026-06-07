"""Benchmark: run single-agent vs multi-agent on known-issue files, compare recall."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.orchestrator import Orchestrator
from protocol.message import Finding, ReviewResult


@dataclass
class KnownIssue:
    file: str
    line: int
    category: str
    description: str


@dataclass
class BenchmarkResult:
    filename: str
    known_issues: list[KnownIssue]
    multi_agent_findings: list[Finding]
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0

    def compute(self) -> None:
        matched: set[int] = set()
        for finding in self.multi_agent_findings:
            for i, issue in enumerate(self.known_issues):
                if i in matched:
                    continue
                if issue.category == finding.category.value and abs((finding.line or 0) - issue.line) <= 5:
                    matched.add(i)
                    self.true_positives += 1
                    break
            else:
                self.false_positives += 1

        self.false_negatives = len(self.known_issues) - self.true_positives
        total_pred = self.true_positives + self.false_positives
        self.precision = self.true_positives / total_pred if total_pred else 0.0
        self.recall = self.true_positives / len(self.known_issues) if self.known_issues else 0.0


KNOWN_ISSUES: dict[str, list[KnownIssue]] = {
    "samples/vulnerable.py": [
        KnownIssue("samples/vulnerable.py", 8, "security", "SQL injection via string concat"),
        KnownIssue("samples/vulnerable.py", 22, "security", "hardcoded credentials"),
        KnownIssue("samples/vulnerable.py", 35, "performance", "N+1 query in loop"),
        KnownIssue("samples/vulnerable.py", 48, "static", "swallowed exception"),
        KnownIssue("samples/vulnerable.py", 61, "security", "path traversal"),
    ]
}


async def run_benchmark(samples_dir: Path = Path("benchmarks/samples")) -> list[BenchmarkResult]:
    orchestrator = Orchestrator()
    results = []

    for filepath_str, known in KNOWN_ISSUES.items():
        path = samples_dir.parent.parent / filepath_str
        if not path.exists():
            print(f"Sample not found: {path}, skipping")
            continue

        code = path.read_text()
        print(f"Benchmarking {path.name}...")
        review: ReviewResult = await orchestrator.review(code, path.name)

        br = BenchmarkResult(
            filename=path.name,
            known_issues=known,
            multi_agent_findings=[r.finding for r in review.consensus_findings],
        )
        br.compute()
        results.append(br)

        print(
            f"  precision={br.precision:.0%}  recall={br.recall:.0%}  "
            f"TP={br.true_positives}  FP={br.false_positives}  FN={br.false_negatives}"
        )

    return results


if __name__ == "__main__":
    asyncio.run(run_benchmark())
