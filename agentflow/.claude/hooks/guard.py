"""PreToolUse hook for Bash: ask (or deny) before commands in .claude/irreversible.json.

Reads the hook payload on stdin; prints a permission decision only when a rule matches.
A guardrail against honest mistakes, not a security boundary: regexes over the raw
command string can be evaded and can match quoted text (e.g. `echo "git push"`).
"""
import json
import re
import sys
from pathlib import Path

RULES = Path(__file__).resolve().parents[1] / "irreversible.json"


def decide(command: str, rules_path: Path = RULES):
    """Return (decision, reason) for the first matching rule, or None to stay silent."""
    try:
        rules = json.loads(rules_path.read_text())["rules"]
        compiled = [(re.compile(r["pattern"]), r.get("decision", "ask"), r["reason"]) for r in rules]
        assert all(d in ("ask", "deny") for _, d, _ in compiled), "decision must be ask or deny"
    except Exception as e:  # broken rule file: fail toward a human, never silently open
        return "ask", f"irreversible-command guard is misconfigured ({type(e).__name__}: {e})"
    for pattern, decision, reason in compiled:
        if pattern.search(command):
            return decision, f"Irreversible action ({reason}). Matched rule: {pattern.pattern}"
    return None


def main():
    payload = json.load(sys.stdin)
    result = decide(payload.get("tool_input", {}).get("command", ""))
    if result:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": result[0],
            "permissionDecisionReason": result[1],
        }}))


if __name__ == "__main__":
    main()
