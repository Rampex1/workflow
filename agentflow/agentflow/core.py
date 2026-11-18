"""agentflow engine: plan validation, SQLite state, async DAG orchestrator.

Stdlib only. Workers and checks are plain Python callables registered by name,
so a plan is pure data (JSON) and a run can be resumed from the database alone.
"""
from __future__ import annotations

import asyncio
import inspect
import fcntl
import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from dataclasses import asdict, dataclass, field
from graphlib import CycleError, TopologicalSorter
from typing import Any, Callable

PENDING, RUNNING, DONE, FAILED, SKIPPED, REJECTED = (
    "pending", "running", "done", "failed", "skipped", "rejected")
BLOCKING = {FAILED, SKIPPED, REJECTED}  # a dep in one of these skips its dependents


@dataclass
class Task:
    id: str
    worker: str                                       # name in the worker registry
    spec: dict = field(default_factory=dict)          # instructions / params for worker and checks
    deps: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)   # names in the check registry
    requires_approval: bool = False                   # human gate before the worker runs
    timeout: float | None = None                      # seconds per attempt


@dataclass
class Context:
    task: Task
    inputs: dict[str, Any]   # outputs of dependencies, keyed by task id
    feedback: list[str]      # verifier errors from earlier attempts of THIS task
    lessons: list[str]       # errors this worker type hit (and later fixed) in past tasks
    attempt: int             # 1-based
    meta: dict = field(default_factory=dict)  # worker-reported usage (e.g. cost_usd); logged with the attempt


Worker = Callable[[Context], Any]            # sync or async; return JSON-serializable output
Check = Callable[[Task, Any], "str | None"]  # None = pass, str = reason it failed
Approver = Callable[[Task], bool]


class PlanError(ValueError):
    pass


def validate(tasks: list[Task], workers: dict, checks: dict) -> None:
    ids = [t.id for t in tasks]
    if len(ids) != len(set(ids)):
        raise PlanError("duplicate task ids")
    for t in tasks:
        if t.worker not in workers:
            raise PlanError(f"{t.id}: unknown worker {t.worker!r}")
        for c in t.checks:
            if c not in checks:
                raise PlanError(f"{t.id}: unknown check {c!r}")
        for d in t.deps:
            if d not in ids:
                raise PlanError(f"{t.id}: unknown dependency {d!r}")
    try:
        TopologicalSorter({t.id: t.deps for t in tasks}).prepare()
    except CycleError as e:
        raise PlanError(f"dependency cycle: {e.args[1]}") from None


def load_plan(path: str) -> list[Task]:
    with open(path) as f:
        return [Task(**d) for d in json.load(f)["tasks"]]


def cli_approver(task: Task) -> bool:
    return input(f"Approve {task.id!r} ({task.worker}) {task.spec}? [y/N] ").strip().lower() == "y"


