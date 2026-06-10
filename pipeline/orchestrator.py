from __future__ import annotations

import asyncio
import sys

from agents.documentation import DocumentationAgent
from agents.moderator import ModeratorAgent
from agents.performance import PerformanceAgent
from agents.security import SecurityAgent
from agents.static_analysis import StaticAnalysisAgent
from agents.test_coverage import TestCoverageAgent
from protocol.consensus import ConflictDetector
from protocol.debate import DebateEngine
from protocol.message import AgentRole, Finding, ReviewResult


class Orchestrator:
    def __init__(self) -> None:
        self.specialists = {
            AgentRole.security: SecurityAgent(),
            AgentRole.performance: PerformanceAgent(),
            AgentRole.static: StaticAnalysisAgent(),
            AgentRole.test_coverage: TestCoverageAgent(),
            AgentRole.documentation: DocumentationAgent(),
        }
        self.moderator = ModeratorAgent()
        self.conflict_detector = ConflictDetector()
        self.debate_engine = DebateEngine()

    async def review(
        self,
        code: str,
        filename: str,
        diff: str | None = None,
    ) -> ReviewResult:
        # Phase 1: parallel specialist analysis
        print(f"[phase 1/4] dispatching {len(self.specialists)} specialist agents in parallel...", file=sys.stderr, flush=True)

        async def _run_agent(role, agent):
            print(f"  → {role.value}: analyzing...", file=sys.stderr, flush=True)
            try:
                findings = await asyncio.wait_for(agent.analyze(code, filename, diff), timeout=45)
            except asyncio.TimeoutError:
                print(f"  ✗ {role.value}: timed out", file=sys.stderr, flush=True)
                return []
            print(f"  ✓ {role.value}: {len(findings)} finding(s)", file=sys.stderr, flush=True)
            return findings

        results = await asyncio.gather(
            *[_run_agent(role, agent) for role, agent in self.specialists.items()]
        )
        all_findings: dict[str, Finding] = {
            f.id: f for findings in results for f in findings
        }
        print(f"[phase 1/4] complete — {len(all_findings)} total findings", file=sys.stderr, flush=True)

        # Phase 2: conflict detection
        print("[phase 2/4] detecting conflicts...", file=sys.stderr, flush=True)
        conflicts = self.conflict_detector.detect(all_findings)
        print(f"[phase 2/4] {len(conflicts)} conflict(s) found", file=sys.stderr, flush=True)

        # Phase 3: debate rounds on conflicted findings
        print("[phase 3/4] running debate rounds...", file=sys.stderr, flush=True)
        transcripts = await self._run_debate_with_logging(all_findings, conflicts)

        # Track which conflicts stayed unresolved after debate
        unresolved = [
            c for c in conflicts
            if not self._conflict_resolved(c.finding_a.id, c.finding_b.id, transcripts)
        ]

        actual_rounds = max(
            (m.round for msgs in transcripts.values() for m in msgs),
            default=0,
        )
        print(f"[phase 3/4] debate complete — {len(conflicts) - len(unresolved)} resolved, {len(unresolved)} unresolved", file=sys.stderr, flush=True)

        # Phase 4: moderator synthesis
        print("[phase 4/4] moderator synthesizing consensus...", file=sys.stderr, flush=True)
        result = await self.moderator.synthesize(
            all_findings, transcripts, unresolved, filename,
            total_conflicts=len(conflicts),
            actual_debate_rounds=actual_rounds,
        )
        print(f"[phase 4/4] done — {result.total_findings} findings, {result.metrics.requires_human_review} need human review", file=sys.stderr, flush=True)
        return result

    async def _run_debate_with_logging(
        self,
        all_findings: dict[str, Finding],
        conflicts: list,
    ) -> dict:
        if not conflicts:
            print("  → no conflicts to debate", file=sys.stderr, flush=True)
            return {}
        for i, conflict in enumerate(conflicts, 1):
            print(
                f"  → conflict {i}/{len(conflicts)}: "
                f"{conflict.finding_a.category.value} vs {conflict.finding_b.category.value} "
                f"({conflict.conflict_type})",
                flush=True,
            )
        transcripts = await self.debate_engine.run(all_findings, conflicts, self.specialists)
        rounds_run = max(
            (m.round for msgs in transcripts.values() for m in msgs),
            default=0,
        )
        print(f"  → {rounds_run} debate round(s) completed", file=sys.stderr, flush=True)
        return transcripts

    def _conflict_resolved(
        self,
        fid_a: str,
        fid_b: str,
        transcripts: dict[str, list],
    ) -> bool:
        msgs_a = transcripts.get(fid_a, [])
        msgs_b = transcripts.get(fid_b, [])
        if not msgs_a or not msgs_b:
            return False
        last_a = msgs_a[-1]
        last_b = msgs_b[-1]
        return last_a.stance.value == "agree" or last_b.stance.value == "agree"
