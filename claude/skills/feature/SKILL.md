---
name: feature
description: Build a feature or fix in an existing codebase end to end, with little back-and-forth. Orchestrates the researcher, test-writer and reviewer subagents. Plan in plan mode with an explicit list of decisions, failing tests first, implement until they pass, independent review, then report with proposed CLAUDE.md lessons. Use when the user types /feature, or asks for a complete, well-researched implementation of a non-trivial change.
argument-hint: <what to build or fix>
---

# /feature

Task: $ARGUMENTS

Corrections are cheap in a plan and expensive in code, so every question comes up before any edit. For a small task, keep the plan short, but never skip the approval or the tests.

You are the orchestrator: delegate to the `researcher`, `test-writer` and `reviewer` subagents (use `Explore` or `general-purpose` if one isn't installed). A subagent knows only its brief, so give each one a self-contained brief: the goal, the relevant files, and what to return. Check what they return against files and test output; don't trust a summary.

## 1. Plan (plan mode)

Enter plan mode unless you're already in it. Read `CLAUDE.md`, then launch `researcher` subagents in parallel, in one message, each with one narrow question: where the change belongs, the most similar existing code to reuse, the conventions that apply, and the exact commands to run the relevant tests and the build or lint. Verify anything a decision rests on by reading the code yourself.

The plan must contain:

- **Goal:** one sentence, plus what's out of scope.
- **Design and files:** the approach, the code it reuses, and each file to change, with why.
- **Decisions:** every choice the user might have made differently, with the alternatives and why this one won.
- **Assumptions and questions:** what you couldn't confirm, and what only the user can decide. Ask; don't guess.
- **Done means:** the exact commands that must pass, and the test cases to add (inputs and expected behaviour, including edge cases and failure paths).

Present it for approval. Apply every correction before going on.

## 2. Tests first

Give the `test-writer` the agreed test cases, the test conventions and the test command. It writes the tests and runs them. Confirm from its output that they fail for the expected reason, not an import or setup error.

## 3. Implement

- Make the smallest change that satisfies the plan, until every "done means" command passes.
- Never weaken, skip or edit the agreed tests to make them pass. If a test is wrong, stop and say why.
- If the same failure survives three different fixes, stop: the plan is probably wrong. Report what you learned.
- Work outside the plan (a refactor, an extra fix, a new dependency) goes in the report, not the code.

## 4. Review

Give the `reviewer` the approved plan, the test command, and the instruction to read `git diff`. Don't send your reasoning, so it isn't anchored on your conclusions. For a large or risky change, also run the `code-review` skill. Check each finding yourself, fix the real ones, rerun the commands, and note any finding you rejected and why.

## 5. Report

- **Changed:** each file, briefly.
- **Verified:** the commands run and their result lines.
- **Departures from the plan,** open risks, and follow-ups not done.
- **Lessons:** for each correction the user made that's likely to come up again, propose one line for `CLAUDE.md`. Add it only if the user agrees.
