# Execution guard: live foreground acceptance passed; human review pending

PR: https://github.com/nvrenuf/landmarksignal-operations/pull/20

## Current evidence — October 7, 2026

Lee's native Windows run at executable commit `4ba547506b29d0b64720a6825b855965a4745675` returned acceptance exit 0 at 13:53 MDT. Four recovery tests passed. The installed native policy recognized manual holds; actual Jeeves local-model parent and separately approved child calls passed; unapproved and wrong-issue children were denied before callbacks; a real contender was blocked throughout the owned scope checks; original cards were preserved and card `t_a43efea7` reached native review.

Evidence remains on Lee's laptop:
`C:\Users\lee\AppData\Local\hermes\landmarksignal-v1\acceptance\fcb34647cb854abb9ca7726c88122455\evidence.json`.

The console result is recorded in GitHub issues #19 and #22. The saved JSON has not yet been independently inspected or published. Issue #19 remains open; PR #20 remains unmerged. No Project authorization, Priority, Execution Order or Sprint fields were changed by the acceptance.

The scoped source review found no merge-blocking defect in the tested foreground guard/acceptance route. Review-workspace regression checks: 20 tests run, 18 passed, two native Windows ownership tests skipped on Linux. Those two checks previously passed in Lee's 13-test native policy/configuration run. Native library evidence remains 13 passed and one unsupported-platform skip; the canonical guard is unchanged since that native library run. There are no GitHub CI check runs or status contexts on the reviewed executable head.

This is synchronous foreground acceptance, not approval for ordinary product execution. Detached worker supervision, a full GitHub-to-worker handoff, old-session policy activation, and normal startup/idle recovery remain unverified. Same-user tamper resistance and cross-session host enforcement are not established. The caller behind the earlier background decomposition/promotion remains unidentified; native manual block events now prevent routine auto-promotion of parked acceptance cards.

## Historical checkpoints

The following sections record earlier findings and pending states. The current evidence above supersedes their pre-acceptance status claims; they remain for traceability.

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

On October 2, 2026, Lee ran the suite in an isolated detached Windows worktree
of commit `2bbcb0755ea5bbe10093a9e148250e9d7f3c1202`, using native Windows
Python with pywin32 from the installed Hermes virtual environment. The result
below was supplied by Lee; this review workspace did not execute Windows tests.

```
Ran 14 tests in 1.755s
OK (skipped=1)
Library tests complete. Hermes integration has NOT been validated by this suite.
Acceptance exit code: 0
```

Thirteen tests passed: six approval tests and seven native Windows mutex tests.
Only the unsupported-platform test was skipped because native mutex support was
available. Real two-process contention, actual mutex abandonment, live-owner
protection, recursive/wrong-thread release, callback/setup error cleanup, and
the synchronous child execution boundary all passed. This establishes library
acceptance for the tested commit; it does not establish installed enforcement.

## Required before operational acceptance

1. Native Windows library acceptance is complete for commit `2bbcb07`, as
   recorded above. Revalidate executable code if it changes.
2. Identify Jeeves's real claim/dispatch/child-creation entry path and integrate
   the authoritative guard there; prove negative checks at that boundary with
   a harmless explicitly authorized workload.
3. Confirm approval is provided by Lee through a controlled path. `approve()`
   stores a record; it does not authenticate a human. An agent sharing file
   write permissions can forge approval. File records alone are not a security
   boundary.
4. Hold ownership for the entire actual work lifetime. Returning a callback that
   launches a detached process/worker does not establish that guarantee.
5. Recheck PR mergeability after integration changes, then obtain Lee's merge
   decision. GitHub currently reports this PR mergeable.

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

## Installed Jeeves inspection and configuration preparation

Lee's read-only inspection identified Hermes revision
`b1968795b2569d2f7a2fc541328399c952679c25` and profile
`%LOCALAPPDATA%\hermes\profiles\jeeves\config.yaml`. The initial raw profile had no
explicit Kanban concurrency/dispatch, delegation, agent-turn or approvals
sections. Lee has now applied the reviewed limits and verified their effective
values through the installed Hermes loader.

