import json
import os
import subprocess
import sys
from pathlib import Path


def test_objective_to_persistent_run_with_stub_claude(tmp_path):
    stub = tmp_path / "claude"
    stub.write_text(f"""#!{sys.executable}
import json
import sys
assert sys.argv[sys.argv.index('--tools') + 1] == ''
payload = json.loads(sys.stdin.read().split('\\n\\n')[-1])
if 'objective' in payload:
    assert payload['constraints'] == ['Use plain text']
    result = json.dumps([dict(id='report', role='implementer', brief='Write report',
                              depends_on=[], contains=['Ready'], risk='contained')])
else:
    result = 'Ready' if payload['failure'] else 'Draft'
print(json.dumps(dict(result=result)))
""")
    stub.chmod(0o755)
    constraints = tmp_path / "constraints.json"
    constraints.write_text('["Use plain text"]')
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    root = Path(__file__).resolve().parents[1]
    cli = [sys.executable, "-m", "agentflow", "--db", str(tmp_path / "runs.db"),
           "--skills", str(tmp_path / "skills")]

    def invoke(*args):
        return json.loads(subprocess.check_output([*cli, *args], cwd=root, env=env, text=True))

    report = invoke("run", "test", "--objective", "Write report",
                    "--constraints-from", str(constraints))["report"]
    assert report["output"] == "Ready"
    assert report["attempts"] == 2
    assert invoke("status", "test") == invoke("resume", "test")
