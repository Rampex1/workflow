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

Every run prints `agentflow: N Claude calls, $X reported cost` to stderr, and
`(K timed out, cost unknown)` when a call was killed: Claude reports no cost for
a killed call, so the dollar figure is then a lower bound. Per-attempt usage is
in the `events` table. A task's `timeout` (seconds) overrides the default 180 s
Claude call limit. When `claude` exits non-zero, its stderr becomes the attempt's
feedback, and any cost it reported is still recorded.

**Bounding each call.** Calls run with `--effort medium` (global `--effort`, or
a task's `spec.effort`) and an output cap of 8000 tokens (`--max-output-tokens`,
passed as `CLAUDE_CODE_MAX_OUTPUT_TOKENS`). Measured on the slugify task at the
default effort, 1 in 3 calls ran away: 76,897 output tokens, 484 s and $1.56
for a 1.4 KB answer, against about 6 s and $0.03 normally. Earlier runs lost 5
of 9 calls to the 180 s timeout this way. At `medium`, 6 of 6 calls took
4–9 s. A call that hits the cap ends with an error, which counts as a failed
attempt, and its cost is reported. Claude Code retries internally up to about
4× the cap first, so the worst case per call is about 32k tokens.

### CLI checks

| Check | Spec fields | Passes when |
|---|---|---|
| `contains` | `contains: [str, ...]` | every string appears in the output |
| `command` | `output_file`, `command: [argv]`, optional `fixtures` (dir, relative to the plan file), `command_timeout` | the output, written to `output_file` in a fresh temp dir beside a copy of `fixtures`, makes `command` exit 0. `{python}` in `command` becomes the running interpreter. A single surrounding Markdown code fence is stripped first. |

Only hand-written `--plan` files can use `command`; planner-generated tasks get
`contains` only, so a model never chooses what gets executed. The command runs
model-written code in a temp dir **without a sandbox**. Use a container for
untrusted plans.

### Fixing an issue in a codebase (`fix`)

```sh
python3 -m agentflow fix bug-123 --repo ~/work/app \
  --issue "average() adds 1 to the result" \
  --check "python -m pytest -q tests/test_stats.py" --readonly tests/
```

The result is a patch, `.workflow/bug-123-fix.patch`, which you review and
apply with `git apply`. Your checkout is never modified.

- **Gate first.** `--check` runs once on the current commit before any Claude
  call. If it already passes, the run is refused, because it can't detect the issue. If it
  fails, the first line is printed (stop there if it's a setup problem, e.g.
  a missing module), and the output is sent to Claude as starting evidence.
- **Each attempt runs in a fresh `git worktree`** of the pinned commit. Claude
  gets Read/Edit/Write/Glob/Grep, plus Bash for exactly the `--check` command, in
  `--restricted --permission-mode dontAsk` mode, which ignores the target
  repo's settings and hooks. The output is the staged diff, with clutter like
  `__pycache__/` and `node_modules/` excluded.
- **The `diff_command` check** applies that diff to another fresh worktree,
  fails if it touches a `--readonly` path (so "fixing" by editing the tests
  is caught), and runs `--check`. A failure is fed back, up to 4 attempts.
- Uncommitted changes in `--repo` are not included; the fix starts from `HEAD`.
- Hand-written plans can use the same worker: `"worker": "coder"` with
  `spec.repo` (relative to the plan file), `spec.check`, optional
  `spec.readonly`, and `"checks": ["diff_command"]`. The planner can't assign
  `coder` tasks. Each coder task starts from the base commit; a dependency's
  diff reaches it as text, not as applied changes.

Recorded run (Nov 2026): a one-line bug in a toy repo was fixed in 1 call,
10 s, $0.04.

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

Recorded loop (Nov 2026, slugify): the length lesson recurred in 2 runs, was
proposed, rewritten by the reviewer as "URL slugs are at most 50 characters.
Truncate at a word boundary…", and approved. The next 2 runs passed on the first
attempt with 2 calls each (about $0.06), against 3–5 calls per run before.

