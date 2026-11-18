import asyncio
import os
import tempfile

import pytest

from agentflow import (DONE, FAILED, REJECTED, RUNNING, SKIPPED, Orchestrator, PlanError, Store,
                       Task, validate)


def run(orch, run_id="r", tasks=None):
    return asyncio.run(orch.run(run_id, tasks))


def ok(ctx):
    return {"id": ctx.task.id, "inputs": ctx.inputs}


def boom(ctx):
    raise RuntimeError("nope")


def is_dict(t, out):
    return None if isinstance(out, dict) else "expected dict"


# --- validation -------------------------------------------------------------

@pytest.mark.parametrize("tasks, msg", [
    ([Task("a", "ok"), Task("a", "ok")], "duplicate"),
    ([Task("a", "nope")], "unknown worker"),
    ([Task("a", "ok", checks=["nope"])], "unknown check"),
    ([Task("a", "ok", deps=["x"])], "unknown dependency"),
    ([Task("a", "ok", deps=["b"]), Task("b", "ok", deps=["a"])], "cycle"),
])
def test_validation_rejects_bad_plans(tasks, msg):
    with pytest.raises(PlanError, match=msg):
        validate(tasks, {"ok": ok}, {})


# --- scheduling --------------------------------------------------------------

def test_independent_tasks_run_concurrently():
    barrier = asyncio.Barrier(3)  # deadlocks (-> timeout) unless all three run at once

    async def w(ctx):
        await asyncio.wait_for(barrier.wait(), 2)
        return ctx.task.id

    st = run(Orchestrator({"w": w}), tasks=[Task(x, "w") for x in "abc"])
    assert all(s["status"] == DONE for s in st.values())


def test_concurrency_limit_respected():
    live = peak = 0

    async def w(ctx):
        nonlocal live, peak
        live += 1
        peak = max(peak, live)
        await asyncio.sleep(0.01)
        live -= 1

    run(Orchestrator({"w": w}, concurrency=2), tasks=[Task(str(i), "w") for i in range(6)])
    assert peak == 2


def test_dependency_order_and_inputs():
    order = []

    def w(ctx):
        order.append(ctx.task.id)
        return ctx.task.id.upper()

    def join(ctx):
        return ctx.inputs

    st = run(Orchestrator({"w": w, "join": join}),
             tasks=[Task("c", "join", deps=["a", "b"]), Task("a", "w"), Task("b", "w")])
    assert st["c"]["output"] == {"a": "A", "b": "B"}
    assert set(order) == {"a", "b"}


# --- verification & correction ----------------------------------------------

def test_failed_task_gets_feedback_and_is_corrected():
    seen = []

    def w(ctx):
        seen.append(list(ctx.feedback))
        return {"v": 1} if ctx.feedback else "wrong"

    st = run(Orchestrator({"w": w}, {"is_dict": is_dict}), tasks=[Task("a", "w", checks=["is_dict"])])
    assert st["a"]["status"] == DONE and st["a"]["attempts"] == 2
    assert seen == [[], ["is_dict: expected dict"]]


def test_correction_budget_is_three():
    st = run(Orchestrator({"w": lambda c: "x"}, {"is_dict": is_dict}),
             tasks=[Task("a", "w", checks=["is_dict"])])
    assert st["a"]["status"] == FAILED and st["a"]["attempts"] == 4  # 1 + 3 corrections


def test_only_failed_task_retries_and_dependents_skip_transitively():
    calls = {}

    def w(ctx):
        calls[ctx.task.id] = calls.get(ctx.task.id, 0) + 1
        return ctx.task.id

    st = run(Orchestrator({"w": w, "boom": boom}), tasks=[
        Task("good", "w"), Task("bad", "boom"),
        Task("child", "w", deps=["bad"]), Task("grandchild", "w", deps=["child", "good"])])
    assert st["good"]["status"] == DONE and calls["good"] == 1
    assert st["bad"]["status"] == FAILED and st["bad"]["attempts"] == 4
    assert st["child"]["status"] == SKIPPED and st["grandchild"]["status"] == SKIPPED
    assert "child" not in calls


def test_worker_exception_and_timeout_count_as_attempts():
    async def slow(ctx):
        if ctx.attempt == 1:
            await asyncio.sleep(5)
        return "ok"

    st = run(Orchestrator({"slow": slow}), tasks=[Task("a", "slow", timeout=0.05)])
    assert st["a"]["status"] == DONE and st["a"]["attempts"] == 2
    assert "TimeoutError" in st["a"]["feedback"][0]


def test_check_crash_and_unserializable_output_are_failures():
    def bad_check(t, out):
        raise KeyError("k")

    st = run(Orchestrator({"w": lambda c: {1, 2}, "w2": lambda c: 1}, {"bad": bad_check},
                          max_corrections=0),
             tasks=[Task("a", "w"), Task("b", "w2", checks=["bad"])])
    assert "not JSON-serializable" in st["a"]["feedback"][0]
    assert "check raised KeyError" in st["b"]["feedback"][0]


# --- approval ------------------------------------------------------------------

def test_approval_denied_by_default_blocks_worker_and_dependents():
    calls = []
    st = run(Orchestrator({"w": lambda c: calls.append(c.task.id)}),
             tasks=[Task("deploy", "w", requires_approval=True), Task("after", "w", deps=["deploy"])])
    assert st["deploy"]["status"] == REJECTED and st["after"]["status"] == SKIPPED
    assert calls == []


