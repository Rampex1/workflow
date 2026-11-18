"""End-to-end demo: parallel fetch -> buggy summary corrected by verifier feedback -> gated publish.

Workers are deterministic stand-ins for LLM agents so the demo is free and reproducible.
Run:  python3 examples/demo.py
"""
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agentflow import Orchestrator, Store, Task  # noqa: E402


async def fetch(ctx):
    await asyncio.sleep(0.2)  # pretend I/O; both fetches overlap
    return {"sales": [120, 80, 100], "costs": [50, 40, 60]}[ctx.task.spec["table"]]


def summarize(ctx):
    sales, costs = sum(ctx.inputs["fetch_sales"]), sum(ctx.inputs["fetch_costs"])
    if not ctx.feedback:  # first attempt makes the classic "LLM" mistakes
        return {"revenue": sales, "profit": sales + costs}
    return {"revenue": sales, "cost": costs, "profit": sales - costs}


def publish(ctx):
    return f"published report: profit={ctx.inputs['summarize']['profit']}"


def has_keys(task, out):
    missing = [k for k in task.spec["required_keys"] if k not in out]
    return f"missing keys {missing}" if missing else None


def profit_consistent(task, out):
    if out.get("profit") != out.get("revenue", 0) - out.get("cost", 0):
        return f"profit {out.get('profit')} != revenue - cost"


def approve(task):
    print(f"  [human] approving {task.id!r}")
    return True


PLAN = [
    Task("fetch_sales", "fetch", {"table": "sales"}),
    Task("fetch_costs", "fetch", {"table": "costs"}),
    Task("summarize", "summarize", {"required_keys": ["revenue", "cost", "profit"]},
         deps=["fetch_sales", "fetch_costs"], checks=["has_keys", "profit_consistent"]),
    Task("publish", "publish", deps=["summarize"], requires_approval=True),
]

if __name__ == "__main__":
    store = Store(os.path.join(tempfile.mkdtemp(), "demo.db"))
    orch = Orchestrator(
        workers={"fetch": fetch, "summarize": summarize, "publish": publish},
        checks={"has_keys": has_keys, "profit_consistent": profit_consistent},
        store=store, approver=approve)
    state = asyncio.run(orch.run("demo", PLAN))

    t0 = store.events("demo")[0][0]
    print("\nEvent log:")
    for ts, task, kind, data in store.events("demo"):
        print(f"  +{ts - t0:5.2f}s  {task or '-':12} {kind:9} {data if data is not None else ''}")
    print("\nFinal state:")
    for tid, s in state.items():
        print(f"  {tid:12} {s['status']:8} attempts={s['attempts']}  output={s['output']}")
