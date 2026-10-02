# Execution guard correction: Windows validation pending

PR: https://github.com/nvrenuf/landmarksignal-operations/pull/20

## Current status

The library and acceptance suite have been corrected after reviewing b6cad0d.
The previous 5/5, 8/8 and 10/10 readiness claims are superseded. Do not merge or
authorize unattended work on the basis of those reports.

The previous suite imported an uncommitted underscore-named module. Its
concurrency workers ran sequentially without acquiring a mutex, and its crash
test fabricated a stale file instead of killing a mutex owner.

## Authoritative files

- `execution_guard_v1_final.py`: the only guard implementation.
- `test_acceptance_corrected.py`: isolated library acceptance tests.
- `execution-guard-v1-final.py`: compatibility import/test wrapper only.

Earlier execution launchers fail closed rather than run obsolete guards.
Earlier guard-test entry points delegate to the corrected suite. The old
handoff-test entry point reports that live integration is unverified.

## What changed

- Create/open a mutex with waiting rights; no file-lock fallback.
- Accept WAIT_ABANDONED as transferred ownership and rebuild diagnostic state.
- Reject recursive ownership across guard objects on the same thread.
- Preserve native ownership and metadata against a non-owner release.
- Release ownership after metadata setup errors and callback exceptions.
- Remove diagnostic metadata before releasing the mutex, close native handles,
  and surface cleanup failures.
- Never use a timestamp to displace a live mutex owner.
- Validate child identity, exact issue binding, record structure and boolean
  approval. Deny missing, malformed or unapproved records.
- Check approval inside the synchronous child callback boundary under the
  parent's owned issue scope. A verify-only test is not an execution test.

Tests use temporary directories and unique mutex names, never live Kanban data.
Owner/contender processes synchronize with bounded pipes, check exit codes and
test genuine abandonment while retaining a kernel handle across owner death.

## Validation actually performed

In the Linux review workspace:

```
python -m py_compile execution_guard_v1_final.py test_acceptance_corrected.py
python test_acceptance_corrected.py --portable
```

Compilation succeeded. Seven portable tests passed, including fail-closed
behavior when native Windows mutex support is unavailable.

```
python test_acceptance_corrected.py
```

This command correctly returned exit 2: Windows acceptance was blocked on Linux.
Skipped Windows tests are not counted as acceptance passes.

Run that same command with native Windows Python and pywin32 from the exact
pushed commit. Exit 0 is required. Do not run it through WSL Python.

## Required before operational acceptance

1. Attach native Windows test output and exit code for the reviewed commit.
2. Identify Jeeves's real claim/dispatch/child-creation entry path and integrate
   the authoritative guard there; prove negative checks at that boundary with
   a harmless explicitly authorized workload.
3. Confirm approval is provided by Lee through a controlled path. `approve()`
   stores a record; it does not authenticate a human. An agent sharing file
   write permissions can forge approval. File records alone are not a security
   boundary.
4. Hold ownership for the entire actual work lifetime. Returning a callback that
   launches a detached process/worker does not establish that guarantee.
5. Resolve any PR conflicts against main, then obtain Lee's merge decision.

No installed Hermes hook has been changed by this repository correction.
The existing mutex name serializes participating callers in the same Windows
session. Cross-session/global-host enforcement has not been established.
Recovery repairs diagnostic metadata only; it does not automatically replay
interrupted work or recover detached child processes.

## Project status

Project #3's existing Status field was already configured and verified:
Idea, Defined, Sprint Ready, Queued for Jeeves, In Progress, Validation,
Human Review, Blocked, Done.

There is no remaining manual Status-field action. This correction does not
change project issues, authorization, priority, order or sprint assignments.

No model changes, Spark changes, bot deployment, merge or branch deletion are
part of this correction.
