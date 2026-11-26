---
name: feature
description: Build a feature, fix or design milestone in an existing codebase end to end, with little back-and-forth. Orchestrates a crew of subagents chosen for the task. Plan in plan mode with an explicit list of decisions, failing tests first, implement until they pass, independent review, then report with proposed CLAUDE.md lessons.
disable-model-invocation: true
argument-hint: <what to build or fix>
hooks:
  Stop:
    - hooks:
        - type: command
          command: '"$HOME/.claude/skills/feature/stop-gate.sh"'
          timeout: 600
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

Enter plan mode unless you're already in it. Read `CLAUDE.md`, everything in `context/` at the repo root (requirement docs and notes the user dropped there; it isn't committed), and the relevant parts of `research/` (earlier findings, decisions and the design doc), then launch the `researcher` agents in parallel, in one message, each with one narrow question: where the change belongs, the most similar existing code to reuse, every caller or consumer of the code you'll change (so a fix lands where all of them route through), the conventions that apply, and the exact commands to run the relevant tests and the build or lint. Verify anything a decision rests on by reading the code yourself.

The plan must contain:

- **Crew:** the agents you'll use after approval, and why each one is needed.
- **Goal:** one sentence, plus what's out of scope.
- **Design and files:** the approach, the code it reuses, and each file to change, with why.
- **Decisions:** every choice the user might have made differently, with the alternatives and why this one won.
- **Assumptions and questions:** what you couldn't confirm, and what only the user can decide. Ask; don't guess.
- **Done means:** the exact commands that must pass, and the test cases to add (inputs and expected behaviour, including edge cases and failure paths).

Present it for approval. Apply every correction before going on.

## After approval: records, branch and rules

- **Records** in `research/` (local; if `git check-ignore -q research` fails, append `research/` to `.git/info/exclude`): save the final plan to `research/plans/<slug>.md`; each new finding to `research/findings/<topic>.md` (frontmatter `sources:` and `date:`, then the answer, evidence and unknowns; never overwrite an existing file, append a dated update instead); and the decisions to `research/decisions.md`.
- **Branch:** if you're on the default branch, create a local branch `feature/<slug>`. Commit after each reviewed step with a clear message. Never push.
- **Progress:** the plan has a `## Progress` section. Append one line after each step (baseline, tests written, task N done with its commit, review result). If the session was compacted or resumed, read Progress and `git log` first and trust them over your memory; never redo finished steps.
- **Keep going without check-ins.** Decide ambiguities yourself and log each in Progress as `Ruling: <what> — <why> — <cost if wrong>`. Stop and ask only when:
  1. an action is irreversible or destructive;
  2. an action is security-sensitive;
  3. an action has a side effect outside the repo (push, publish, deploy);
  4. an agreed test looks wrong (say why; never change it yourself);
  5. the same failure survives three different fixes (the plan is probably wrong; report what you learned);
  6. the plan is so broken that every way forward is a guess.

## 2. Baseline, then tests first

Run the test and build commands from the plan once before changing anything, and record the result in Progress as the baseline. Failures that were already there aren't yours to fix; note them.

Give the `test-writer` the agreed test cases, the test conventions and the test command. It writes the tests and runs them. Confirm from its output that they fail for the expected reason, not an import or setup error. Commit the tests.

## 3. Implement

**Arm the stop gate first.** Write the "done means" commands to `research/.gate` as a shell script (e.g. `npm test --silent && npm run lint`). This skill's Stop hook runs it whenever you try to finish and blocks you while it fails, so "done" means the check passes, not that you think it does. Never edit `research/.gate` to make it pass. If you must stop under the stop list, delete it and log a Ruling saying why.

- Make the smallest change that satisfies the plan, until every "done means" command passes.
- Never weaken, skip or edit the agreed tests to make them pass.
- Work outside the plan (a refactor, an extra fix, a new dependency) goes in the report, not the code.
- **Long milestone** (several separable tasks in the plan): give each task to a fresh `general-purpose` implementer, one at a time, never in parallel. Its brief holds only that task, the interfaces from earlier tasks, and the test command; it must not spawn subagents or commit. Have the `reviewer` check that task's diff, then commit it before starting the next. Run the "done means" commands yourself. For a short milestone, implement it yourself.

## 4. Review

Write the diff of the whole change against the branch point to a file (e.g. `git diff <base>... > research/plans/<slug>.diff`), and give the `reviewer` its path, the approved plan and the test command. Don't send your reasoning, and don't pre-judge: never tell it what not to flag or that "the plan chose" something. For a large or risky change, also run the `code-review` skill. Check each finding yourself, fix the real ones, rerun the commands, and commit. Never drop a finding silently: log each rejected one in Progress as a ruling.

## 5. Report

Before reporting, delete `research/.gate` and `research/.gate-blocks`, so the gate doesn't block the rest of the session.

- **Branch and commits:** the branch name and its commits (not pushed).
- **Changed:** each file, briefly.
- **Verified:** the commands run and their result lines, against the baseline.
- **Departures from the plan,** open risks, and follow-ups not done.
- **Rulings:** every ruling from Progress, so the user can review and undo them.
- **Lessons:** for each correction the user made that's likely to come up again, propose one line and where it belongs: `CLAUDE.local.md` (this repo, just for the user), `~/.claude/CLAUDE.md` (all repos), or the team's `CLAUDE.md` (only for a team convention). Add it only if the user agrees.
