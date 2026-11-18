import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow import Task
from agentflow.__main__ import command, prepare

ROOT = Path(__file__).resolve().parents[1]


def task(tmp_path, **spec):
    (tmp_path / "test_m.py").write_text("from m import f\ndef test_f():\n    assert f() == 2\n")
    return Task("t", "implementer", checks=["command"], spec={
        "output_file": "m.py", "fixtures": str(tmp_path),
        "command": ["{python}", "-m", "pytest", "-q", "-p", "no:cacheprovider"], **spec})


def test_command_passes_and_strips_code_fence(tmp_path):
    assert command(task(tmp_path), "```python\ndef f():\n    return 2\n```\n") is None


def test_command_failure_returns_test_output(tmp_path):
    msg = command(task(tmp_path), "def f():\n    return 3\n")
    assert msg.split("\n")[0].startswith("exited 1: FAILED test_m.py::test_f")  # first line = lesson
    assert "assert 3 == 2" in msg


def test_command_rejects_output_path_escape(tmp_path):
    assert "escapes" in command(task(tmp_path, output_file="../evil.py"), "x = 1")


def test_prepare_validates_and_pins_fixtures(tmp_path):
    with pytest.raises(ValueError, match="spec.command"):
        prepare([Task("t", "implementer", checks=["command"], spec={"output_file": "m.py"})], "p.json")
    t = Task("t", "implementer", checks=["command"],
             spec={"output_file": "m.py", "command": ["true"], "fixtures": "fx"})
    prepare([t], str(tmp_path / "plan.json"))
    assert t.spec["fixtures"] == str((tmp_path / "fx").resolve())


def test_plan_with_command_check_corrects_code_and_reports_cost(tmp_path):
    """Stub Claude writes buggy code, sees pytest output as failure, fixes it."""
    stub = tmp_path / "bin" / "claude"
    stub.parent.mkdir()
    stub.write_text(f"""#!{sys.executable}
import json, sys
payload = json.loads(sys.stdin.read().split('\\n\\n')[-1])
fixed = any('assert 3 == 2' in f for f in payload['failure'])
code = '```python\\ndef f():\\n    return ' + ('2' if fixed else '3') + '\\n```'
print(json.dumps(dict(result=code, total_cost_usd=0.01)))
""")
    stub.chmod(0o755)
    (tmp_path / "fx").mkdir()
    (tmp_path / "fx" / "test_m.py").write_text("from m import f\ndef test_f():\n    assert f() == 2\n")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"tasks": [{
        "id": "code", "worker": "implementer", "checks": ["command"],
        "spec": {"brief": "f returns 2", "output_file": "m.py", "fixtures": "fx",
                 "command": ["{python}", "-m", "pytest", "-q", "-p", "no:cacheprovider"]}}]}))
    env = {**os.environ, "PATH": f"{stub.parent}:{os.environ['PATH']}"}
    r = subprocess.run([sys.executable, "-m", "agentflow", "--db", str(tmp_path / "runs.db"),
                        "run", "x", "--plan", str(plan)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)["code"]
    assert out["status"] == "done" and out["attempts"] == 2
    assert "agentflow: 2 Claude calls, $0.0200 reported cost" in r.stderr
