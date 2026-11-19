---
name: feature
description: Build a feature, fix or design milestone in an existing codebase end to end, with little back-and-forth. Orchestrates a crew of subagents chosen for the task. Plan in plan mode with an explicit list of decisions, failing tests first, implement until they pass, independent review, then report with proposed CLAUDE.md lessons.
disable-model-invocation: true
argument-hint: <what to build or fix>
---

# /feature

Task: $ARGUMENTS

Corrections are cheap in a plan and expensive in code, so every question comes up before any edit. For a small task, keep the plan short, but never skip the approval or the tests.

**Scope first.** If the task is a whole project (several milestones, and no design doc yet), stop and suggest `/design` instead. If a design doc exists, read it and implement only the milestone asked for.

You are the orchestrator. Choose the crew this task needs:

- `researcher` agents for the questions the plan depends on;
- `test-writer` for the tests;
- `reviewer` for the review;
- specialists as general-purpose agents with a role brief, only when the task calls for one, for example a security reviewer for auth code, or a migration checker for schema changes.

Skip roles that add nothing; a docs-only change needs no `test-writer`. If one of the named subagents isn't installed, use `Explore` or `general-purpose` with the same brief. A subagent knows only its brief, so make each brief self-contained: the goal, the relevant files, and what to return. Check what they return against files and test output; don't trust a summary.

## 1. Plan (plan mode)

Enter plan mode unless you're already in it. Read `CLAUDE.md`, everything in `context/` at the repo root (requirement docs and notes the user dropped there; it isn't committed), and the relevant parts of `research/` (earlier findings, decisions and the design doc), then launch the `researcher` agents in parallel, in one message, each with one narrow question: where the change belongs, the most similar existing code to reuse, the conventions that apply, and the exact commands to run the relevant tests and the build or lint. Verify anything a decision rests on by reading the code yourself.

The plan must contain:

- **Crew:** the agents you'll use after approval, and why each one is needed.
- **Goal:** one sentence, plus what's out of scope.
- **Design and files:** the approach, the code it reuses, and each file to change, with why.
- **Decisions:** every choice the user might have made differently, with the alternatives and why this one won.
- **Assumptions and questions:** what you couldn't confirm, and what only the user can decide. Ask; don't guess.
- **Done means:** the exact commands that must pass, and the test cases to add (inputs and expected behaviour, including edge cases and failure paths).

Present it for approval. Apply every correction before going on.

Once approved, keep a record in `research/` (local; if `git check-ignore -q research` fails, append `research/` to `.git/info/exclude`): save the final plan to `research/plans/<slug>.md`, each new research finding to `research/findings/<topic>.md` (frontmatter `sources:`, then the answer, evidence and unknowns), and the decisions to `research/decisions.md`.

**From here on, keep going without check-ins.** The plan has a `## Progress` section: append one line after each step (tests written and failing as expected; task N done, with its commit or files; review round result). If the session was compacted or resumed, read it and `git log` first, and trust them over your memory; never redo finished steps. Decide ambiguities yourself and log each in Progress as `Ruling: <what> — <why> — <cost if wrong>`. Stop and ask only for something irreversible or destructive, something security-sensitive, a side effect outside the repo (push, publish, deploy), or a plan so broken that every way forward is a guess.

## 2. Tests first

Give the `test-writer` the agreed test cases, the test conventions and the test command. It writes the tests and runs them. Confirm from its output that they fail for the expected reason, not an import or setup error.

## 3. Implement

- Make the smallest change that satisfies the plan, until every "done means" command passes.
- Never weaken, skip or edit the agreed tests to make them pass. If a test is wrong, stop and say why.
- If the same failure survives three different fixes, stop: the plan is probably wrong. Report what you learned.
- Work outside the plan (a refactor, an extra fix, a new dependency) goes in the report, not the code.
- **Long milestone** (several separable tasks in the plan): give each task to a fresh `general-purpose` implementer, one at a time, never in parallel. Its brief holds only that task, the interfaces from earlier tasks, and the test command; it must not spawn subagents. Have the `reviewer` check each task before starting the next, and run the "done means" commands yourself. For a short milestone, implement it yourself.

## 4. Review

Write `git diff` for the whole change to a file (e.g. `research/plans/<slug>.diff`), and give the `reviewer` its path, the approved plan and the test command. Don't send your reasoning, and don't pre-judge: never tell it what not to flag or that "the plan chose" something. For a large or risky change, also run the `code-review` skill. Check each finding yourself, fix the real ones, and rerun the commands. Never drop a finding silently: log each rejected one in Progress as a ruling.

## 5. Report

- **Changed:** each file, briefly.
- **Verified:** the commands run and their result lines.
- **Departures from the plan,** open risks, and follow-ups not done.
- **Rulings:** every ruling from Progress, so the user can review and undo them.
- **Lessons:** for each correction the user made that's likely to come up again, propose one line for `CLAUDE.md`. Add it only if the user agrees.