The local untracked `kanban-control.py` and `kanban-guard.bat` do not invoke the
authoritative guard. Their origin check is a placeholder; task counting can
fail open; the controller omits the exact task ID required by this Hermes
revision; the batch script accepts any nonempty token and can return success
after command failure. A dispatch-only mutex wrapper would also be insufficient:
Hermes dispatch starts detached workers whose lifetime exceeds the command.

The named LandmarkSignal board contains one ready card:
`t_b4bb78ed`, titled Issue #1, unassigned and without a full GitHub issue URL.
GitHub Issue #1 is closed. Preserve the record and do not dispatch this stale
card. The other inspected card is an archived test child. No correctly bound
Issue #19 card was found. GitHub Issue #19 is open and explicitly permits only
harmless safety testing, including no Spark access or deployment.

`configure_jeeves_v1.py` prepares a reversible profile update for this installed
Hermes revision. It appends explicit dispatch-off and concurrency-one settings,
one child at most with spawn depth one and a 300-second child limit, 20 agent
turns, manual approval mode and denial of unattended/cron approval. Existing
config bytes remain intact; conflicts stop the update; the original is backed
up. Applying also checks the installed Hermes config loader's effective values.

Five configuration preservation/failure tests passed in the review workspace.
On October 2, Lee applied the helper successfully on Windows. The exact original
SHA256 was `f0d6f636a970ac5437a0114c6cbdb7bcf12c78c0bbab93075b9972e58a8183da`;
backup: `config.pre-v1-20261002T225452Z-1bb9f0cc.yaml` in the Jeeves profile.
The installed loader confirmed every configured limit and preservation of the
model/session/terminal/memory settings. Loading the new file does not demonstrate
that an already-running gateway has reloaded it.

These limits do not authenticate child approval or integrate the mutex into
live Hermes. Operational acceptance still requires the guarded entry path,
exact issue/card binding, a controlled child-approval boundary and the harmless
live test. No issue/card, authorization, model, infrastructure or dispatcher has
been modified or launched during this preparation.

## Prepared foreground integration; not yet accepted on Windows

`install_jeeves_policy.py` installs the reviewed native pre-tool hook only in
the existing Jeeves profile, preserving other plugin files and backing up the
config. It also explicitly sets `kanban.review_dispatch: false`; this Hermes
revision otherwise defaults to automatic review dispatch. The hook blocks
unowned execution, shell, task mutation and delegation. Planning reads remain
available. Existing Hermes sessions require a runtime restart to load it.

`guarded_jeeves_acceptance.py` is a manual foreground entry for open Issue #19.
It starts a fresh native Jeeves agent, uses the existing laptop model at
loopback port 18434, exposes no tools, and holds the authoritative Windows mutex
through the actual parent and child agent lifetimes and cleanup. The console
requires separate exact human approval phrases before parent work and before
child execution. Unapproved and wrong-issue child callbacks must be denied.
Real competing processes must fail to acquire ownership before and after the
actual model calls. The existing library suite separately established contention
during a held callback.

The entry binds a new named-board test card to the complete reviewed Issue #19
URL and claims that exact card. Existing cards are compared field-for-field;
the stale Issue #1 card is preserved. Successful work produces evidence and
uses the native review handoff, never completion. Failure stops, preserves
diagnostics and blocks its own card when ownership is established. Only an
explicit human retry can resume this runner's exact blocked acceptance card.

The reviewed `kanban-control.py` and `kanban-guard.bat` accept only this manual
acceptance route and return failure for legacy claim/dispatch/token routes.
Lee's dirty original checkout and its untracked old launchers remain untouched.

Compilation and six portable policy tests passed in the review workspace;
two additional native ownership tests were skipped on Linux and must run on
Windows. Neither installation nor live model acceptance has yet been verified
on Lee's Windows laptop. The new hook denies ordinary product execution until
a separately reviewed guarded work route exists. This foreground trial does
not establish native detached dispatcher/delegate-tool supervision, Spark
workers, cross-session enforcement or resistance to another program running
as the same Windows user. The child here is a real second synchronous native
Jeeves agent, not a deployed worker bot.

After the live Windows run, return the evidence to this PR for human review.
Do not claim Issue #19's GitHub-evidence criterion until that evidence is
actually published. No merge, branch deletion or auto-completion is authorized.

