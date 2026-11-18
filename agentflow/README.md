# agentflow

A small, stdlib-only Python engine for running agent workflows as a DAG. It verifies
every task's output, retries only the tasks that fail, keeps state in SQLite so a run
can be resumed, and asks a human before running irreversible tasks.

```
python3 -m pytest -q tests      # engine tests
python3 examples/demo.py        # fail -> correct -> succeed -> approval, with event log
```

## Claude Code CLI

Run from this directory with an authenticated Claude Code CLI on PATH:

```sh
python3 -m agentflow run report --objective "Draft a design for a local CSV reporting tool"
python3 -m agentflow status report
python3 -m agentflow resume report
```

Use `run NAME --plan FILE` to supply the engine's JSON task plan. Use
`--constraints-from FILE` with an objective to pass a JSON array of approved
constraints to the planner. Global `--db`, `--jobs` and `--skills` flags go
before the command. The CLI stores text outputs and evidence in SQLite, invokes Claude
with built-in tools disabled, and denies approval-gated tasks. The Python API
supports project-specific workers and checks.

Every run prints `agentflow: N Claude calls, $X reported cost` to stderr. The
count includes calls that timed out; their cost is not reported by Claude, so
the dollar figure is a lower bound. Per-attempt usage is in the `events` table.
A task's `timeout` (seconds) overrides the default 180 s Claude call limit.

### CLI checks

| Check | Spec fields | Passes when |
|---|---|---|
| `contains` | `contains: [str, ...]` | every string appears in the output |
| `command` | `output_file`, `command: [argv]`, optional `fixtures` (dir, relative to the plan file), `command_timeout` | the output, written to `output_file` in a fresh temp dir beside a copy of `fixtures`, makes `command` exit 0. `{python}` in `command` becomes the running interpreter. A single surrounding Markdown code fence is stripped first. |

Only hand-written `--plan` files can use `command`; planner-generated tasks get
`contains` only, so a model never chooses what gets executed. The command runs
model-written code in a temp dir **without a sandbox**. Use a container for
untrusted plans.

### Example: code that must pass hidden tests

```sh
python3 -m agentflow run slugify-demo --plan examples/slugify/plan.json
```

`examples/slugify/fixtures/test_slugify.py` enforces a 50-character rule that
the brief omits, so the first attempt fails and pytest's output is fed back as
the correction. Recorded run (Nov 2026): attempt 1 failed the length test, attempt
2 timed out at 180 s, attempt 3 passed all six tests, and the dependent
`usage-note` task passed first time: 4 calls, $0.12 reported.

### Learned constraints (lessons → Skills)

When a task fails a check and then passes, the first line of each failed check
message is saved as a lesson for that worker type. Checks put a one-line
summary first, e.g. `command: exited 1: FAILED test_slugify.py::test_max_50_chars...`.
Raw lessons are **never sent to Claude**. They reach prompts only after a human
turns them into rules:

```sh
python3 -m agentflow lessons                       # unreviewed lessons, with how many tasks hit each
python3 -m agentflow lessons --propose             # drafts .workflow/proposals/<worker>-constraints/SKILL.md
                                                   #   for lessons seen in >= --min-count (2) tasks
# edit the draft: rewrite each line as a general rule, delete task-specific ones
python3 -m agentflow lessons --approve implementer # installs .claude/skills/implementer-constraints/SKILL.md
python3 -m agentflow lessons --reject implementer  # or discard the draft
```

Approving or rejecting marks those lessons as reviewed, so they are not proposed
again. An approved skill's body (without frontmatter or HTML comments) is sent
as `constraints` in every prompt for that worker type. It is also a normal
Claude Code Skill for interactive sessions in this project. A new proposal for a
worker that already has a skill starts from the current skill, so approving it
replaces the file with the reviewed union.

## Architecture

```
plan (JSON / list[Task]) ──validate──▶ Orchestrator ──▶ Worker(ctx) ──▶ checks(task, out)
                                          │   ▲                              │
                                          │   └──── feedback (≤3 retries) ◀──┘ fail
                                          ▼
                                SQLite: tasks (current state) + events (append-only log)
```

| Component | MVP form | Notes |
|---|---|---|
| Planner | **A plan is data** (`list[Task]` / JSON). | An LLM planner is just one way to produce this data, and its output goes through the same `validate()`. Reusable plans need no LLM call at all. |
| Worker | `Callable[[Context], Any]`, sync or async | Sync workers run in a thread, so subprocess and HTTP workers (e.g. `claude -p`) don't block other tasks. |
| Tools | Plain Python that a worker calls | The engine doesn't need its own tool abstraction. |
| Verification | `Callable[[Task, Any], str \| None]` | Deterministic checks. `None` means pass; a string is the error message fed back to the worker. |
| Orchestrator | `Orchestrator.run(run_id, tasks=None)` | Runs tasks in DAG order with concurrency, retries, skip propagation, approval and resume. |
| State | `Store` (SQLite) | Every state change is committed as it happens. |