def test_approval_granted_runs_task():
    asked = []
    orch = Orchestrator({"w": lambda c: 1}, approver=lambda t: asked.append(t.id) or True)
    st = run(orch, tasks=[Task("deploy", "w", requires_approval=True)])
    assert st["deploy"]["status"] == DONE and asked == ["deploy"]


# --- persistence ---------------------------------------------------------------

def test_resume_after_crash_preserves_done_outputs():
    path = os.path.join(tempfile.mkdtemp(), "state.db")
    calls = []

    def w(ctx):
        calls.append(ctx.task.id)
        return ctx.task.id

    tasks = [Task("a", "w"), Task("b", "w", deps=["a"]), Task("c", "w", deps=["b"])]
    s1 = Store(path)
    s1.init("r", tasks)
    s1.save("r", "a", status=DONE, attempts=1, output="A-from-before")
    s1.save("r", "b", status=RUNNING, attempts=1, feedback=["attempt 1 broke"])  # process died here
    s1.db.close()

    st = run(Orchestrator({"w": w}, store=Store(path)))  # resume from DB alone
    assert calls == ["b", "c"]  # a not re-run
    assert st["a"]["output"] == "A-from-before"
    assert st["b"]["attempts"] == 2  # budget carried over


def test_rerun_of_finished_run_is_noop():
    calls = []
    orch = Orchestrator({"w": lambda c: calls.append(1)})
    run(orch, tasks=[Task("a", "w")])
    run(orch, tasks=[Task("a", "w")])
    assert calls == [1]


def test_lessons_from_corrections_reach_future_tasks():
    seen = []

    def w(ctx):
        seen.append(ctx.lessons)
        return {} if ctx.feedback else "x"

    orch = Orchestrator({"w": w}, {"is_dict": is_dict})
    run(orch, "r1", [Task("a", "w", checks=["is_dict"])])
    run(orch, "r2", [Task("b", "w", checks=["is_dict"])])
    assert seen[0] == [] and seen[-1] == ["is_dict: expected dict"]


def test_unknown_run_resume_raises():
    with pytest.raises(PlanError, match="unknown run"):
        run(Orchestrator({}), "missing")


def test_sync_timeout_waits_for_thread_before_retry():
    import time

    events = []

    def worker(ctx):
        events.append(("start", ctx.attempt))
        if ctx.attempt == 1:
            time.sleep(0.06)
        events.append(("end", ctx.attempt))
        return "ok"

    state = run(Orchestrator({"w": worker}), tasks=[Task("a", "w", timeout=0.02)])
    assert state["a"]["status"] == DONE
    assert "TimeoutError" in state["a"]["feedback"][0]
    assert events == [("start", 1), ("end", 1), ("start", 2), ("end", 2)]


def test_second_store_cannot_resume_active_run(tmp_path):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def worker(ctx):
            entered.set()
            await release.wait()
            return "ok"

        path = str(tmp_path / "runs.db")
        first = Orchestrator({"w": worker}, store=Store(path))
        second = Orchestrator({"w": worker}, store=Store(path))
        job = asyncio.create_task(first.run("same", [Task("a", "w")]))
        await entered.wait()
        try:
            with pytest.raises(PlanError, match="already active"):
                await second.run("same")
        finally:
            release.set()
            assert (await job)["a"]["status"] == DONE

    asyncio.run(scenario())


def test_resume_does_not_replay_interrupted_gated_worker():
    store = Store()
    store.init("r", [Task("a", "w", requires_approval=True)])
    store.save("r", "a", status=RUNNING, attempts=1)
    calls = []
    state = run(Orchestrator({"w": lambda ctx: calls.append(ctx)}, store=store,
                             approver=lambda task: True))
    assert state["a"]["status"] == FAILED
    assert calls == []


def test_worker_meta_is_logged_with_attempt():
    def w(ctx):
        ctx.meta["cost_usd"] = 0.5
        return 1

    orch = Orchestrator({"w": w})
    run(orch, tasks=[Task("a", "w")])
    attempts = [d for _, t, k, d in orch.store.events("r") if k == "attempt"]
    assert attempts == [{"n": 1, "errors": [], "meta": {"cost_usd": 0.5}}]


def test_worker_errors_are_not_lessons():
    def w(ctx):
        if ctx.attempt == 1:
            raise TimeoutError("slow api")
        return {} if ctx.attempt == 3 else "x"

    orch = Orchestrator({"w": w}, {"is_dict": is_dict})
    run(orch, tasks=[Task("a", "w", checks=["is_dict"])])
    assert orch.store.lessons("w") == ["is_dict: expected dict"]


def test_lessons_are_first_lines_counted_per_task():
    def w(ctx):
        return {} if ctx.feedback else "x"

    def long_check(t, out):
        return None if isinstance(out, dict) else "expected dict\n" + "detail " * 500

    orch = Orchestrator({"w": w}, {"c": long_check})
    for r in ("r1", "r2"):
        run(orch, r, [Task("a", "w", checks=["c"])])
    assert orch.store.lesson_counts() == {"w": {"c: expected dict": 2}}