Lessons are grouped by worker type, so an approved constraint reaches every
task of that type. Keep rules general, or scope them in the text ("URL slugs
are…").

Approving or rejecting marks those lessons as reviewed, so they are not proposed
again. An approved skill's body (without frontmatter or HTML comments) is sent
as `constraints` in every prompt for that worker type. With `--objective`, every
approved skill also goes to the planner (after any `--constraints-from` items), so
the rules shape how the work is split and checked. It is also a normal
Claude Code Skill for interactive sessions in this project. A new proposal for a
worker that already has a skill starts from the current skill, so approving it
replaces the file with the reviewed union.

### Irreversible-command guard (Claude Code hook)

`.claude/settings.json` registers a `PreToolUse` hook on Bash
(`.claude/hooks/guard.py`) for interactive Claude Code sessions in this project.
It checks each command against the rules in `.claude/irreversible.json` (regex,
reason, and `ask` or `deny`; the first match wins). Default rules:

| Decision | Matches |
|---|---|
| `deny` | recursive `rm` of `/`, `~` or `$HOME` |
| `ask` | recursive `rm`, `git push`, `git reset --hard` / `clean -f` / `restore`, deleting branches or rewriting history, `npm`/`pnpm`/`yarn publish`, `twine upload`, `gh release create`, `terraform apply`/`destroy`, `kubectl apply`/`delete`, `helm install`/`upgrade`, deploy scripts at command position, `make deploy`, `DROP TABLE`/`TRUNCATE TABLE` |

`ask` shows Claude Code's approval prompt, so a human decides. In headless
`claude -p` nobody can answer, so `ask` acts as a denial. If the rules file can't
be read or parsed, the guard asks before every Bash command instead of failing
open.

Verified in a fresh headless session (Nov 2026): `echo hello-control` ran, and
`echo git push` was blocked with the rule's reason and listed in
`permission_denials`.

Edit the rules for your project and run `python3 -m pytest tests/test_guard.py`.
The rules match the raw command text: this guard catches honest mistakes and is
**not a security boundary**. Quoting or indirection can get past it, and it also
fires on quoted text such as `echo "git push"`. That is a deliberate trade:
anchoring rules to the command's position would miss `git -C repo push`.
The orchestrator does not rely on it: workers run with no tools, and approval for
gated tasks is enforced by the engine.

## Architecture

Visual walkthrough: [DIAGRAMS.md](DIAGRAMS.md).

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
- **Hooks don't enforce runtime safety.** Claude Code hooks (the irreversible-command guard) protect interactive development sessions. Runtime approval is enforced by the engine itself, so it applies to every kind of worker, whether that's Python code, an HTTP call or `claude -p`, and doesn't depend on hook configuration.
- **Approval is requested for each attempt.** An interrupted approval-gated task is marked failed on resume so the operator can reconcile its effects.
- **Synchronous deadlines cannot kill Python threads.** A timed-out worker retains its slot and run lock until it exits. Configure I/O deadlines inside blocking workers.
- **One runner per database and run ID.** Runs use an advisory file lock on macOS and Linux. Keep lock files beside the database.
- **"Return to the original worker" means a fresh call with feedback, not the same session.** That makes retries stateless and resumable. If a long context is needed, put it in `spec`.
- **Constraint extraction uses the verifier's messages directly, not an LLM summary.** That's deterministic and free. A human rewrites recurring ones into general rules before any prompt sees them, because raw check output is task-specific and misleads unrelated tasks.
- **Retried side effects must be idempotent.** The engine retries whole tasks, so a worker that writes externally should be idempotent even when gated by approval.

## Current scope

The Python engine, the Claude-backed CLI, the `contains` and `command` checks,
usage accounting, reviewed lessons → Skills, and the irreversible-command hook
are implemented. Tests exercise the Claude protocol with a
local stub; `examples/slugify` runs against real Claude.

## Possible next steps
Every milestone in the original plan is done. Pick these up when a real project
needs them:
- **Sandboxed `command` check** (a container) for plans you didn't write.
- **Per-plan lesson scope**, if worker-type grouping proves too coarse.
- **A pause-for-approval CLI flow**: the CLI currently denies gated tasks;
  `cli_approver` exists for Python API runs.
