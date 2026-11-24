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

## Phone notifications

Per session and off by default. When on, a Telegram bot messages you "Claude finished: <project>" plus the tail of Claude's last message each time Claude finishes a task. While notifications are on, Claude ends a reply with `⏭ more to do` when work is left; then the message starts with ⏸ and has a **Continue** button: tap it (within an hour) and that session picks up again as if you'd typed "continue". The paused message also shows your plan usage (`Session 23% (resets 17:00) · Week 41%`) so you can decide whether to spend more. Otherwise it starts with ✅, with no button. To give a session any other prompt, reply to its message in Telegram (swipe left on it, type, send); the session picks up your reply as its next prompt and 👍 marks it received. Works on both kinds of message within an hour; only replies from your own chat count. In a long session, if Claude seems to have forgotten the marker, run `/notify on` again. Needs `jq`.

One-time setup: install the `/notify` skill (the Install loop above), symlink the hook and add it to `~/.claude/settings.json`:

```sh
mkdir -p ~/.claude/hooks && ln -sf "$PWD/hooks/notify-phone.sh" ~/.claude/hooks/
```

```json
"hooks": {
  "Stop": [{ "hooks": [{ "type": "command", "command": "\"$HOME/.claude/hooks/notify-phone.sh\"", "asyncRewake": true, "timeout": 3700 }] }]
}
```

Usage comes from the status line (hooks don't receive it), so also symlink `hooks/statusline.sh` the same way and add `"statusLine": { "type": "command", "command": "\"$HOME/.claude/hooks/statusline.sh\"" }`. It shows the same usage line at the bottom of the terminal.

Turn it on:

1. In Telegram, message [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token it gives you.
2. Send your new bot any message, then get your chat id from `curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates"` (the `"chat":{"id":...}` number).
3. Save both once, in `~/.claude/telegram.env` (outside every repo; the token is a secret, so keep it private):

```sh
printf 'TELEGRAM_TOKEN=%s\nTELEGRAM_CHAT_ID=%s\n' '<TOKEN>' '<CHAT_ID>' > ~/.claude/telegram.env && chmod 600 ~/.claude/telegram.env
```

Then, in any session, type `/notify on`, `/notify on <name>` (titles that session's messages, e.g. `/notify on auth refactor`, so you can tell sessions apart; default is the project folder name) or `/notify off`. It applies to that session only; new sessions start off.

## External

Skills and plugins by others that I've installed: one folder each in [`skills/external/`](skills/external/), with source, install command and usage (archify, graphify, i-have-adhd, impeccable, ponytail).

## Context

Put anything that isn't in the codebase (a mentor's requirements doc, meeting notes, Slack threads, API specs) in `context/` at the root of the repo you're working in. Both skills read it, along with the codebase, before asking anything. Keep it out of git without touching the team's `.gitignore`:

```sh
mkdir -p context && echo "context/" >> .git/info/exclude
```

## Research

The skills keep a record of their work in `research/` at the repo root: `findings/` (one cited file per research question), `decisions.md`, `design/<slug>.md` (from `/design`), `plans/<slug>.md` (from `/feature`) and `onboarding/` (from `/onboarding`). It stays local: the skills add it to `.git/info/exclude`, and later runs reuse it.

## Skills

- `/design <project or requirement docs>`: requirements and questions, research by a crew chosen for the project, key decisions for you to approve, then a cited design doc reviewed adversarially, ending with milestones sized for `/feature`.
- `/feature <task or milestone>`: runs a change end to end, orchestrating a crew it picks from the subagents below. A plan-mode plan (`researcher` agents, every decision with alternatives) for you to approve. Then, without check-ins, on a local `feature/<slug>` branch (never pushed): a baseline test run, failing tests first (`test-writer`), implementation, independent review (`reviewer`, plus `/code-review` for big changes), with a Progress log that survives compaction and every judgment call logged as a ruling. A Stop hook (`stop-gate.sh`) blocks it from finishing while the plan's "done means" commands fail. Ends with a report: commits, rulings, and proposed lessons for `CLAUDE.md`.
- `/onboarding [area]`: onboards you onto an unfamiliar repo. Researchers map the area you'll work on, it runs the build and tests to prove the setup, draws Archify diagrams, and writes a two-page cited doc to `research/onboarding/<repo>.md` (reading order, key flows, where changes go, gotchas, glossary, who to ask, questions for your mentor, hands-on exercises). `/onboarding quiz` quizzes you on it one question at a time, and brings back missed questions later.

## Subagents

Claude delegates to these on its own when a task matches, or ask by name ("have the reviewer check this diff").

- `researcher`: read-only; answers one focused question with cited evidence, options and unknowns.
- `test-writer`: writes tests in the codebase's style and runs them; never changes the code under test.
- `reviewer`: harsh, independent review of a diff against its goal; reports findings with severity, never edits.
