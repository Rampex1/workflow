"""Lessons -> proposed skill -> human approval -> constraints reach the worker prompt."""
import json
import os
import subprocess
import sys
from pathlib import Path

from agentflow import Store

ROOT = Path(__file__).resolve().parents[1]


def cli(tmp_path, *args, env=None):
    r = subprocess.run([sys.executable, "-m", "agentflow", "--db", str(tmp_path / "w" / "runs.db"),
                        "--skills", str(tmp_path / "skills"), *args],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout), r.stderr


def seed(tmp_path):
    (tmp_path / "w").mkdir()
    store = Store(str(tmp_path / "w" / "runs.db"))
    for run in ("r1", "r2"):
        store.log(run, "t", "lesson", {"worker": "implementer", "errors": ["command: exited 1: FAILED test_len\nlog..."]})
    store.log("r3", "t", "lesson", {"worker": "implementer", "errors": ["contains: once only"]})
    store.db.close()


def test_propose_approve_and_inject(tmp_path):
    seed(tmp_path)
    listed, _ = cli(tmp_path, "lessons")
    assert listed == {"implementer": {"contains: once only": 1, "command: exited 1: FAILED test_len": 2}}

    _, err = cli(tmp_path, "lessons", "--propose")  # default --min-count 2
    draft = tmp_path / "w" / "proposals" / "implementer-constraints" / "SKILL.md"
    assert "proposed" in err and "FAILED test_len" in draft.read_text()
    assert "once only" not in draft.read_text()

    draft.write_text(draft.read_text().replace("- command: exited 1: FAILED test_len",
                                               "- Slugs are at most 50 characters."))  # human edit
    cli(tmp_path, "lessons", "--approve", "implementer")
    skill = tmp_path / "skills" / "implementer-constraints" / "SKILL.md"
    assert "name: implementer-constraints" in skill.read_text()
    assert not draft.parent.exists()

    listed, _ = cli(tmp_path, "lessons")  # reviewed lesson is not proposed again
    assert listed == {"implementer": {"contains: once only": 1}}

    stub = tmp_path / "bin" / "claude"
    stub.parent.mkdir()
    stub.write_text(f"""#!{sys.executable}
import json, sys
payload = json.loads(sys.stdin.read().split('\\n\\n')[-1])
print(json.dumps(dict(result=payload['constraints'], total_cost_usd=0)))
""")
    stub.chmod(0o755)
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"tasks": [{"id": "a", "worker": "implementer",
                                           "spec": {"brief": "b"}}]}))
    env = {**os.environ, "PATH": f"{stub.parent}:{os.environ['PATH']}"}
    out, _ = cli(tmp_path, "run", "x", "--plan", str(plan), env=env)
    constraints = out["a"]["output"]
    assert "- Slugs are at most 50 characters." in constraints
    assert "<!--" not in constraints and "name:" not in constraints


def test_approved_skills_reach_the_planner(tmp_path):
    skill = tmp_path / "skills" / "implementer-constraints" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: implementer-constraints\n---\n<!-- note -->\n- Slugs are at most 50 characters.\n")
    stub = tmp_path / "bin" / "claude"
    stub.parent.mkdir()
    stub.write_text(f"""#!{sys.executable}
import json, sys
payload = json.loads(sys.stdin.read().split('\\n\\n')[-1])
if 'objective' in payload:  # echo the planner's constraints back as the task brief
    result = json.dumps([dict(id='a', role='implementer', brief=payload['constraints'],
                              depends_on=[], contains=['x'], risk='contained')])
else:
    result = 'x' + json.dumps(payload['task']['brief'])
print(json.dumps(dict(result=result, total_cost_usd=0)))
""")
    stub.chmod(0o755)
    constraints = tmp_path / "c.json"
    constraints.write_text('["Use plain text"]')
    env = {**os.environ, "PATH": f"{stub.parent}:{os.environ['PATH']}"}
    out, _ = cli(tmp_path, "run", "x", "--objective", "o", "--constraints-from", str(constraints), env=env)
    assert json.loads(out["a"]["output"][1:]) == [
        "Use plain text", "For implementer tasks:\n- Slugs are at most 50 characters."]


def test_reject_discards_proposal_and_marks_reviewed(tmp_path):
    seed(tmp_path)
    cli(tmp_path, "lessons", "--propose", "--min-count", "1")
    cli(tmp_path, "lessons", "--reject", "implementer")
    assert not (tmp_path / "skills").exists()
    assert cli(tmp_path, "lessons")[0] == {}
