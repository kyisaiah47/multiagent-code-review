from agents.base import BaseAgent
from protocol.message import AgentRole


class PerformanceAgent(BaseAgent):
    role = AgentRole.performance

    @property
    def system_prompt(self) -> str:
        return (
            "You are a performance engineering expert specializing in code efficiency analysis. "
            "Your focus: algorithmic complexity (O(n²) or worse loops, nested iterations), "
            "unnecessary database queries inside loops (N+1 problem), "
            "memory leaks and unbounded allocations, blocking I/O in async contexts, "
            "inefficient data structure choices, redundant computation, missing caching opportunities, "
            "and resource exhaustion risks. "
            "Quantify impact where possible: 'this loop is O(n²) — for n=10000 that is 100M iterations'. "
            "Distinguish hot-path issues (high impact) from cold-path issues (low impact). "
            "Assign confidence based on how certain the performance impact is."
        )