class Store:
    """One row per task per run (current state) + append-only event log."""

    def __init__(self, path: str = ":memory:"):
        self.active_runs = set()
        self.db = sqlite3.connect(path, isolation_level=None)  # autocommit: every write is durable
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks(
                run TEXT, id TEXT, def TEXT, status TEXT, attempts INT,
                output TEXT, feedback TEXT, PRIMARY KEY(run, id));
            CREATE TABLE IF NOT EXISTS events(run TEXT, ts REAL, task TEXT, kind TEXT, data TEXT);
        """)

    @contextmanager
    def lock_run(self, run: str):
        if run in self.active_runs:
            raise PlanError(f"run {run!r} is already active")
        self.active_runs.add(run)
        try:
            database = self.db.execute("PRAGMA database_list").fetchone()[2]
            if not database:
                yield
                return
            digest = hashlib.sha256(run.encode()).hexdigest()
            lock_path = Path(f"{Path(database).resolve()}.{digest}.lock")
            with lock_path.open("a") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise PlanError(f"run {run!r} is already active") from None
                yield
        finally:
            self.active_runs.remove(run)

    def init(self, run: str, tasks: list[Task]) -> None:
        for t in tasks:
            self.db.execute("INSERT OR IGNORE INTO tasks VALUES(?,?,?,?,0,NULL,'[]')",
                            (run, t.id, json.dumps(asdict(t)), PENDING))
        for tid, row in self.load(run).items():
            if row["status"] == RUNNING:
                gated = row["task"].requires_approval
                message = "Interrupted attempt. Reconcile external state before rerunning." if gated else "Interrupted attempt."
                self.save(run, tid, status=FAILED if gated else PENDING,
                          feedback=[*row["feedback"], message])

    def load(self, run: str) -> dict[str, dict]:
        rows = self.db.execute(
            "SELECT id, def, status, attempts, output, feedback FROM tasks WHERE run=?", (run,))
        return {tid: {"task": Task(**json.loads(d)), "status": st, "attempts": n,
                      "output": json.loads(o) if o is not None else None, "feedback": json.loads(fb)}
                for tid, d, st, n, o, fb in rows}

    def save(self, run: str, tid: str, **kw) -> None:
        for k in ("output", "feedback"):
            if k in kw:
                kw[k] = json.dumps(kw[k])
        cols = ", ".join(f"{k}=?" for k in kw)
        self.db.execute(f"UPDATE tasks SET {cols} WHERE run=? AND id=?", (*kw.values(), run, tid))

    def log(self, run: str, task: str | None, kind: str, data: Any = None) -> None:
        self.db.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                        (run, time.time(), task, kind, json.dumps(data)))

    def events(self, run: str) -> list[tuple]:
        return [(ts, t, k, json.loads(d)) for ts, t, k, d in self.db.execute(
            "SELECT ts, task, kind, data FROM events WHERE run=? ORDER BY rowid", (run,))]

    def lesson_counts(self) -> dict[str, dict[str, int]]:
        """{worker: {lesson: tasks that failed on it, then passed}}, newest first.

        A lesson is the first line of a check message (checks put their summary there).
        """
        # ponytail: exact-match grouping; fuzzy clustering if near-duplicates pile up.
        out: dict[str, dict[str, int]] = {}
        for (d,) in self.db.execute("SELECT data FROM events WHERE kind='lesson' ORDER BY rowid DESC"):
            data = json.loads(d)
            counts = out.setdefault(data["worker"], {})
            for line in dict.fromkeys(e.split("\n", 1)[0][:300] for e in data["errors"]):
                counts[line] = counts.get(line, 0) + 1
        return out

    def lessons(self, worker: str, limit: int = 20) -> list[str]:
        return list(self.lesson_counts().get(worker, {}))[:limit]


class Orchestrator:
    def __init__(self, workers: dict[str, Worker], checks: dict[str, Check] | None = None,
                 store: Store | None = None, approver: Approver | None = None,
                 max_corrections: int = 3, concurrency: int = 4):
        if concurrency < 1 or max_corrections < 0:
            raise ValueError("concurrency must be positive and max_corrections nonnegative")
        self.workers, self.checks = workers, checks or {}
        self.store = store or Store()
        self.approver = approver or (lambda t: False)  # deny by default: unattended runs never act irreversibly
        self.max_corrections, self.concurrency = max_corrections, concurrency

    async def run(self, run_id: str, tasks: list[Task] | None = None, *, new: bool = False) -> dict[str, dict]:
        """Start a run (tasks given) or resume one (tasks omitted). Returns final per-task state."""
        with self.store.lock_run(run_id):
            if new and self.store.load(run_id):
                raise PlanError("Run already exists. Use resume or select another ID.")
            return await self._run(run_id, tasks)

    async def _run(self, run_id: str, tasks: list[Task] | None) -> dict[str, dict]:
        if tasks is not None:
            validate(tasks, self.workers, self.checks)
            self.store.init(run_id, tasks)
        else:
            self.store.init(run_id, [])
        state = self.store.load(run_id)
        if not state:
            raise PlanError(f"unknown run {run_id!r}")
        validate([s["task"] for s in state.values()], self.workers, self.checks)
        order = list(TopologicalSorter({k: s["task"].deps for k, s in state.items()}).static_order())
        sem = asyncio.Semaphore(self.concurrency)
        running: dict[str, asyncio.Task] = {}
        self.store.log(run_id, None, "run_start")

        try:
            while True:
                for tid in order:  # topological order => skips propagate transitively in one pass
                    s = state[tid]
                    if s["status"] != PENDING or tid in running:
                        continue
                    dep_status = [state[d]["status"] for d in s["task"].deps]
                    if any(d in BLOCKING for d in dep_status):
                        s["status"] = SKIPPED
                        self.store.save(run_id, tid, status=SKIPPED)
                        self.store.log(run_id, tid, "skipped")
                    elif all(d == DONE for d in dep_status):
                        running[tid] = asyncio.create_task(self._execute(run_id, state, tid, sem))
                if not running:
                    break
                finished, _ = await asyncio.wait(running.values(), return_when=asyncio.FIRST_COMPLETED)
                for tid in [k for k, v in running.items() if v in finished]:
                    running.pop(tid).result()  # re-raise engine bugs instead of hanging

        finally:
            for job in running.values():
                job.cancel()
            await asyncio.gather(*running.values(), return_exceptions=True)

        self.store.log(run_id, None, "run_end", {k: s["status"] for k, s in state.items()})
        return state

    async def _execute(self, run: str, state: dict, tid: str, sem: asyncio.Semaphore) -> None:
        s, t = state[tid], state[tid]["task"]

        def update(**kw):
            s.update(kw)
            self.store.save(run, tid, **kw)

        async with sem:
            update(status=RUNNING)
            inputs = {d: state[d]["output"] for d in t.deps}
            lessons = self.store.lessons(t.worker)
            while s["attempts"] <= self.max_corrections:  # 1 initial attempt + max_corrections retries
                n = s["attempts"] + 1
                if t.requires_approval:
                    ok = await self._call_sync(self.approver, t, None)
                    self.store.log(run, tid, "approval", ok)
                    if not ok:
                        return update(status=REJECTED)
                update(attempts=n)
                ctx = Context(t, inputs, list(s["feedback"]), lessons, n)
                try:
                    out = await self._call(self.workers[t.worker], ctx, t.timeout)
                except Exception as e:  # crash or timeout is just a failed attempt
                    out, errors = None, [f"worker error: {type(e).__name__}: {e}"]
                else:
                    errors = self._verify(t, out)
                self.store.log(run, tid, "attempt", {"n": n, "errors": errors, **({"meta": ctx.meta} if ctx.meta else {})})
                if not errors:
                    # Lessons are check failures only; crashes/timeouts/interruptions are infra, not constraints.
                    learned = [e for e in s["feedback"] if not e.startswith(("worker error:", "Interrupted attempt"))]
                    if learned:
                        self.store.log(run, tid, "lesson", {"worker": t.worker, "errors": learned})
                    return update(status=DONE, attempts=n, output=out)
                update(attempts=n, feedback=s["feedback"] + errors)
            update(status=FAILED)

    async def _call(self, fn: Worker, ctx: Context, timeout: float | None) -> Any:
        if inspect.iscoroutinefunction(fn):
            return await asyncio.wait_for(fn(ctx), timeout)
        return await self._call_sync(fn, ctx, timeout)

    @staticmethod
    async def _call_sync(fn, argument, timeout):
        # Hold the slot until the thread actually stops, including on cancellation.
        job = asyncio.create_task(asyncio.to_thread(fn, argument))
        try:
            return await asyncio.wait_for(asyncio.shield(job), timeout)
        except (TimeoutError, asyncio.CancelledError):
            await asyncio.gather(asyncio.shield(job), return_exceptions=True)
            raise

    def _verify(self, t: Task, out: Any) -> list[str]:
        try:
            json.dumps(out)
        except (TypeError, ValueError) as e:
            return [f"output not JSON-serializable: {e}"]
        errors = []
        for name in t.checks:
            try:
                msg = self.checks[name](t, out)
            except Exception as e:
                msg = f"check raised {type(e).__name__}: {e}"
            if msg:
                errors.append(f"{name}: {msg}")
        return errors
