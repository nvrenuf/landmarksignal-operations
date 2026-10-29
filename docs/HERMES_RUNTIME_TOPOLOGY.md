# Hermes / Jeeves Runtime Topology — Canonical Operations Reference

## Purpose

This document is the canonical starting point for understanding the Hermes/Jeeves runtime topology on Lee's Windows laptop.

Use it to avoid re-deriving basic infrastructure relationships in every new Jeeves session.

This document intentionally separates:

- **durable topology** — paths, ownership boundaries, and architectural relationships that should remain stable;
- **live state** — PIDs, active processes, current model routes, gateway health, and other facts that can change and must be verified when they matter.

If a dated report conflicts with this document on durable topology, stop and reconcile the conflict before changing the runtime.

## Authority and scope

This repository owns the maintained LandmarkSignal integration and operational documentation for Hermes/Jeeves.

It does **not** contain:

- the full installed Hermes runtime;
- private live configuration;
- credentials;
- the live Kanban database;
- model weights;
- complete machine backups.

Relevant existing documents:

- `docs/HERMES_FOLDER_MAP.md` — detailed installed path map.
- `docs/GITHUB_HERMES_WORKFLOW.md` — GitHub-to-Hermes workflow.
- `docs/KANBAN_EXECUTION_POLICY.md` — execution controls and limits.
- `docs/JEEVES_EXECUTION_CONTRACT.md` — authority and worker behavior.
- `docs/JEEVES_KNOWN_GOOD_2026-10-15.md` — dated recovery checkpoint.
- `docs/HERMES_SPARK_CONNECTIVITY_RUNBOOK.md` — Spark connectivity and recovery.

This file is the first document to read when the question is:

> "How do the root Hermes home, Jeeves profile, gateway, skills, Hindsight, and Kanban relate to each other?"

## Durable directory topology

Root Hermes home:

```text
C:\Users\lee\AppData\Local\hermes
```

Jeeves profile home:

```text
C:\Users\lee\AppData\Local\hermes\profiles\jeeves
```

Installed upstream Hermes runtime/source:

```text
C:\Users\lee\AppData\Local\hermes\hermes-agent
```

LandmarkSignal execution board:

```text
C:\Users\lee\AppData\Local\hermes\kanban\boards\landmarksignal\kanban.db
```

LandmarkSignal launch/dashboard plugin:

```text
C:\Users\lee\AppData\Local\hermes\plugins\landmarksignal-launch\dashboard
```

Root/default execution-policy plugin:

```text
C:\Users\lee\AppData\Local\hermes\plugins\landmarksignal-execution
```

Jeeves execution-policy plugin:

```text
C:\Users\lee\AppData\Local\hermes\profiles\jeeves\plugins\landmarksignal-execution
```

Jeeves profile configuration:

```text
C:\Users\lee\AppData\Local\hermes\profiles\jeeves\config.yaml
```

Root/default configuration:

```text
C:\Users\lee\AppData\Local\hermes\config.yaml
```

Local LandmarkSignal workspaces and workflow artifacts are stored under the root Hermes home, including `landmarksignal-v1\work`, intake, returns, recovery, and acceptance directories. Read the card's stored workspace path instead of guessing a workspace location.

## Root home versus profile home

Hermes has a root installation/home and may also use profile-specific homes.

The Jeeves profile is **not** a second complete Hermes installation. It is a profile overlay containing profile-specific configuration, skills/plugins, memory/provider settings, and other profile state.

Do not assume that every process launched while the Jeeves profile is selected must have:

```text
HERMES_HOME=C:\Users\lee\AppData\Local\hermes\profiles\jeeves
```

The LandmarkSignal integration deliberately pins some shared resources, including the canonical LandmarkSignal Kanban board, under the root Hermes home.

A process's root/profile relationship must be determined from the actual Hermes launcher/profile behavior, not inferred only from its current working directory.

## Active profile

The selected or sticky active profile is operational state and may change.

Before a profile-sensitive change, verify the active profile using the supported Hermes profile/config commands.

Do not treat an old chat statement, Hindsight memory, or dated report as proof of the current active profile.

For normal Jeeves work, the expected profile is:

```text
jeeves
```

The authoritative Jeeves profile configuration is:

```text
%LOCALAPPDATA%\hermes\profiles\jeeves\config.yaml
```

## Gateway model

The Hermes gateway is a shared runtime service and has historically operated as a **default-profile multiplexer** while browser/dashboard sessions select a profile.

Important operational consequence:

> A running gateway process whose command line does not visibly contain `-p jeeves` is not, by itself, proof that the Jeeves profile is not being served correctly.

The existing operations evidence records a running root/default gateway alongside Jeeves-profile browser use.

Do not replace, kill, or start a second gateway merely because a profile-specific gateway status reports failure or because the running gateway command line does not include a profile flag.

### Gateway ownership rule

Before restarting or replacing a gateway:

1. Verify the currently listening process and port.
2. Verify ownership using the supported Hermes runtime/status tooling.
3. Verify whether the existing gateway is the shared/default multiplexer.
4. Check for active Kanban work and active sessions.
5. Require explicit operator approval before replacing a healthy shared gateway.

A status such as:

```text
gateway_replace_ownership_unproven
```

is a safety stop. It means ownership has not been proven strongly enough to replace the process. It is **not** evidence that a second gateway should be started.

## Kanban ownership

The canonical existing LandmarkSignal execution board is shared under the root Hermes home:

```text
%LOCALAPPDATA%\hermes\kanban\boards\landmarksignal\kanban.db
```

