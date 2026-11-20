#!/bin/sh
# Stop hook for /feature: blocks Claude from finishing while the plan's
# "done means" check fails. No-op unless research/.gate exists, so it's
# harmless for the rest of the session once /feature removes the gate.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
gate=research/.gate
blocks=research/.gate-blocks
[ -f "$gate" ] || exit 0

if out=$(sh "$gate" 2>&1); then
  rm -f "$blocks"
  exit 0
fi

count=$(( $(cat "$blocks" 2>/dev/null || echo 0) + 1 ))
echo "$count" > "$blocks"
if [ "$count" -gt 5 ]; then
  # Brake: never trap the session in an endless loop.
  rm -f "$blocks"
  exit 0
fi

{
  echo "Stop gate ($count/5): the done-means check in research/.gate fails, so you can't finish yet. Last 40 lines:"
  printf '%s\n' "$out" | tail -40
  echo "Keep fixing. If you must stop under the /feature stop list, delete research/.gate and log a Ruling in Progress saying why."
} >&2
exit 2
