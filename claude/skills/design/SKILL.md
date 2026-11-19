---
name: design
description: Turn a project's requirements into an end-to-end design doc after in-depth research and adversarial review, ending with milestones sized for /feature. Orchestrates a crew of subagents chosen for the project.
disable-model-invocation: true
argument-hint: <project description, or paths to the requirement docs>
---

# /design

Project: $ARGUMENTS

You are the orchestrator. The deliverable is a design doc that the user and their mentor can approve with few changes, and a milestone list they can implement one `/feature` run at a time. Corrections are cheapest before the doc is written, so all questions and key decisions come up first.

A subagent knows only its brief, so give each one a self-contained brief: the goal, the relevant files or links, and what to return. Check what they return against the sources; don't trust a summary.

**Keep a record in `research/`** at the repo root. It stays local: if `git check-ignore -q research` fails, append `research/` to `.git/info/exclude`.

```
research/
  findings/<topic>.md   # one per research question
  decisions.md          # every key decision
  design/<slug>.md      # the design doc
```

Subagents can't write there, so you save each finding after checking it. Each findings file starts with frontmatter listing its `sources:` (`path:line` or URL), then the answer, the evidence and the unknowns. Read any existing `research/` first, and reuse findings that are still true instead of researching again.

## 1. Requirements and questions

Gather context before writing anything, even when a requirements doc was given:

- everything in `context/` at the repo root (requirement docs, notes, emails, specs dropped there by the user; it isn't committed), plus any files passed as arguments;
- `CLAUDE.md` and any existing design docs;
- the codebase itself: launch `researcher` agents in parallel to map the code the project touches (entry points, similar features, how config, auth, deploys and tests work).

Then present:

- **Requirements,** numbered (R1, R2, …): functional, non-functional (performance, scale, security, cost), and constraints. Mark each one as stated (cite the file in `context/` or the user's words) or inferred (cite the code it's inferred from).
- **Non-goals:** what this project won't do.
- **Questions** only the user or their mentor can answer. Don't ask anything the code or `context/` already answers; ask the rest now, don't guess.

Stop until the user answers. Update the requirements with their answers.

## 2. Crew and research

Choose the crew this project needs and say why. Typical members:

- `researcher` agents, one narrow question each: where the project fits in the existing codebase, the most similar existing systems or patterns to reuse, conventions and platform constraints, and outside options (libraries, services, approaches) with tradeoffs.
- Specialists as general-purpose agents with a role brief, only when a requirement calls for one: for example security, data modelling, performance or migration.

Skip roles that add nothing. Launch the independent agents in parallel, in one message. Verify any finding a decision will rest on by reading the source yourself, then save each one to `research/findings/<topic>.md`.

## 3. Key decisions, then STOP

For each decision that shapes the design, give two or three options with tradeoffs (complexity, risk, cost, fit with existing code), your recommendation, and which requirements it serves. Stop and get the user's choices before writing the doc. Append each decision to `research/decisions.md`: the options, the choice, who approved it, the date, and the findings it rests on.

## 4. Write the doc

Write it to `research/design/<slug>.md`, citing the `research/findings/` files it draws on. Sections:

1. **Context and problem:** why this project exists.
2. **Goals and non-goals.**
3. **Requirements:** the numbered list from step 1.
4. **Current state:** the relevant existing system, with `path:line` citations.
5. **Proposed design:** components, data model, APIs or interfaces, the main flows (a Mermaid diagram where it helps), error handling, security and observability.
6. **Alternatives considered,** and why each lost.
7. **Risks and mitigations.**
8. **Testing and rollout:** how each part will be verified, and how it ships safely.
9. **Milestones:** small, ordered, each one implementable in a single `/feature` run, with its requirements and a "done means" (the tests or checks that prove it).
10. **Open questions.**

Cite every claim about the codebase (`path:line`) and every outside fact (URL). Mark anything you couldn't confirm as unverified.

## 5. Check and review

- **Traceability:** every requirement maps to a part of the design and to a milestone. List any gaps and fix them.
- **Adversarial review:** give the doc and the requirements (not your reasoning) to one or two reviewers with different lenses, for example `reviewer` for feasibility and correctness, and a general-purpose agent for requirements coverage and clarity to a new reader. Ask for findings by severity. Fix the real ones. If blockers remain after two rounds, report them instead of looping.

## 6. Report

- The doc's path, and a five-line summary.
- Decisions that need the mentor's sign-off.
- Open questions and risks.
- The milestones as ready-to-run commands: `/feature <milestone>, per research/design/<slug>.md`.
