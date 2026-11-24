#!/bin/sh
# Stop hook: messages "Claude finished" to your phone through a Telegram bot.
# Credentials live in ~/.claude/telegram.env (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID).
# Per session, off by default: `/notify on` creates ~/.claude/notify-phone.d/<session id>.
# ponytail: flag files of ended sessions are never cleaned up; they're empty, delete the folder anytime.
sid=$(sed -n 's/.*"session_id" *: *"\([^"]*\)".*/\1/p' | head -1)
[ -n "$sid" ] && [ -f "$HOME/.claude/notify-phone.d/$sid" ] || exit 0
. "$HOME/.claude/telegram.env" 2>/dev/null || exit 0
curl -s -m 5 "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
  --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
  --data-urlencode "text=Claude finished: $(basename "${CLAUDE_PROJECT_DIR:-$PWD}")" >/dev/null 2>&1
exit 0
