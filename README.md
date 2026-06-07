# Multi-Agent Code Review

**Multi-agent code review system powered by specialist AI agents — built for the [Global AI Hackathon with Qwen Cloud](https://qwenhackathon.devpost.com/).**

Track 3: Agent Society · Qwen Cloud

---

## What it does

Five specialist AI agents review your code concurrently, debate findings, and produce a consensus report — flagging what needs human attention when they disagree.

| Agent | Focus |
|---|---|
| Static Analysis | Code smells, dead code, complexity, style |
| Security | OWASP Top 10, injection, hardcoded secrets, auth flaws |
| Performance | Algorithmic complexity, N+1 queries, memory leaks |
| Documentation | Missing docstrings, unclear APIs, comment coverage |
| Test Coverage | Missing test cases, untested branches, edge cases |

A **Moderator** runs up to 3 debate rounds when agents conflict. Findings that can't be resolved are escalated for human review.

## Architecture

```
Input: source file + optional git diff
    │
    ▼
Orchestrator (qwen-max)
    │  dispatches concurrently
    ├── StaticAnalysisAgent (qwen-plus)
    ├── SecurityAgent       (qwen-plus)
    ├── PerformanceAgent    (qwen-plus)
    ├── DocumentationAgent  (qwen-plus)
    └── TestCoverageAgent   (qwen-plus)
    │
    ▼
ModeratorAgent (qwen-max)
    │  up to 3 debate rounds on conflicting findings
    ▼
ConsensusResult
    ├── consensus_findings  (agreed findings with severity + confidence)
    ├── unresolved_conflicts (escalated for human review)
    └── metrics             (conflicts detected/resolved, human review flag)
```

## Usage

### CLI

```bash
python main.py review path/to/file.py
python main.py review path/to/file.py --diff "$(git diff HEAD~1 path/to/file.py)"
```

### API server

```bash
python main.py serve
# POST http://localhost:8000/review
```

## Getting started

### 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
```

```env
QWEN_API_KEY=your_key_here
```

### 3. Run

```bash
python main.py review yourfile.py
```

## Output

The CLI renders a rich terminal report: a summary table of all findings (severity, agent, line, confidence, consensus status) followed by detailed panels for each finding with description, suggestion, and evidence. Unresolved conflicts are called out separately for human review.
