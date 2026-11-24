---
name: notify
description: Turn Telegram phone notifications on or off for this session only. Off by default.
disable-model-invocation: true
argument-hint: on | off
---

Run exactly one command, then reply in one line: phone notifications are now on (or off) for this session.

- If `$ARGUMENTS` is `off`: `rm -f ~/.claude/notify-phone.d/${CLAUDE_SESSION_ID}`
- Otherwise: `mkdir -p ~/.claude/notify-phone.d && touch ~/.claude/notify-phone.d/${CLAUDE_SESSION_ID}`

If `~/.claude/telegram.env` doesn't exist, say so: messages can't be sent until it's set up (see the "Phone notifications" section of the workflow repo's `claude/README.md`).
