# claude

My Claude Code skills and subagents.

## Install

```sh
# from this folder: symlink, so edits here apply right away
mkdir -p ~/.claude/skills ~/.claude/agents
for d in skills/*/; do [ "$d" = skills/external/ ] || ln -sfn "$PWD/$d" ~/.claude/skills/$(basename "$d"); done
for f in agents/*.md; do ln -sf "$PWD/$f" ~/.claude/agents/; done
```

Start a new Claude Code session to pick them up. Rerun only when you add a new skill or subagent.

## External

Skills and plugins by others that I've installed: one folder each in [`skills/external/`](skills/external/), with source, install command and usage (archify, graphify, i-have-adhd, impeccable, ponytail).

## Context

Put anything that isn't in the codebase (a mentor's requirements doc, meeting notes, Slack threads, API specs) in `context/` at the root of the repo you're working in. Both skills read it, along with the codebase, before asking anything. Keep it out of git without touching the team's `.gitignore`:

```sh
mkdir -p context && echo "context/" >> .git/info/exclude
```

## Research

The skills keep a record of their work in `research/` at the repo root: `findings/` (one cited file per research question), `decisions.md`, `design/<slug>.md` (from `/design`) and `plans/<slug>.md` (from `/feature`). It stays local: the skills add it to `.git/info/exclude`, and later runs reuse it.

## Skills

- `/design <project or requirement docs>`: requirements and questions, research by a crew chosen for the project, key decisions for you to approve, then a cited design doc reviewed adversarially, ending with milestones sized for `/feature`.
- `/feature <task or milestone>`: runs a change end to end, orchestrating a crew it picks from the subagents below. A plan-mode plan (`researcher` agents, every decision with alternatives) for you to approve. Then, without check-ins, on a local `feature/<slug>` branch (never pushed): a baseline test run, failing tests first (`test-writer`), implementation, independent review (`reviewer`, plus `/code-review` for big changes), with a Progress log that survives compaction and every judgment call logged as a ruling. A Stop hook (`stop-gate.sh`) blocks it from finishing while the plan's "done means" commands fail. Ends with a report: commits, rulings, and proposed lessons for `CLAUDE.md`.

## Subagents

Claude delegates to these on its own when a task matches, or ask by name ("have the reviewer check this diff").

- `researcher`: read-only; answers one focused question with cited evidence, options and unknowns.
- `test-writer`: writes tests in the codebase's style and runs them; never changes the code under test.
- `reviewer`: harsh, independent review of a diff against its goal; reports findings with severity, never edits.
