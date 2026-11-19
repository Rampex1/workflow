---
name: feature
description: Build a feature or fix in an existing codebase end to end, with little back-and-forth. Research with subagents, get the plan approved, write failing tests, implement until they pass, have a fresh subagent review the diff, then report. Use when the user types /feature, or asks for a complete, well-researched implementation of a non-trivial change.
argument-hint: <what to build or fix>
---

# /feature

Task: $ARGUMENTS

Work in the phases below, in order. Corrections are cheap in the plan and expensive in code, so all the important questions come up in phase 2, and nothing after it should surprise the user. Scale down for small tasks (skip the subagents, keep the plan to a few lines), but never skip the stop after phase 2 or the tests.

## 1. Research (parallel subagents)

Read `CLAUDE.md` and any contributing docs first. Then launch Explore subagents **in one message**, each with one narrow question and a request for file paths plus short excerpts, not file dumps. Typical questions:

- Where does this change belong? Which files, modules and entry points are involved?
- How does the codebase already do the most similar thing? (Reuse it rather than inventing something new.)
- What conventions apply: naming, error handling, logging, configuration, dependency injection?
- How are tests written and run here? Find the exact command for the narrowest relevant test run, and for the full build or lint.

Verify anything the decisions will rest on by reading the code yourself. Don't trust a summary for it.

## 2. Plan, then STOP

Present the plan in this shape:

- **Goal:** one sentence, plus what's explicitly out of scope.
- **Design:** the approach, and which existing code it reuses.
- **Files:** each file to change or add, with one line on why.
- **Decisions:** every choice the user might have made differently, each with the alternatives and why this one won.
- **Assumptions:** things you believe but couldn't confirm.
- **Questions:** anything only the user can decide. Ask; don't guess.
- **Done means:** the exact commands that must pass, and the test cases you'll add (inputs and expected behaviour, including edge cases and failure paths).

Then **stop and wait for approval**. Apply every correction the user makes before continuing. If they changed a decision, update the plan and show it again.

## 3. Tests first

Write the agreed test cases following the codebase's test conventions. Run them and confirm they fail **for the expected reason** (missing behaviour, not an import or setup error).

## 4. Implement

- Make the smallest change that satisfies the plan. Follow the conventions found in phase 1.
- Run the "done means" commands after each meaningful step, until all of them pass.
- Never weaken, skip or edit the agreed tests to make them pass. If a test is wrong, stop and say why.
- If the same failure survives three different fixes, stop: the plan is probably wrong. Report what you learned and propose a change to the plan.
- Anything outside the approved plan (a refactor, an extra fix, a new dependency) gets noted for the report, not done.

## 5. Independent review (fresh subagent)

Spawn a general-purpose subagent with only: the approved plan, the diff (`git diff`), and the test command. **Not your reasoning**, so it isn't anchored on your conclusions. Ask it to find:

- bugs, missed edge cases and error paths;
- places where the diff departs from the plan;
- convention violations compared with nearby code;
- behaviour the tests don't cover.

Check each finding yourself. Fix the real ones, rerun the commands, and say which findings you rejected and why.

## 6. Report

- **Changed:** files and a short description of each change.
- **Verified:** the commands you ran and their results (paste the summary lines).
- **Departures from the plan,** and why.
- **Open risks** and follow-ups you didn't do.
- **Lessons:** for every correction the user made during this task that is likely to come up again, propose one line for `CLAUDE.md` (for example "New endpoints need an integration test"). Add them only if the user agrees.
