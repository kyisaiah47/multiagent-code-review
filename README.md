<div align="center">

<!-- BANNER_PLACEHOLDER -->

# 🤝 Multi-Agent Code Review

**Five specialist AI agents review your code concurrently, debate findings, and deliver a consensus report.**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Qwen](https://img.shields.io/badge/Qwen%20Cloud-AI%20Powered-6B46C1?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

</div>

<br/>

Multi-Agent Code Review orchestrates five specialist AI agents — Static Analysis, Security, Performance, Documentation, and Test Coverage — that concurrently inspect your code and debate conflicting findings. A Moderator agent runs up to three rounds of consensus-building, escalating anything unresolved for human review. Built for the [Global AI Hackathon with Qwen Cloud](https://qwenhackathon.devpost.com/) (Track 3: Agent Society).

## ✨ Features

- **Concurrent specialist agents** — five agents review your code in parallel, each focused on a distinct concern (style, security, performance, docs, and test coverage)
- **Debate-driven consensus** — a Moderator agent runs up to 3 rounds of structured debate to resolve conflicting findings before surfacing them
- **Human escalation** — unresolved conflicts are flagged explicitly for human review so nothing slips through
- **CLI + REST API** — review files directly from the terminal or integrate via a local FastAPI server
- **Git diff support** — pass `git diff` output alongside a file to focus review on only what changed
- **Rich terminal output** — findings rendered as a severity-sorted table with per-finding panels showing description, suggestion, evidence, and consensus status

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Orchestration & Moderation | `qwen-max` |
| Specialist Agents | `qwen-plus` (×5) |
| API Server | FastAPI |
| Terminal UI | Rich |
| Language | Python 3 |

### Architecture

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
    ├── consensus_findings   (agreed findings with severity + confidence)
    ├── unresolved_conflicts (escalated for human review)
    └── metrics              (conflicts detected/resolved, human review flag)
```

## 🚀 Getting Started

### 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Set QWEN_API_KEY=your_key_here in .env
```

### 3. Review a file

```bash
# Review a file
python main.py review path/to/file.py

# Review with a git diff
python main.py review path/to/file.py --diff "$(git diff HEAD~1 path/to/file.py)"
```

### 4. Run as an API server

```bash
python main.py serve
# POST http://localhost:8000/review
```

## 📄 License

MIT
