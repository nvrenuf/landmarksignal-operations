# Operating Model

## Control Hierarchy

```
Lee + ChatGPT
├── strategy
├── priorities
├── sprint selection
├── architecture decisions
└── acceptance criteria

GitHub
├── authoritative execution record
├── issues
├── dependencies
├── sprint assignments
├── PRs
├── decisions
└── evidence

Jeeves
├── executive orchestrator
├── maintains execution state
├── coordinates Hermes workers
├── may decompose approved work
└── may NOT change LandmarkSignal strategic priority or scope without escalation

Argus
└── LandmarkSignal domain lead within Hermes

Hermes workers
└── execute approved work
```

## Execution Flow

1. **Strategy & Priorities** — Set by Lee + ChatGPT
2. **Issue Creation** — Jeeves creates implementation issues
3. **Approval** — Lee approves sprint work
4. **Execution** — Jeeves coordinates Hermes workers
5. **Validation** — Evidence attached to issues/PRs
6. **Human Review** — Lee reviews and merges production changes

## Key Rules

> **Jeeves may optimize execution of approved work. Jeeves may not optimize LandmarkSignal strategy.**

> **All production changes require human review and approval.**

> **Existing Community Capital DGX services are production dependencies. LandmarkSignal infrastructure work must be additive.**

---

*Detailed content will be populated during Lee + ChatGPT planning.*
