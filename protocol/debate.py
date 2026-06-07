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

        for conflict in conflicts:
            fid_a = conflict.finding_a.id
            fid_b = conflict.finding_b.id
            transcripts.setdefault(fid_a, [])
            transcripts.setdefault(fid_b, [])

            agent_a = agents.get(conflict.finding_a.category)
            agent_b = agents.get(conflict.finding_b.category)

            if not agent_a or not agent_b:
                continue

            for round_num in range(1, settings.max_debate_rounds + 1):
                a_response, b_response = await asyncio.gather(
                    agent_a.respond_to_challenge(conflict.finding_a, conflict.finding_b, round_num),
                    agent_b.respond_to_challenge(conflict.finding_b, conflict.finding_a, round_num),
                )

                msg_a = DebateMessage(
                    round=round_num,
                    agent=conflict.finding_a.category,
                    target_finding_id=fid_a,
                    challenger_finding_id=fid_b,
                    stance=DebateStance(a_response.get("stance", "maintain")),
                    reasoning=a_response.get("reasoning", ""),
                    updated_confidence=float(a_response.get("updated_confidence", conflict.finding_a.confidence)),
                )
                msg_b = DebateMessage(
                    round=round_num,
                    agent=conflict.finding_b.category,
                    target_finding_id=fid_b,
                    challenger_finding_id=fid_a,
                    stance=DebateStance(b_response.get("stance", "maintain")),
                    reasoning=b_response.get("reasoning", ""),
                    updated_confidence=float(b_response.get("updated_confidence", conflict.finding_b.confidence)),
                )
                transcripts[fid_a].append(msg_a)
                transcripts[fid_b].append(msg_b)

                # Update confidence in the live finding for subsequent rounds
                conflict.finding_a = conflict.finding_a.model_copy(
                    update={"confidence": msg_a.updated_confidence}
                )
                conflict.finding_b = conflict.finding_b.model_copy(
                    update={"confidence": msg_b.updated_confidence}
                )

                # Early termination if both agents agree
                if msg_a.stance == DebateStance.agree and msg_b.stance == DebateStance.agree:
                    break

        return transcripts