### Schemas

```python
Task(id, worker, spec={}, deps=[], checks=[], requires_approval=False, timeout=None)
Context(task, inputs={dep_id: output}, feedback=[str], lessons=[str], attempt=int)
```
Plan JSON: `{"tasks": [{"id": "...", "worker": "...", "deps": [...], "checks": [...], ...}]}` → `load_plan(path)`.

Task statuses: `pending → running → done | failed | rejected`; `skipped` when a dependency is failed, skipped or rejected.

### Engine guarantees (each one is covered by a test)
- A plan with duplicate ids, unknown workers/checks/deps, or a cycle is rejected before anything runs.
- Independent tasks run concurrently, up to `concurrency`.
- A failed task is retried with the verifier's messages as `ctx.feedback`. It gets at most 1 + `max_corrections` (3) attempts.
- A worker exception, a timeout, a check that raises, or output that isn't JSON-serializable all count as a failed attempt. None of them crash the run.
- Only the failed task is retried. Its dependents are skipped transitively, and independent branches still finish.
- `requires_approval` tasks call the approver before the worker runs. The default approver **denies**, so an unattended run never takes an irreversible action.
- Resume: `run(run_id)` with no tasks continues from the database. Finished outputs are kept and interrupted ordinary tasks can retry within their remaining budget. Interrupted approval-gated tasks require manual reconciliation and are marked failed.
- Lessons: when a task passes after failing, its failed-check messages (not crashes, timeouts or interruptions) are saved under that worker's name. `Store.lesson_counts()` groups their first lines by worker and counts the tasks that hit each. Python API workers can read recent ones from `ctx.lessons`; the CLI sends only human-approved constraints.

## Reusing it in a project

```python
from agentflow import Orchestrator, Store, Task, cli_approver
import asyncio

orch = Orchestrator(
    workers={"coder": my_coder, "writer": my_writer},
    checks={"tests_pass": run_pytest, "has_keys": has_keys},
    store=Store("runs.db"), approver=cli_approver)
state = asyncio.run(orch.run("release-42", tasks))   # later: asyncio.run(orch.run("release-42")) to resume
```

1. Write workers. Use LLM workers only where judgment is needed; anything that can be plain code should be plain code.
2. Write checks as cheap, deterministic functions such as schema checks, `pytest` exit codes, linters or diffs. Make the error messages specific, because the worker uses them to fix its output.
3. Mark side-effecting tasks `requires_approval=True`.
4. Build the plan by hand, from JSON, or with an LLM planner, then run it.

## Design review (decisions vs. the original proposal)

- **The planner is optional, not a core component.** Calling an LLM to plan every run is the largest avoidable LLM cost. Here a plan is validated data.
- **No LangGraph for now.** The whole engine, including storage, is about 230 lines of asyncio. LangGraph would duplicate the scheduling and checkpointing and add a heavy dependency. Reconsider it if you need streaming UIs, interrupt/resume across services, or its tooling.
- **Hooks don't enforce runtime safety.** Claude Code hooks protect development sessions. Runtime approval is enforced by the engine itself, so it applies to every kind of worker, whether that's Python code, an HTTP call or `claude -p`, and doesn't depend on hook configuration.
- **Approval is requested for each attempt.** An interrupted approval-gated task is marked failed on resume so the operator can reconcile its effects.
- **Synchronous deadlines cannot kill Python threads.** A timed-out worker retains its slot and run lock until it exits. Configure I/O deadlines inside blocking workers.
- **One runner per database and run ID.** Runs use an advisory file lock on macOS and Linux. Keep lock files beside the database.
- **"Return to the original worker" means a fresh call with feedback, not the same session.** That makes retries stateless and resumable. If a long context is needed, put it in `spec`.
- **Constraint extraction uses the verifier's messages directly, not an LLM summary.** That's deterministic and free. A human rewrites recurring ones into general rules before any prompt sees them, because raw check output is task-specific and misleads unrelated tasks.
- **Retried side effects must be idempotent.** The engine retries whole tasks, so a worker that writes externally should be idempotent even when gated by approval.

## Current scope

The Python engine, the Claude-backed CLI, the `contains` and `command` checks,
usage accounting, and reviewed lessons → Skills are implemented. Tests exercise the Claude protocol with a
local stub; `examples/slugify` runs against real Claude.

## Next milestones
1. **Approval hook**: a project hook that blocks commands with known
   irreversible effects during interactive Claude Code sessions.
