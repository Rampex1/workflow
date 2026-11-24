---
name: notify
description: Turn Telegram phone notifications on or off for this session only. Off by default.
disable-model-invocation: true
argument-hint: on [name] | off
---

Run exactly one command, then reply in one line: phone notifications are now on (naming the title, if one was given) or off for this session.

- If `$ARGUMENTS` is `off`: `rm -f ~/.claude/notify-phone.d/${CLAUDE_SESSION_ID}`
- Otherwise: the name is whatever follows `on` in `$ARGUMENTS` (may be empty). Run `mkdir -p ~/.claude/notify-phone.d && printf '%s' '<name>' > ~/.claude/notify-phone.d/${CLAUDE_SESSION_ID}`, with any `'` in the name removed. Notifications are titled with this name; empty means the project folder name.

When turning it on, also follow this for the rest of the session: while phone notifications are on, if you stop with work still left that you'd do on "continue" (a milestone, the next phase, remaining tasks), end your reply with a final line that is exactly `⏭ more to do`. Leave it out when the task is finished or you need the user to answer a question or make a decision.

If `~/.claude/telegram.env` doesn't exist, say so: messages can't be sent until it's set up (see the "Phone notifications" section of the workflow repo's `claude/README.md`).
