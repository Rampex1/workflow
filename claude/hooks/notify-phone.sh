#!/bin/sh
# Stop hook (asyncRewake): messages "Claude finished" to your phone through a Telegram bot,
# with a Continue button. Tapping it wakes this session with "continue" (exit 2 = rewake).
# Credentials live in ~/.claude/telegram.env (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID). Needs jq.
# Per session, off by default: `/notify on [name]` creates ~/.claude/notify-phone.d/<session id>, holding the title.
# ponytail: flag files of ended sessions are never cleaned up; they're tiny, delete the folder anytime.
# ponytail: sessions share one bot; a tap is only seen while its own session polls (up to 1h after stop).
in=$(cat)
sid=$(printf '%s' "$in" | jq -r '.session_id // empty')
d="$HOME/.claude/notify-phone.d"
[ -n "$sid" ] && [ -f "$d/$sid" ] || exit 0
. "$HOME/.claude/telegram.env" 2>/dev/null || exit 0
api="https://api.telegram.org/bot$TELEGRAM_TOKEN"

# Only the latest notification per session keeps listening.
[ -f "$d/$sid.pid" ] && kill "$(cat "$d/$sid.pid")" 2>/dev/null
echo $$ > "$d/$sid.pid"

full=$(printf '%s' "$in" | jq -r '.last_assistant_message // ""')
last=$(printf '%s' "$full" | tail -c 600)
proj=$(cat "$d/$sid")  # title from `/notify on <name>`
[ -n "$proj" ] || proj=$(basename "${CLAUDE_PROJECT_DIR:-$PWD}")
# /notify on asks Claude to end a reply with "⏭ more to do" when work remains.
if printf '%s' "$full" | tail -c 200 | grep -q '⏭ more to do'; then
  msg=$(curl -s -m 10 "$api/sendMessage" \
    --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
    --data-urlencode "text=⏸ Paused, more to do: $proj
$(cat "$d/usage.txt" 2>/dev/null)
$last" \
    --data-urlencode 'reply_markup={"inline_keyboard":[[{"text":"▶ Continue","callback_data":"go"}]]}' \
    | jq -r '.result.message_id // empty')
else
  curl -s -m 10 "$api/sendMessage" --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
    --data-urlencode "text=✅ Done: $proj
$last" >/dev/null
  rm -f "$d/$sid.pid"
  exit 0
fi
[ -n "$msg" ] || exit 0

end=$(( $(date +%s) + 3600 ))
while [ "$(date +%s)" -lt "$end" ]; do
  hit=$(curl -s -m 10 "$api/getUpdates?allowed_updates=%5B%22callback_query%22%5D" | jq -c --argjson m "$msg" \
    '[.result[]? | select(.callback_query.message.message_id == $m)][0] // empty')
  if [ -n "$hit" ]; then
    curl -s -m 5 "$api/getUpdates?offset=$(( $(printf '%s' "$hit" | jq .update_id) + 1 ))&timeout=0" >/dev/null
    curl -s -m 5 "$api/answerCallbackQuery" --data-urlencode "callback_query_id=$(printf '%s' "$hit" | jq -r .callback_query.id)" \
      --data-urlencode "text=Continuing" >/dev/null
    curl -s -m 5 "$api/editMessageReplyMarkup" --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
      --data-urlencode "message_id=$msg" >/dev/null
    rm -f "$d/$sid.pid"
    echo "The user tapped Continue on their phone: continue working on the task." >&2
    exit 2
  fi
  sleep 3
done
rm -f "$d/$sid.pid"
exit 0
