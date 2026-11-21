---
name: onboarding
description: Onboard the user onto a repository they don't know. Builds a short, cited onboarding doc with Archify diagrams of the area they'll work on, verifies the setup by running it, then quizzes them on it, tracking misses for later review. Use /onboarding [area] to build, /onboarding quiz to be quizzed.
disable-model-invocation: true
argument-hint: [area you'll work on] | quiz
---

# /onboarding

Request: $ARGUMENTS

The goal is that the user understands the part of this repo they'll work on, fast. The doc is short enough to read in one sitting; the quiz makes it stick. Every claim about the code cites `path:line`; mark anything you couldn't confirm as unverified.

Everything goes in `research/` at the repo root, which stays local: if `git check-ignore -q research` fails, append `research/` to `.git/info/exclude`. Never edit the repo's code.

If the request is `quiz`, skip to **Quiz**. Otherwise build the doc.

## 1. Scope

Read `CLAUDE.md`, `context/`, the README and any existing `research/onboarding/`. If the request doesn't name an area and the repo is more than one small service, ask one question: what will the user work on? Onboard that area and how it connects to the rest, not the whole repo.

If `research/onboarding/<repo>.md` already exists, update it instead: re-check only what changed since the commit stamped in it (`git diff <commit>..HEAD --stat`).

## 2. Map

If `graphify-out/graph.json` exists, query it first (`graphify query`, `path`, `explain`) and pass what you learn into the briefs below. Don't build a graph yourself; for a large repo, suggest the user run `/graphify` once.

Launch `researcher` agents in parallel, in one message, one narrow question each, scoped to the area:

- entry points and the 1–2 most important flows, traced end to end;
- the data model (tables, schemas, key types);
- how to build, run, test and debug locally (exact commands);
- config, environments and deployment;
- conventions the code follows (structure, naming, error handling, testing style);
- ownership: `CODEOWNERS`, and the most-changed files (`git log --format= --name-only | sort | uniq -c | sort -rn | head`, which you run yourself, since researchers have no shell).

Check what they return against the code before using it. Save each finding to `research/findings/<topic>.md` (frontmatter `sources:` and `date:`; never overwrite, append a dated update), so `/design` and `/feature` can reuse them.

## 3. Prove the setup

Run the build and test commands. Record what worked, what failed and how you fixed it (missing env vars, services to start, slow tests). If something can't be run locally, say so. A setup section that hasn't been run is marked unverified.

## 4. Diagrams

With the `archify` skill, draw from the code (repository-backed): one architecture diagram of the area and its neighbours, and one sequence diagram for each key flow. Save each as `research/onboarding/<repo>-diagrams/<name>.html`, then export a PNG: run `node ~/.claude/skills/archify/bin/archify.mjs visual-check <name>.html --summary --out-dir <tmp>`, copy its `2048x1320.light.png` capture to `<name>.png` beside the HTML, and delete `<tmp>`. If `archify` isn't installed or the export fails, use Mermaid instead.

## 5. Write the doc

Write `research/onboarding/<repo>.md`. Two pages at most: cut anything the user could look up when they need it. Start with `Built at <commit> on <date>`. Sections:

1. **What it is:** one paragraph, then the architecture diagram: `![Architecture](<repo>-diagrams/architecture.png)` and `[Interactive version](<repo>-diagrams/architecture.html)`.
2. **Reading order:** about 10 files to read, in order, one line each on why.
3. **Key flows:** each as numbered steps with `path:line`, plus its sequence diagram.
4. **Where changes go:** "To add X, edit Y" for the 3–5 most common changes.
5. **Run, test, debug:** the commands from step 3, and the gotchas you hit.
6. **Conventions:** the few rules a reviewer would flag.
7. **Glossary:** domain terms and abbreviations, one line each.
8. **Who to ask:** owners per part, from step 2.
9. **Questions for your mentor:** what you couldn't work out from the code.
10. **Try it:** three small hands-on exercises, e.g. run one test alone, add a log line and see it in the output, set a breakpoint in a key flow.

Then report the doc's path and offer the first quiz.

## Quiz

Read `research/onboarding/<repo>.md` and `research/onboarding/quiz-log.md` (create it if missing). Ask five questions, **one at a time**, waiting for each answer. Start with questions the user missed before that are due again, then fill with new ones, mixing:

- **recall:** "Where is auth checked?"
- **trace:** "A request hits `/upload`. Which files does it pass through, in order?"
- **predict:** "What happens if Redis is down?" Have the user guess first, then check the code together.
- **locate:** "Where would you add a new field to the user profile?"

Ground every question in the code, not just the doc. After each answer, grade it (right, partly right or wrong), show the correct answer with `path:line`, and add one line of why it matters. Don't give hints before the user answers.

After the five, append each question to `quiz-log.md` with the date, the result and when it's next due: wrong → next quiz, partly right → in 3 days, right → in 10 days, right a second time in a row → retired. End with the score and the one topic to reread.
