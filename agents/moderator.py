from __future__ import annotations

import json

from openai import AsyncOpenAI

from config import settings
from protocol.message import (
    AgentRole,
    Conflict,
    ConsensusResult,
    DebateMessage,
    Finding,
    ReviewMetrics,
    ReviewResult,
)


class ModeratorAgent:
    role = AgentRole.moderator
    model = settings.moderator_model

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
        )

    async def synthesize(
        self,
        all_findings: dict[str, Finding],
        debate_transcripts: dict[str, list[DebateMessage]],
        unresolved_conflicts: list[Conflict],
        filename: str,
    ) -> ReviewResult:
        consensus_results = []
        for fid, finding in all_findings.items():
            transcript = debate_transcripts.get(fid, [])
            result = await self._build_consensus(finding, transcript)
            consensus_results.append(result)

        metrics = ReviewMetrics(
            agents_used=5,
            debate_rounds=settings.max_debate_rounds,
            conflicts_detected=len(unresolved_conflicts) + sum(
                1 for r in consensus_results if r.debate_transcript
            ),
            conflicts_resolved=sum(
                1 for r in consensus_results if r.debate_transcript and r.consensus_reached
            ),
            high_confidence_findings=sum(
                1 for r in consensus_results if r.finding.confidence >= 0.8
            ),
            requires_human_review=sum(1 for r in consensus_results if r.requires_human_review),
        )

        return ReviewResult(
            filename=filename,
            total_findings=len(consensus_results),
            consensus_findings=sorted(
                consensus_results,
                key=lambda r: (
                    ["critical", "high", "medium", "low", "info"].index(r.finding.severity),
                    -r.finding.confidence,
                ),
            ),
            unresolved_conflicts=unresolved_conflicts,
            metrics=metrics,
        )

    async def _build_consensus(
        self,
        finding: Finding,
        transcript: list[DebateMessage],
    ) -> ConsensusResult:
        if not transcript:
            return ConsensusResult(
                finding=finding,
                consensus_reached=True,
                agreement_score=finding.confidence,
                supporting_agents=[finding.category],
                debate_transcript=[],
                resolution="No conflict — sole finding on this location.",
                requires_human_review=finding.confidence < 0.5,
            )

        debate_summary = "\n".join(
            f"Round {m.round} | {m.agent.value}: {m.stance.value} — {m.reasoning}"
            for m in transcript
        )
        prompt = (
            f"Finding:\n{finding.model_dump_json(indent=2)}\n\n"
            f"Debate transcript:\n{debate_summary}\n\n"
            "Based on the debate, return a JSON object with:\n"
            '- "consensus_reached": bool\n'
            '- "agreement_score": float 0.0-1.0\n'
            '- "resolution": string explaining the final verdict\n'
            '- "requires_human_review": bool\n'
            '- "updated_confidence": float 0.0-1.0 for the finding\n'
        )
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior engineering lead arbitrating a code review debate. "
                        "Be decisive. Weigh technical merit, not agent seniority. "
                        "Require human review only when expert disagreement is genuine and consequential."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = json.loads(response.choices[0].message.content)
        updated_finding = finding.model_copy(
            update={"confidence": raw.get("updated_confidence", finding.confidence)}
        )
        supporting = list({m.agent for m in transcript if m.stance.value != "agree"})
        supporting.append(finding.category)

        return ConsensusResult(
            finding=updated_finding,
            consensus_reached=raw["consensus_reached"],
            agreement_score=raw["agreement_score"],
            supporting_agents=supporting,
            debate_transcript=transcript,
            resolution=raw["resolution"],
            requires_human_review=raw["requires_human_review"],
        )
