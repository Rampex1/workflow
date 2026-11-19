# claude

My Claude Code skills and subagents.

## Install

```sh
# from this folder
mkdir -p ~/.claude/skills && cp -R skills/* ~/.claude/skills/
mkdir -p ~/.claude/agents && cp agents/*.md ~/.claude/agents/
```

Start a new Claude Code session to pick them up. It's a copy, so rerun this after editing a skill or subagent.

## Context

Put anything that isn't in the codebase (a mentor's requirements doc, meeting notes, Slack threads, API specs) in `context/` at the root of the repo you're working in. Both skills read it, along with the codebase, before asking anything. Keep it out of git without touching the team's `.gitignore`:

```sh
mkdir -p context && echo "context/" >> .git/info/exclude
```

## Skills

- `/design <project or requirement docs>`: requirements and questions, research by a crew chosen for the project, key decisions for you to approve, then a cited design doc reviewed adversarially, ending with milestones sized for `/feature`.
- `/feature <task or milestone>`: runs a change end to end, orchestrating a crew it picks from the subagents below. A plan-mode plan (`researcher` agents, every decision with alternatives) for you to approve, failing tests first (`test-writer`), implementation, independent review (`reviewer`, plus `/code-review` for big changes), then a report with proposed `CLAUDE.md` lessons.

## Subagents

Claude delegates to these on its own when a task matches, or ask by name ("have the reviewer check this diff").

- `researcher`: read-only; answers one focused question with cited evidence, options and unknowns.
- `test-writer`: writes tests in the codebase's style and runs them; never changes the code under test.
- `reviewer`: harsh, independent review of a diff against its goal; reports findings with severity, never edits.
