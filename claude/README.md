# claude

My Claude Code skills.

## Install

```sh
# from this folder
mkdir -p ~/.claude/skills && cp -R skills/* ~/.claude/skills/
```

Start a new Claude Code session to pick them up. It's a copy, so rerun this after editing a skill.

## Skills

- `/feature <task>`: runs a change end to end. A plan-mode plan (subagent research, every decision with alternatives) for you to approve, failing tests first, implementation, `/code-review`, then a report with proposed `CLAUDE.md` lessons.