It is separate from any root/default generic `kanban.db`.

Do not derive the board path from:

- the current chat directory;
- the selected profile directory;
- a worker's workspace;
- Hindsight memory.

Read the configured board or the durable operations documentation.

The current LandmarkSignal operating model keeps GitHub Project state as the planning/authorization record and Hermes Kanban as the local execution lifecycle.

## Skills

Skills may exist at root level and/or within a profile.

Profile-specific Jeeves skills live under the Jeeves profile tree.

Repository skill changes do not automatically update installed skill copies.

When a skill was installed from `nvrenuf/forge-skills`, treat that repository as the source for the skill definition and explicitly refresh the installed copy when required.

Do not assume a merged Forge Skills PR is already present in the Jeeves profile.

## Hindsight

Hindsight is operational memory, not authoritative project or runtime state.

Use Hindsight for:

- prior decisions;
- known quirks;
- commands that worked;
- previous failures and repairs;
- operational context.

Do not use Hindsight as sole authority for:

- current gateway PID or ownership;
- current active profile;
- current model endpoint;
- current GitHub status;
- current Kanban task state;
- current repository contents;
- whether a PR has merged;
- whether a service is currently healthy.

When Hindsight and durable repository documentation disagree, repository documentation wins for the documented architecture. When either conflicts with live runtime inspection, stop and determine whether the durable document is stale before changing the system.

## Hindsight and new-session resume

A new Jeeves session should **not** rediscover the complete Hermes architecture unless a health check shows a real inconsistency.

Normal startup should be:

1. Load available Hindsight context.
2. Read this runtime-topology document when infrastructure context is needed.
3. Read the target project's authoritative files.
4. Read live GitHub/Kanban state relevant to the current task.
5. Verify only the live runtime facts that could materially affect the requested operation.
6. Continue the task.

Do not re-investigate root-versus-profile gateway architecture merely because a new chat session started.

## Model/provider configuration

Jeeves model/provider settings are profile-specific and have changed over time.

A known-good October 15 checkpoint recorded a local route in the Jeeves profile, but model routes are live operational state and must not be copied blindly from a dated document.

Before model/provider changes:

- read the current Jeeves profile configuration;
- verify the actual endpoint;
- verify exact model identity;
- preserve authentication;
- avoid restarting shared CCT/DGX services;
- create a targeted backup before a change.

Do not restore an entire old profile merely to repair one model field.

## Browser dashboard and desktop app

The browser dashboard is a local interface to the existing Hermes services.

Browser reloads and desktop application restarts are separate from the underlying runtime.

Closing or crashing the desktop app does not, by itself, prove that:

- the gateway stopped;
- the Kanban stopped;
- the model server stopped;
- Hindsight stopped;
- the browser dashboard is invalid.

Verify service health independently before restarting infrastructure.

Known local browser entry points have included:

```text
http://127.0.0.1:9119/kanban?profile=jeeves
http://127.0.0.1:9119/jeeves-launch?profile=jeeves
```

Treat ports and availability as live state.

## Startup / recovery decision tree

### If Jeeves is responding normally

Do not inspect or restart the gateway merely because a new session was opened.

Read project state and continue.

### If the browser dashboard is available but the desktop app crashed

Use the browser dashboard.

Do not restart shared services unless an actual service health check fails.

### If a profile-specific gateway reports startup failure but a shared gateway is running

Do not start another gateway automatically.

Verify whether the shared/default gateway is expected to serve the selected profile.

### If the gateway is unhealthy or absent

Use the supported Hermes status/runtime tooling to establish:

- expected owner;
- expected port;
- active profile;
- active Kanban work;
- active model route.

Then follow the relevant recovery runbook. Do not improvise process replacement.

### If model inference fails

Verify the model endpoint independently of gateway state.

Gateway health and model-server health are separate questions.

## Facts that are intentionally NOT pinned here

Do not store the following as permanent topology facts:

- PIDs;
- current task counts;
- exact process counts;
- temporary ports unless they are part of a reviewed stable configuration;
- current model ID unless explicitly designated as the active baseline;
- current GitHub issue state;
- current Kanban card state;
- temporary tunnels;
- ephemeral error messages.

Those belong in dated evidence or live inspection.

## Known current ambiguity to resolve once, not every session

Historical documentation proves that a root/default gateway can coexist with Jeeves-profile browser use and that the LandmarkSignal board is root-pinned.

However, the exact current Hermes implementation path that resolves the sticky/default profile into a root-launched gateway should be documented from code/runtime evidence if it has not already been proven.

Until that proof is captured:

- do not treat a root-launched gateway as suspicious by itself;
- do not treat a profile-specific `startup_failed` state as permission to replace it;
- do not create a parallel gateway merely to make the status display look cleaner.

Once proven, update this section and the relevant runtime check so future sessions do not revisit the question.

## Source-of-truth hierarchy

For Hermes/Jeeves operations:

```text
Current live inspection
  + canonical operations documentation
  + current configuration
  > Hindsight memory
  > chat history
```

For a product/project such as Model Factory:

```text
Project repository + GitHub Project state
  > Hindsight memory
  > chat history
```

Hindsight should accelerate resume, not replace verification of live state.

## Change discipline

Before changing root/profile/gateway topology:

- identify the exact owning configuration or process;
- make a targeted backup;
- check active work;
- avoid broad restores;
- do not print credentials;
- do not change shared CCT/DGX services without explicit approval;
- update this document when the durable topology changes.

If only a live-state fact changed, update dated evidence instead of rewriting the durable topology.
