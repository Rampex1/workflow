# claude

My Claude Code skills and subagents.

## Install

```sh
# from this folder
mkdir -p ~/.claude/skills && cp -R skills/* ~/.claude/skills/
mkdir -p ~/.claude/agents && cp agents/*.md ~/.claude/agents/
```

Start a new Claude Code session to pick them up. It's a copy, so rerun this after editing a skill or subagent.

## Skills

- `/feature <task>`: runs a change end to end, orchestrating the subagents below. A plan-mode plan (`researcher` agents, every decision with alternatives) for you to approve, failing tests first (`test-writer`), implementation, independent review (`reviewer`, plus `/code-review` for big changes), then a report with proposed `CLAUDE.md` lessons.

## Subagents

Claude delegates to these on its own when a task matches, or ask by name ("have the reviewer check this diff").

- `researcher`: read-only; answers one focused question with cited evidence, options and unknowns.
- `test-writer`: writes tests in the codebase's style and runs them; never changes the code under test.
- `reviewer`: harsh, independent review of a diff against its goal; reports findings with severity, never edits.
