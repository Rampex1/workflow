"""Run and inspect Claude-backed artifact workflows."""
import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from functools import partial
from pathlib import Path

from . import DONE, Orchestrator, Store, Task, load_plan, validate

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("researcher", "implementer", "reviewer")
LESSON_RUN = "_lessons"  # pseudo run id in the events table for review decisions
REVIEW_NOTE = ("<!-- agentflow:review Rewrite the new lines below as general rules, delete task-specific "
               "ones, then run: python -m agentflow lessons --approve {worker} -->")
SKILL_TEMPLATE = """---
name: {worker}-constraints
description: Constraints learned from verified corrections of {worker} tasks. Apply them to every {worker} deliverable.
---
Follow these constraints. Each one comes from a check that failed and was then fixed."""
FENCE = re.compile(r"\A\s*```[\w+-]*\n(.*?)\n?```\s*\Z", re.S)


def claude(role, payload, meta=None, timeout=None, effort="medium", max_output_tokens=8000):
    """One stateless Claude call. effort + output cap bound runaway generations (seen: 77k tokens, $1.56)."""
    guide = (ROOT / ".claude" / "agents" / f"{role}.md").read_text().split("---", 2)[2]
    meta = {} if meta is None else meta
    meta["llm_calls"] = meta.get("llm_calls", 0) + 1  # counted before the call: a killed call still happened
    try:
        reply = subprocess.run(
            ["claude", "-p", "--tools", "", "--setting-sources", "project", "--output-format", "json",
             "--no-session-persistence", "--effort", effort],
            input=f"{guide}\n\n{json.dumps(payload)}", capture_output=True, text=True, cwd=ROOT,
            env={**os.environ, "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(max_output_tokens)},
            timeout=timeout or 180,
        )
    except subprocess.TimeoutExpired:
        meta["timeouts"] = meta.get("timeouts", 0) + 1  # killed: Claude never reports this call's cost
        raise
    try:
        envelope = json.loads(reply.stdout)
    except json.JSONDecodeError:  # crashed before replying: surface why instead of a bare exit code
        raise RuntimeError(f"claude exited {reply.returncode}: {(reply.stderr or reply.stdout)[-500:]}") from None
    # Recorded before the error check: failed calls (incl. output-cap hits) still cost money.
    meta["cost_usd"] = meta.get("cost_usd", 0) + (envelope.get("total_cost_usd") or 0)
    if reply.returncode or envelope.get("is_error") or not isinstance(envelope.get("result"), str):
        raise ValueError(f"Claude returned an unsuccessful response for {role}: {str(envelope.get('result'))[:300]}")
    return envelope["result"]


def skill_body(path):
    """Approved constraint text, without frontmatter or HTML comments."""
    if not path.exists():
        return ""
    return re.sub(r"<!--.*?-->", "", path.read_text().split("---", 2)[2], flags=re.S).strip()


def work(opts, ctx):
    # Only human-approved constraints reach the model; raw lessons wait in `lessons --propose`.
    return claude(ctx.task.worker, {
        "task": ctx.task.spec, "dependencies": ctx.inputs, "failure": ctx.feedback,
        "constraints": skill_body(opts.skills / f"{ctx.task.worker}-constraints" / "SKILL.md"),
        "attempt": ctx.attempt,
    }, ctx.meta, ctx.task.timeout, ctx.task.spec.get("effort", opts.effort), opts.max_output_tokens)


def contains(task, output):
    markers = task.spec.get("contains")
    if not isinstance(markers, list) or not markers or not all(isinstance(m, str) and m.strip() for m in markers):
        return "contains requires a nonempty array of literal strings"
    missing = [marker for marker in markers if marker not in output]
    return f"Missing required text: {missing}" if missing else None


def command(task, output):
    """Write the output into a scratch dir beside copied fixtures, run spec.command, pass on exit 0."""
    # ponytail: runs model-written code unsandboxed in a temp dir; use a container for untrusted plans.
    spec = task.spec
    if not isinstance(output, str):
        return "command check needs text output"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        if spec.get("fixtures"):
            shutil.copytree(spec["fixtures"], root, dirs_exist_ok=True)
        target = (root / spec["output_file"]).resolve()
        if not target.is_relative_to(root):
            return f"output_file escapes the work directory: {spec['output_file']!r}"
        target.parent.mkdir(parents=True, exist_ok=True)
        fenced = FENCE.match(output)
        target.write_text(fenced[1] if fenced else output)
        argv = [sys.executable if arg == "{python}" else arg for arg in spec["command"]]
        result = subprocess.run(argv, cwd=root, capture_output=True, text=True,
                                timeout=spec.get("command_timeout", 120))
    if result.returncode:
        log = result.stdout + result.stderr
        lines = [line for line in log.splitlines() if line.strip()]
        # First line is the lesson: pytest's FAILED/ERROR summary, else the last line (e.g. an exception).
        summary = "; ".join(l for l in lines if l.startswith(("FAILED ", "ERROR "))) or (lines[-1] if lines else "no output")
        return f"exited {result.returncode}: {summary}\n{log[-3000:]}"
    return None


def prepare(tasks, plan_path):
    """Fail fast on malformed command specs and pin fixture paths so resume works from any cwd."""
    for t in tasks:
        if "command" not in t.checks:
            continue
        if not (isinstance(t.spec.get("command"), list) and t.spec["command"] and t.spec.get("output_file")):
            raise ValueError(f"{t.id}: command check needs spec.command (nonempty list) and spec.output_file")
        if t.spec.get("fixtures"):
            t.spec["fixtures"] = str((Path(plan_path).parent / t.spec["fixtures"]).resolve())
    return tasks


def usage(store, run_id):
    metas = [d["meta"] for _, _, kind, d in store.events(run_id)
             if kind in ("plan", "attempt") and isinstance(d, dict) and d.get("meta")]
    return tuple(sum(m.get(k, 0) for m in metas) for k in ("llm_calls", "cost_usd", "timeouts"))


def review_lessons(args, store):
    """List unreviewed lessons; propose, approve or reject <worker>-constraints skills."""
    proposals = Path(args.db).parent / "proposals"
    worker = args.approve or args.reject
    if worker:
        draft = proposals / f"{worker}-constraints"
        if not (draft / "lessons.json").exists():
            raise ValueError(f"no proposal for {worker!r}; run: lessons --propose")
        reviewed = json.loads((draft / "lessons.json").read_text())
        if args.approve:
            target = args.skills / draft.name / "SKILL.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(draft / "SKILL.md", target)
        store.log(LESSON_RUN, None, "reviewed",
                  {"worker": worker, "lessons": reviewed, "approved": bool(args.approve)})
        shutil.rmtree(draft)
        return {"worker": worker, "approved": bool(args.approve), "lessons": reviewed}

    done = {(d["worker"], lesson) for _, _, kind, d in store.events(LESSON_RUN)
            if kind == "reviewed" for lesson in d["lessons"]}
    pending = {}
    for w, counts in store.lesson_counts().items():
        if left := {lesson: n for lesson, n in counts.items() if (w, lesson) not in done}:
            pending[w] = left
    if args.propose:
        for w, counts in pending.items():
            picked = [lesson for lesson, n in counts.items() if n >= args.min_count]
            if not picked:
                continue
            draft = proposals / f"{w}-constraints"
            draft.mkdir(parents=True, exist_ok=True)
            current = args.skills / draft.name / "SKILL.md"
            head = current.read_text().rstrip() if current.exists() else SKILL_TEMPLATE.format(worker=w)
            head = re.sub(r"\n*<!-- agentflow:review.*?-->", "", head, flags=re.S)
            bullets = "\n".join(f"- {lesson} <!-- fixed in {counts[lesson]} task(s) -->" for lesson in picked)
            (draft / "SKILL.md").write_text(f"{head}\n\n{REVIEW_NOTE.format(worker=w)}\n{bullets}\n")
            (draft / "lessons.json").write_text(json.dumps(picked))
            print(f"agentflow: proposed {draft / 'SKILL.md'}", file=sys.stderr)
    return pending


def plan(objective, constraints, meta=None, opts=None):
    rows = json.loads(claude("planner", {"objective": objective, "constraints": constraints}, meta, None,
                             *((opts.effort, opts.max_output_tokens) if opts else ())))
    return [
        Task(row["id"], row["role"], spec={"brief": row["brief"], "contains": row["contains"]},
             deps=row["depends_on"], checks=["contains"],
             requires_approval=row.get("risk") == "irreversible")
        for row in rows
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=".workflow/runs.db")
    parser.add_argument("--jobs", default=4, type=int)
    parser.add_argument("--skills", default=ROOT / ".claude" / "skills", type=Path)
    parser.add_argument("--effort", default="medium", choices=("low", "medium", "high", "xhigh", "max"),
                        help="Claude effort; a task's spec.effort overrides it")
    parser.add_argument("--max-output-tokens", default=8000, type=int,
                        help="per-call output cap; a call that hits it fails and is retried")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "resume", "status"):
        sub = commands.add_parser(name)
        sub.add_argument("run_id")
        if name == "run":
            source = sub.add_mutually_exclusive_group(required=True)
            source.add_argument("--objective")
            source.add_argument("--plan")
            sub.add_argument("--constraints-from", type=Path)
    review = commands.add_parser("lessons", help="list, propose, approve or reject learned constraints")
    action = review.add_mutually_exclusive_group()
    action.add_argument("--propose", action="store_true")
    action.add_argument("--approve", metavar="WORKER")
    action.add_argument("--reject", metavar="WORKER")
    review.add_argument("--min-count", default=2, type=int, help="tasks a lesson must recur in to be proposed")
    args = parser.parse_args()
    try:
        database = Path(args.db)
        database.parent.mkdir(parents=True, exist_ok=True)
        store = Store(str(database))
        if args.command == "lessons":
            print(json.dumps(review_lessons(args, store), indent=2))
            return 0
        workers = dict.fromkeys(ROLES, partial(work, args))
        checks = {"contains": contains, "command": command}
        engine = Orchestrator(workers, checks, store=store, concurrency=args.jobs)
        if args.command == "status":
            state = store.load(args.run_id)
            if not state:
                raise ValueError(f"unknown run {args.run_id!r}")
        else:
            tasks = None
            if args.command == "run":
                if store.load(args.run_id):
                    raise ValueError("Run already exists. Use resume or select another ID.")
                constraints = json.loads(args.constraints_from.read_text()) if args.constraints_from else []
                if not isinstance(constraints, list) or not all(isinstance(item, str) for item in constraints):
                    raise ValueError("Constraints must be a JSON array of strings")
                if args.plan:
                    tasks = prepare(load_plan(args.plan), args.plan)
                else:
                    # Learning edge: approved skills also reach the splitter, so they shape how work is cut.
                    constraints += [f"For {d.name.removesuffix('-constraints')} tasks:\n{body}"
                                    for d in sorted(args.skills.glob("*-constraints"))
                                    if (body := skill_body(d / "SKILL.md"))]
                    meta = {}
                    try:
                        tasks = plan(args.objective, constraints, meta, args)
                    finally:
                        store.log(args.run_id, None, "plan", {"meta": meta})
                validate(tasks, workers, checks)
            state = asyncio.run(engine.run(args.run_id, tasks, new=args.command == "run"))
        print(json.dumps({tid: {key: row[key] for key in ("status", "attempts", "output", "feedback")}
                          for tid, row in state.items()}, indent=2))
        calls, cost, timeouts = usage(store, args.run_id)
        killed = f" ({timeouts} timed out, cost unknown)" if timeouts else ""
        print(f"agentflow: {calls} Claude calls{killed}, ${cost:.4f} reported cost", file=sys.stderr)
        return int(args.command != "status" and any(row["status"] != DONE for row in state.values()))
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"agentflow: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
