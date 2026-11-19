"""`fix`: a stub Claude edits a throwaway worktree; the diff is checked in a fresh one; the repo is untouched."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


CHECK = f"{sys.executable} -m pytest -q -p no:cacheprovider"


def make_repo(tmp_path, op):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "calc.py").write_text(f"def add(a, b):\n    return a {op} b\n")
    (repo / "test_calc.py").write_text("from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")
    sh(repo, "git", "init", "-q")
    sh(repo, "git", "add", ".")
    sh(repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    return repo


def fix(tmp_path, repo, env=None):
    return subprocess.run([sys.executable, "-m", "agentflow", "--db", str(tmp_path / "w" / "runs.db"),
                           "--skills", str(tmp_path / "skills"), "fix", "bug", "--repo", str(repo),
                           "--issue", "add() subtracts", "--check", CHECK, "--readonly", "test_calc.py"],
                          cwd=ROOT, env=env, capture_output=True, text=True)


def test_check_that_already_passes_is_refused(tmp_path):
    r = fix(tmp_path, make_repo(tmp_path, "+"))  # no claude on purpose: refused before any call
    assert r.returncode == 1 and "already passes" in r.stderr


def test_fix_retries_until_tests_pass_without_touching_readonly_or_the_repo(tmp_path):
    repo = make_repo(tmp_path, "-")

    # Attempt 1 cheats by editing the read-only test; attempt 2 fixes the code.
    stub = tmp_path / "bin" / "claude"
    stub.parent.mkdir()
    stub.write_text(f"""#!{sys.executable}
import json, os, sys
argv = sys.argv
assert '--restricted' in argv and argv[argv.index('--permission-mode') + 1] == 'dontAsk'
payload = json.loads(sys.stdin.read().split('\\n\\n')[-1])
assert 'repo' not in payload['task'] and 'FAILED' in payload['task']['failing_check'] and f"Bash({{payload['task']['check']}})" in argv
if payload['attempt'] == 1:
    open('test_calc.py', 'w').write('def test_add():\\n    pass\\n')
else:
    assert 'read-only' in payload['failure'][0]
    open('calc.py', 'w').write('def add(a, b):\\n    return a + b\\n')
    os.makedirs('__pycache__'); open('__pycache__/calc.pyc', 'w').write('junk')
print(json.dumps(dict(result='done', total_cost_usd=0.01)))
""")
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub.parent}:{os.environ['PATH']}"}
    r = fix(tmp_path, repo, env)
    assert r.returncode == 0, r.stderr
    task = json.loads(r.stdout)["fix"]
    assert task["status"] == "done" and task["attempts"] == 2
    assert "+    return a + b" in task["output"] and "test_calc" not in task["output"]
    assert "__pycache__" not in task["output"]

    patch = tmp_path / "w" / "bug-fix.patch"
    assert patch.read_text() == task["output"] and "apply" in r.stderr
    assert sh(repo, "git", "status", "--porcelain") == ""             # real repo untouched
    assert len(sh(repo, "git", "worktree", "list").splitlines()) == 1  # no leftover worktrees
    sh(repo, "git", "apply", str(patch))
    assert "a + b" in (repo / "calc.py").read_text()
