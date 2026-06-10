from __future__ import annotations

import asyncio

from config import settings
from protocol.message import (
    AgentRole,
    Conflict,
    DebateMessage,
    DebateStance,
    Finding,
)


class DebateEngine:
    async def run(
        self,
        all_findings: dict[str, Finding],
        conflicts: list[Conflict],
        agents: dict[AgentRole, object],
    ) -> dict[str, list[DebateMessage]]:
        """Returns mapping of finding_id -> debate messages for that finding."""
        transcripts: dict[str, list[DebateMessage]] = {}

        async def _debate_one(conflict: Conflict) -> None:
            fid_a = conflict.finding_a.id
            fid_b = conflict.finding_b.id
            transcripts.setdefault(fid_a, [])
            transcripts.setdefault(fid_b, [])

            agent_a = agents.get(conflict.finding_a.category)
            agent_b = agents.get(conflict.finding_b.category)
            if not agent_a or not agent_b:
                return

            a_response, b_response = await asyncio.gather(
                agent_a.respond_to_challenge(conflict.finding_a, conflict.finding_b, 1),
                agent_b.respond_to_challenge(conflict.finding_b, conflict.finding_a, 1),
            )
            transcripts[fid_a].append(DebateMessage(
                round=1, agent=conflict.finding_a.category,
                target_finding_id=fid_a, challenger_finding_id=fid_b,
                stance=DebateStance(a_response.get("stance", "maintain")),
                reasoning=a_response.get("reasoning", ""),
                updated_confidence=float(a_response.get("updated_confidence", conflict.finding_a.confidence)),
            ))
            transcripts[fid_b].append(DebateMessage(
                round=1, agent=conflict.finding_b.category,
                target_finding_id=fid_b, challenger_finding_id=fid_a,
                stance=DebateStance(b_response.get("stance", "maintain")),
                reasoning=b_response.get("reasoning", ""),
                updated_confidence=float(b_response.get("updated_confidence", conflict.finding_b.confidence)),
            ))

        await asyncio.gather(*[_debate_one(c) for c in conflicts])
        return transcripts
