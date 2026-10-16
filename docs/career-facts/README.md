# Career Fact Library

**Status:** STRUCTURE ONLY — No career facts populated.
**Last reviewed:** 2026-10-16
**Reviewed by:** Lee Cuevas
**Access:** Read-only by career-hunter and career-strategist profiles.
**Authority:** Lee is the sole authority for approved facts. No agent may add, modify, or infer career facts without Lee's explicit review and approval.

## Structure

```
career-facts/
├── README.md              ← This file
├── verified/
│   ├── accomplishments.md  ← Lee's verified professional accomplishments
│   ├── certifications.md   ← Lee's verified certifications and licenses
│   ├── education.md        ← Lee's verified education
│   └── experience.md       ← Lee's verified work experience with dates
├── current/
│   ├── capabilities.md     ← Current technical projects and capabilities (verified)
│   └── projects.md         ← Current technical projects (with verification status)
├── targets/
│   ├── roles.md            ← Target roles and descriptions
│   ├── compensation.md     ← Compensation requirements and ranges
│   └── locations.md        ← Location and travel preferences
├── unverified/
│   └── pending.md          ← Claims pending Lee's review and approval
└── restricted/
    └── confidential.md     ← Confidential information (never shared)
```

## Rules

1. **All facts in `verified/` must be reviewed and approved by Lee.** No agent adds facts without Lee approval.
2. **All facts in `current/` must include a verification status** (verified/needs-review/date-last-verified).
3. **No agent may infer or fabricate facts.** Only explicitly approved facts are authoritative.
4. **`unverified/` and `restricted/` are for Lee's use only.** Agents may read but never write.
5. **Confidential facts in `restricted/` must never appear in agent output** unless Lee explicitly authorizes sharing specific items.
6. **When an agent references a fact**, it must cite the source file (e.g., "verified/accomplishments.md, line 12").

## How to Use

- **career-hunter** reads from `verified/` and `current/` to score job opportunities and prepare applications.
- **career-strategist** reads from `verified/` and `current/` to develop positioning and relationship strategies.
- **Jeeves** coordinates which facts are relevant for each task and surfaces them to workers.
- **Lee** reviews and approves facts, adding them to `verified/` from `unverified/`.
