#!/bin/sh
# Stop hook (asyncRewake): messages "Claude finished" to your phone through a Telegram bot,
# with a Continue button (when Claude paused with more to do). Tapping it, or replying to the
# message in Telegram, wakes this session with "continue" or your reply as the prompt (exit 2 = rewake).
# Credentials live in ~/.claude/telegram.env (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID). Needs jq.
# Per session, off by default: `/notify on [name]` creates ~/.claude/notify-phone.d/<session id>, holding the title.
# ponytail: flag files of ended sessions are never cleaned up; they're tiny, delete the folder anytime.
# ponytail: sessions share one bot; a tap or reply is only seen while its own session polls (up to 1h after stop).
in=$(cat)
sid=$(printf '%s' "$in" | jq -r '.session_id // empty')
d="$HOME/.claude/notify-phone.d"
[ -n "$sid" ] && [ -f "$d/$sid" ] || exit 0
. "$HOME/.claude/telegram.env" 2>/dev/null || exit 0

# Claude stops while waiting on a background subagent and is woken when it reports back (a
# <task-notification> naming the launch's tool_use_id). Stay quiet until no agent is pending.
# ponytail: background shells (run_in_background) aren't counted: a dev server never "finishes".
tp=$(printf '%s' "$in" | jq -r '.transcript_path // empty')
if [ -f "$tp" ]; then
  for id in $(jq -r 'select(.type=="user") | .message.content | arrays | .[]
      | select(.type=="tool_result" and ((.content|tostring)|test("Async agent launched"))) | .tool_use_id' "$tp"); do
    grep -q "<tool-use-id>$id</tool-use-id>" "$tp" || exit 0
  done
fi
api="https://api.telegram.org/bot$TELEGRAM_TOKEN"

# Only the latest notification per session keeps listening.
[ -f "$d/$sid.pid" ] && kill "$(cat "$d/$sid.pid")" 2>/dev/null
echo $$ > "$d/$sid.pid"

# HTML escaping for Telegram's parse_mode=HTML.
esc() { sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'; }
title=$(cat "$d/$sid")  # from `/notify on <name>`
[ -n "$title" ] || title=$(basename "${CLAUDE_PROJECT_DIR:-$PWD}")
title=$(printf '%s' "$title" | esc)
# /notify on asks Claude to end a reply with "⏭ more to do" when work remains.
paused=$(printf '%s' "$in" | jq -r '.last_assistant_message // "" | test("⏭ more to do\\s*$")')
# Excerpt: marker dropped, last ~400 chars starting at a line (or word) boundary.
excerpt=$(printf '%s' "$in" | jq -r '.last_assistant_message // ""
  | sub("\\s*⏭ more to do\\s*$"; "") | sub("\\s+$"; "")
  | if length > 400 then .[-400:] | (if test("\n") then sub("^[^\n]*\n"; "") else sub("^\\S*\\s+"; "") end) | "…" + . else . end
  | gsub("&"; "&amp;") | gsub("<"; "&lt;") | gsub(">"; "&gt;")')
send() { t=$1; shift; curl -s -m 10 "$api/sendMessage" --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
  --data-urlencode "parse_mode=HTML" --data-urlencode "text=$t" "$@"; }
if [ "$paused" = true ]; then
  usage=$(cat "$d/usage.txt" 2>/dev/null)
  msg=$(send "⏸ <b>$title</b>${usage:+
📊 $usage}

$excerpt" --data-urlencode 'reply_markup={"inline_keyboard":[[{"text":"▶ Continue","callback_data":"go"}]]}' \
    | jq -r '.result.message_id // empty')
else
  msg=$(send "✅ <b>$title</b>

$excerpt" | jq -r '.result.message_id // empty')
fi
[ -n "$msg" ] || { rm -f "$d/$sid.pid"; exit 0; }

# Wait up to 1h for a Continue tap, or a Telegram reply to this message (sent to Claude as the prompt).
# Only updates from your own chat count: a reply becomes a prompt with this session's tool access.
end=$(( $(date +%s) + 3600 ))
while [ "$(date +%s)" -lt "$end" ]; do
  hit=$(curl -s -m 10 "$api/getUpdates?allowed_updates=%5B%22callback_query%22%2C%22message%22%5D" \
    | jq -c --argjson m "$msg" --arg c "$TELEGRAM_CHAT_ID" '[.result[]? | select(
        (.callback_query.message.message_id == $m and (.callback_query.message.chat.id | tostring) == $c)
        or (.message.reply_to_message.message_id == $m and (.message.chat.id | tostring) == $c and .message.text))][0] // empty')
  if [ -n "$hit" ]; then
    curl -s -m 5 "$api/getUpdates?offset=$(( $(printf '%s' "$hit" | jq .update_id) + 1 ))&timeout=0" >/dev/null
    curl -s -m 5 "$api/editMessageReplyMarkup" --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
      --data-urlencode "message_id=$msg" >/dev/null
    rm -f "$d/$sid.pid"
    cq=$(printf '%s' "$hit" | jq -r '.callback_query.id // empty')
    if [ -n "$cq" ]; then
      curl -s -m 5 "$api/answerCallbackQuery" --data-urlencode "callback_query_id=$cq" \
        --data-urlencode "text=Continuing" >/dev/null
      echo "The user tapped Continue on their phone: continue working on the task." >&2
    else
      curl -s -m 5 "$api/setMessageReaction" --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
        --data-urlencode "message_id=$(printf '%s' "$hit" | jq .message.message_id)" \
        --data-urlencode 'reaction=[{"type":"emoji","emoji":"👍"}]' >/dev/null
      printf 'The user replied from their phone. Treat this as their next prompt:\n%s\n' \
        "$(printf '%s' "$hit" | jq -r .message.text)" >&2
    fi
    exit 2
  fi
  sleep 3
done
rm -f "$d/$sid.pid"
exit 0
