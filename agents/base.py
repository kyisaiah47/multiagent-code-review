from __future__ import annotations

import json
from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from config import settings
from protocol.message import AgentRole, Finding


class BaseAgent(ABC):
    role: AgentRole
    model: str = settings.specialist_model

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
        )

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    async def analyze(self, code: str, filename: str, diff: str | None = None) -> list[Finding]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self._user_prompt(code, filename, diff)},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2048,
        )
        raw = json.loads(response.choices[0].message.content)
        findings = []
        for f in raw.get("findings", []):
            try:
                f.setdefault("category", self.role.value)
                findings.append(Finding(**f))
            except Exception:
                continue
        return findings

    async def respond_to_challenge(
        self,
        my_finding: Finding,
        challenger_finding: Finding,
        debate_round: int,
    ) -> dict:
        prompt = (
            f"DEBATE ROUND {debate_round}\n\n"
            f"YOUR FINDING:\n{my_finding.model_dump_json(indent=2)}\n\n"
            f"CHALLENGER FINDING (from {challenger_finding.category} agent):\n"
            f"{challenger_finding.model_dump_json(indent=2)}\n\n"
            "Respond with a JSON object containing:\n"
            '- "stance": one of "agree", "maintain", "concede_partial"\n'
            '- "reasoning": your technical justification (be specific)\n'
            '- "updated_confidence": float 0.0-1.0 for your finding after considering the challenge\n'
        )
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=256,
        )
        return json.loads(response.choices[0].message.content)

    def _user_prompt(self, code: str, filename: str, diff: str | None) -> str:
        parts = [f"File: {filename}\n\n```\n{code}\n```"]
        if diff:
            parts.append(f"\nGit diff:\n```diff\n{diff}\n```")
        parts.append(
            "\nReturn a JSON object with a 'findings' array (max 2 findings, most important only). "
            "Each finding must have: file, line (int or null), line_end (int or null), severity "
            "(critical/high/medium/low/info), title, description, suggestion, "
            "confidence (0.0-1.0), evidence."
        )
        return "\n".join(parts)
