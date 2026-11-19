# agentflow diagrams

agentflow runs a list of tasks for Claude, where some tasks depend on others.
Each task is a `claude -p` call. Its output must pass an automatic check, and a
failed check sends the error back to Claude for another try. All state is kept
in SQLite, so a run can be resumed.

## 1. The whole thing

```mermaid
flowchart LR
    subgraph IN["Where tasks come from"]
        OBJ["--objective 'Draft a design...'"] --> PLANNER["planner (one Claude call)"]
        PLANFILE["--plan plan.json (hand-written)"]
    end

    PLANNER -->|"JSON list of tasks"| VALIDATE
    PLANFILE --> VALIDATE

    VALIDATE{"validate()<br/>no duplicate ids, cycles,<br/>unknown workers or checks"} -->|ok| ORCH
    VALIDATE -->|bad| ERR["refuse to run"]

    ORCH["Orchestrator<br/>runs tasks in dependency order,<br/>up to 4 at a time"] --> TASK["run one task<br/>(diagram 2)"]
    TASK --> ORCH
    ORCH <--> DB[("SQLite runs.db<br/>tasks: current state<br/>events: append-only log")]

    DB --> STATUS["status / resume"]
```

## 2. What happens to one task

```mermaid
flowchart TD
    START(["task is pending"]) --> DEPS{"did all its deps finish?"}
    DEPS -->|"a dep failed or was skipped"| SKIP(["skipped"])
    DEPS -->|yes| GATE{"requires_approval?"}
    GATE -->|"yes: ask approver<br/>(the CLI always says no)"| REJ(["rejected"])
    GATE -->|"no, or approved"| CALL

    CALL["worker = claude -p as role<br/>(researcher / implementer / reviewer)<br/>gets: brief + dep outputs + past errors<br/>+ approved constraints"] --> CHECK

    CHECK{"checks"} -->|"contains: required strings present?<br/>command: write file, run pytest"| PASS{"pass?"}
    PASS -->|yes| DONE(["done: output saved"])
    PASS -->|"no: error text becomes feedback"| TRIES{"fewer than 4 attempts?"}
    TRIES -->|yes| CALL
    TRIES -->|no| FAIL(["failed: its dependents get skipped"])
```

## 3. The learning loop: lessons become skills

```mermaid
flowchart LR
    A["task fails a check,<br/>then passes on a retry"] --> L["first line of the error<br/>saved as a lesson for that role"]
    L --> P["agentflow lessons --propose<br/>(drafts a skill for lessons seen in 2+ tasks)"]
    P --> H["a human rewrites it<br/>as a general rule"]
    H -->|"--approve"| S[".claude/skills/role-constraints/SKILL.md"]
    H -->|"--reject"| X["thrown away"]
    S -->|"--objective runs: sent to the planner,<br/>shaping how work is split and checked"| PL["planner"]
    S -->|"sent as constraints in every<br/>future prompt for that role"| W["workers"]
    PL --> C["next run passes first time"]
    W --> C
```

## 4. Fixing an issue in a codebase (`fix`)

```mermaid
flowchart TD
    I["fix NAME --repo --issue --check --readonly"] --> PIN["pin the repo's current commit"]
    PIN --> PRE{"run the check<br/>on that commit"}
    PRE -->|passes| REF(["refused: the check<br/>can't detect the issue"])
    PRE -->|"fails (expected)"| W["fresh git worktree:<br/>Claude reads and edits files,<br/>may run only the check"]
    W --> D["output = the staged diff"]
    D --> C["diff_command, in another fresh worktree:<br/>apply the diff, refuse read-only edits,<br/>run the check"]
    C --> OK{"passed?"}
    OK -->|yes| P(["patch file:<br/>you review, then git apply"])
    OK -->|"no: output fed back"| T{"fewer than 4 attempts?"}
    T -->|yes| W
    T -->|no| F(["failed"])
```

Your checkout is never modified. Every attempt and every check uses its own
throwaway worktree, so a failed attempt leaves nothing behind.

## Example: `examples/slugify/plan.json`

```mermaid
flowchart LR
    S["slugify<br/>(implementer)<br/>check: hidden pytest file"] -->|output passed in| U["usage-note<br/>(reviewer)<br/>check: contains 'slugify('"]
```

1. The hidden test requires slugs of at most 50 characters, and the task brief
   never mentions this. The first attempt fails.
2. The pytest failure is fed back to Claude, and the next attempt passes.
3. `usage-note` then runs, using the slugify code as its input.
4. After the same failure happens in two runs, it can be turned into a
   constraint, so later runs pass on the first try.

The irreversible-command hook (`.claude/hooks/guard.py`) isn't part of the
engine. It's a separate safety net for interactive Claude Code sessions in this
folder. The text roles' Claude calls run with all tools turned off. The `fix`
coder runs with `--restricted`, which ignores project hooks, and its Bash is
limited to the check command.
