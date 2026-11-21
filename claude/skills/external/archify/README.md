# archify

Interactive HTML diagrams (architecture, sequence, ERD, ...) and one-page explainers, including code-backed diagrams of a repo.

- Source: https://github.com/tt-a1i/archify (Apache-2.0)
- Type: skill (Claude picks it when you ask for a diagram)

```sh
git clone --depth 1 https://github.com/tt-a1i/archify /tmp/archify && cp -R /tmp/archify/archify ~/.claude/skills/archify
node ~/.claude/skills/archify/bin/archify.mjs doctor
```

Use: "Use Archify to diagram this repo's request flow". Output goes to `.archify/` (add it to `.git/info/exclude`). Set `ARCHIFY_UPDATE_CHECK_DISABLED=1` to turn off its update check.
