#!/bin/sh
# Status line: shows plan usage and saves it to ~/.claude/notify-phone.d/usage.txt for notify-phone.sh,
# since hooks don't get rate limits but the status line does.
u=$(jq -r '.rate_limits // empty | [
  (.five_hour // empty | "Session \(.used_percentage | floor)%" + (if (.resets_at | type) == "number" then " (resets \(.resets_at | strflocaltime("%H:%M")))" else "" end)),
  (.seven_day // empty | "Week \(.used_percentage | floor)%")
] | join(" · ")')
[ -n "$u" ] && mkdir -p "$HOME/.claude/notify-phone.d" && printf '%s\n' "$u" > "$HOME/.claude/notify-phone.d/usage.txt"
printf '%s\n' "$u"
