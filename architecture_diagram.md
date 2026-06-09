# Architecture Diagram — Multi-Agent Code Review

```mermaid
flowchart TD
    subgraph Input
        SRC["Source File\n(.py / .js / .ts / …)"]
        DIFF["Git Diff\n(optional)"]
    end

    subgraph Interfaces["Access Interfaces"]
        CLI["CLI\npython main.py review"]
        API["FastAPI\nPOST /review"]
    end

    subgraph Cloud["Alibaba Cloud"]
        DS["DashScope API\ndashscope-intl.aliyuncs.com\n(Qwen model inference)"]
        FC["Function Compute v3\nHTTP Function host"]
    end

    subgraph Orchestration["Orchestrator (qwen-max)"]
        ORC["Orchestrator\npipeline/orchestrator.py"]
    end

    subgraph Specialists["Specialist Agents — parallel (qwen-plus × 5)"]
        SA["StaticAnalysisAgent\nlogic / complexity / leaks"]
        SEC["SecurityAgent\nOWASP / injection / secrets"]
        PERF["PerformanceAgent\nN+1 / memory / I/O"]
        DOC["DocumentationAgent\ndocstrings / coverage"]
        TC["TestCoverageAgent\nbranches / edge cases"]
    end

    subgraph DebateLayer["Debate & Consensus (protocol/)"]
        CD["ConflictDetector\nlocation + semantic overlap"]
        DE["DebateEngine\nup to 3 rounds"]
        MOD["ModeratorAgent (qwen-max)\narbitrates & synthesises"]
    end

    subgraph Output["Review Result"]
        CR["ConsensusResult\nper-finding verdict"]
        UC["Unresolved Conflicts\nescalated for human review"]
        MET["ReviewMetrics\nconflicts / rounds / confidence"]
    end

    GH["GitHub API\n(PR comment via\n.github/workflows/code-review.yml)"]

    %% Input → interfaces
    SRC --> CLI
    SRC --> API
    DIFF --> CLI
    DIFF --> API

    %% Interfaces → orchestrator (via FC on Alibaba Cloud)
    CLI --> FC
    API --> FC
    FC --> ORC

    %% Orchestrator fans out to specialists
    ORC -->|"asyncio.gather"| SA
    ORC -->|"asyncio.gather"| SEC
    ORC -->|"asyncio.gather"| PERF
    ORC -->|"asyncio.gather"| DOC
    ORC -->|"asyncio.gather"| TC

    %% All specialists call DashScope
    SA  -->|"OpenAI-compat\nAPI call"| DS
    SEC -->|"OpenAI-compat\nAPI call"| DS
    PERF-->|"OpenAI-compat\nAPI call"| DS
    DOC -->|"OpenAI-compat\nAPI call"| DS
    TC  -->|"OpenAI-compat\nAPI call"| DS

    %% Findings feed conflict detection
    SA  --> CD
    SEC --> CD
    PERF--> CD
    DOC --> CD
    TC  --> CD

    %% Conflict detection → debate
    CD -->|"Conflict list"| DE

    %% Debate engine calls agents back for responses
    DE -->|"respond_to_challenge()"| SA
    DE -->|"respond_to_challenge()"| SEC
    DE -->|"respond_to_challenge()"| PERF
    DE -->|"respond_to_challenge()"| DOC
    DE -->|"respond_to_challenge()"| TC

    %% Those challenge calls also hit DashScope
    DE -->|"agent LLM calls"| DS

    %% Debate transcripts → moderator
    DE -->|"Debate transcripts"| MOD
    MOD -->|"synthesize() LLM call"| DS

    %% Moderator produces output
    MOD --> CR
    MOD --> UC
    MOD --> MET

    %% Results surface via interfaces
    CR  --> CLI
    UC  --> CLI
    MET --> CLI
    CR  --> API
    UC  --> API
    MET --> API

    %% CI/CD posts to GitHub
    API --> GH

    %% Styling
    classDef cloud fill:#FF6A00,color:#fff,stroke:#c45000
    classDef agent fill:#6B46C1,color:#fff,stroke:#4c2f99
    classDef debate fill:#0070f3,color:#fff,stroke:#005bb5
    classDef io    fill:#1a1a2e,color:#eee,stroke:#444
    classDef iface fill:#009688,color:#fff,stroke:#00695c

    class DS,FC cloud
    class SA,SEC,PERF,DOC,TC,ORC agent
    class CD,DE,MOD debate
    class SRC,DIFF,CR,UC,MET,GH io
    class CLI,API iface
```

## Component Summary

| Component | File(s) | Model | Role |
|---|---|---|---|
| Orchestrator | `pipeline/orchestrator.py` | `qwen-max` | Fans out to specialists, coordinates phases |
| StaticAnalysisAgent | `agents/static_analysis.py` | `qwen-plus` | Logic errors, complexity, resource leaks |
| SecurityAgent | `agents/security.py` | `qwen-plus` | OWASP Top 10, injection, hardcoded secrets |
| PerformanceAgent | `agents/performance.py` | `qwen-plus` | N+1 queries, memory pressure, I/O blocking |
| DocumentationAgent | `agents/documentation.py` | `qwen-plus` | Docstring coverage, API contract clarity |
| TestCoverageAgent | `agents/test_coverage.py` | `qwen-plus` | Branch coverage gaps, missing edge cases |
| ConflictDetector | `protocol/consensus.py` | — | Location + semantic overlap detection |
| DebateEngine | `protocol/debate.py` | — | Runs up to 3 structured debate rounds |
| ModeratorAgent | `agents/moderator.py` | `qwen-max` | Arbitrates debate, builds ConsensusResult |
| FastAPI server | `api/main.py` | — | REST interface (`POST /review`, `GET /health`) |
| CLI | `main.py` | — | Terminal interface with Rich output |
| FC Deployment | `deploy/alibaba_cloud.py` | — | Alibaba Cloud Function Compute + ECS/VPC |

## Debate / Moderation Flow

```mermaid
sequenceDiagram
    participant ORC as Orchestrator
    participant CD as ConflictDetector
    participant DE as DebateEngine
    participant A1 as Agent A (e.g. Security)
    participant A2 as Agent B (e.g. Performance)
    participant MOD as ModeratorAgent
    participant DS as DashScope API

    ORC->>CD: all_findings (dict)
    CD-->>ORC: conflicts[]

    loop up to 3 debate rounds
        ORC->>DE: run(findings, conflicts, agents)
        DE->>A1: respond_to_challenge(finding_a, finding_b, round)
        A1->>DS: chat.completions (qwen-plus)
        DS-->>A1: {stance, reasoning, updated_confidence}
        DE->>A2: respond_to_challenge(finding_b, finding_a, round)
        A2->>DS: chat.completions (qwen-plus)
        DS-->>A2: {stance, reasoning, updated_confidence}
        DE-->>ORC: DebateMessage[] (transcripts)
        alt both agents agree
            DE-->>ORC: early exit
        end
    end

    ORC->>MOD: synthesize(findings, transcripts, unresolved)
    MOD->>DS: chat.completions (qwen-max) per finding
    DS-->>MOD: {consensus_reached, agreement_score, resolution}
    MOD-->>ORC: ReviewResult
```
