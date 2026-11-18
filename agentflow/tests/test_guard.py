import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
from guard import decide  # noqa: E402


@pytest.mark.parametrize("cmd, decision", [
    ("rm -rf /", "deny"),
    ("rm -rf ~", "deny"),
    ("cd x && rm -fr $HOME/", "deny"),
    ("rm -rf build/", "ask"),
    ("rm --recursive dist", "ask"),
    ("git push origin main", "ask"),
    ("git commit -m x && git push --force", "ask"),
    ("git reset --hard HEAD~1", "ask"),
    ("git clean -fd", "ask"),
    ("git branch -D feature", "ask"),
    ("npm publish", "ask"),
    ("terraform apply -auto-approve", "ask"),
    ("kubectl delete pod x", "ask"),
    ("./deploy.sh prod", "ask"),
    ("scripts/deploy", "ask"),
    ("make deploy", "ask"),
    ("psql -c 'DROP TABLE users'", "ask"),
])
def test_irreversible_commands_need_a_human(cmd, decision):
    assert decide(cmd)[0] == decision


@pytest.mark.parametrize("cmd", [
    "ls -la", "rm file.txt", "rm -f a.pyc", "git status", "git pull", "git commit -m 'push later'",
    "python3 -m pytest -q", "cat deployment.yaml", "grep -r deploy_key .", "npm install",
])
def test_ordinary_commands_pass_silently(cmd):
    assert decide(cmd) is None


def test_broken_rules_file_fails_toward_ask(tmp_path):
    bad = tmp_path / "rules.json"
    bad.write_text('{"rules": [{"pattern": "(", "reason": "x"}]}')
    decision, reason = decide("ls", bad)
    assert decision == "ask" and "misconfigured" in reason


def test_hook_protocol_end_to_end():
    def hook(cmd):
        r = subprocess.run([sys.executable, str(ROOT / ".claude" / "hooks" / "guard.py")],
                           input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout

    assert hook("ls") == ""
    out = json.loads(hook("git push"))["hookSpecificOutput"]
    assert out == {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                   "permissionDecisionReason": out["permissionDecisionReason"]}
    assert "publishes commits" in out["permissionDecisionReason"]


@pytest.mark.parametrize("cmd", ["bash deploy.sh", "make test && ./scripts/deploy-prod.sh", "fly deploy"])
def test_deploy_scripts_at_command_position(cmd):
    assert decide(cmd)[0] == "ask"
