from __future__ import annotations

import asyncio

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
        results = await asyncio.gather(
            *[agent.analyze(code, filename, diff) for agent in self.specialists.values()]
        )
        all_findings: dict[str, Finding] = {
            f.id: f for findings in results for f in findings
        }

        # Phase 2: conflict detection
        conflicts = self.conflict_detector.detect(all_findings)

        # Phase 3: debate rounds on conflicted findings
        transcripts = await self.debate_engine.run(all_findings, conflicts, self.specialists)

        # Track which conflicts stayed unresolved after debate
        unresolved = [
            c for c in conflicts
            if not self._conflict_resolved(c.finding_a.id, c.finding_b.id, transcripts)
        ]

        # Phase 4: moderator synthesis
        return await self.moderator.synthesize(
            all_findings, transcripts, unresolved, filename
        )

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
