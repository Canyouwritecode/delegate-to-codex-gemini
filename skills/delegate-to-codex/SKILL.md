---
name: delegate-to-codex
description: Delegate a well-specified implementation task (feature, refactor, tests, boilerplate, migration) to the Codex CLI to save Claude usage, then review the result. Use when the plan is clear and the work is mostly typing code. Not for architecture, ambiguous requirements or debugging that needs judgment.
allowed-tools: Read Write Bash(git *) Bash(codex exec *) Bash(mkdir *) Bash(grep *) Bash(echo *)
---

# Delegate to Codex

You plan and review. Codex implements.

## 1. Prepare
- Check the git state with `git status`. If this is not a git repo, or the repo has no commits yet (`git rev-parse HEAD` fails), stop and ask the user. Codex's changes can only be reviewed as a diff against a commit.
- If there are uncommitted changes, ask the user whether to commit or stash first, so Codex's changes show up as a clean diff. If that would block ongoing work, save `git status`, `git diff` and file hashes instead, and compare them after the run.
- Create `.codex-tasks/` if it doesn't exist and keep it out of git: if it is not already in `.git/info/exclude`, append it (`echo ".codex-tasks/" >> .git/info/exclude`). This is local-only, so it never adds a `.gitignore` change to the diff.
- If you are resuming after a break, check earlier result and log files first. A background run can be cut off when a session ends, so don't assume it succeeded.

## 2. Write the brief
For matching or reconciliation logic, first dry-run the planned rule on real data yourself (counts only if the data is private). It shows what the plan missed before anyone builds it.

Keep briefs small: large ones come back with tests missing and placeholders invented. Split a big task into separate briefs. Two briefs that touch different files can run at the same time.

Write `.codex-tasks/<task-name>.md` with your file tool, not a shell heredoc, because quotes in the text can break the command. Start the run only after the write has succeeded.

Codex sees nothing from this conversation and does not read CLAUDE.md (it reads AGENTS.md if there is one), so the brief must stand on its own:
- Goal (1-3 sentences)
- Files to create or change, with paths
- Files and areas it must NOT touch
- Paths it must never open: copy the project's secrets rules word for word, if it has any (for example "Never open `secrets/` or `*.pdf`."). Always include `.env*` files.
- Constraints: libraries, patterns, style rules, and the project's domain rules that matter for this task. Restate them; don't just point to a file.
- The exact interface, and for rule-based code the exact patterns and the order rules run in.
- Every test written out, with expected values you computed yourself. State that each listed test must exist. Include:
  - behaviour for invalid input (Codex rarely adds validation on its own);
  - at least one messy real-world case per function;
  - for code that builds database rows or API payloads, one test that sends them to the real system (local database, real schema);
  - for logic that pairs or matches rows, a test that shuffles the input and expects the same result. Tie-breaks on input order pass fixed-order tests, then change once rows come from a database.
- The exact test or build command to run, and the instruction to run it before finishing. If the project has no test setup yet, make setting it up part of the task (or a separate first task) instead of skipping tests. On Windows, use `npm.cmd`, not `npm`, because the PowerShell execution policy can block `npm.ps1`.
- If the code or tests will contain non-ASCII text (accented letters, currency or math symbols, typographic quotes, special spaces): "Source files must be pure ASCII, with no BOM; write non-ASCII characters as escapes (e.g. `\u00e9`)." Codex has silently corrupted literal non-ASCII into U+FFFD in both code and tests, so the tests still passed.
- If the task installs packages: tell it not to put a package-manager cache inside the repo, and run that one task with `-c sandbox_workspace_write.network_access=true` (the sandbox blocks network by default).
- "If a test runner or service can't start in your sandbox, say so; do not work around it."
- "If two instructions in this brief conflict, report it instead of picking one."
- If the task pins a package version, choose one at least two weeks old. Some tools refuse newer ones, and that policy should not be bypassed.
- For a refactor: commit first, tell Codex never to delete or restore files, and have it work in small checked edits. A failed run can otherwise lose uncommitted work; `~/.codex/sessions` holds whatever Codex read, which can help recovery.
- If the test runner can't start in the sandbox, give it a plain script it can run there, such as a Node script importing the file directly.
- "Do not commit."
- "End with a short summary: files changed, tests run, results, open issues."

After writing the brief, confirm that escapes survived: some file tools turn an escape into the real character, and Codex then copies that. Before sending, check every example and rule in the brief against each other, against the existing tests, and against the project's stated principles. Codex follows a wrong rule faithfully.

## 3. Run Codex
Run it in the background (Bash tool, `run_in_background: true`), because it can take several minutes. Send its progress log to a file so it doesn't fill your context:

    codex exec --sandbox workspace-write -o .codex-tasks/<task-name>.result.md - < .codex-tasks/<task-name>.md 2> .codex-tasks/<task-name>.log

When it finishes, get the session id so the fix round resumes this exact session (not whatever Codex session ran last on this machine):

    grep -m1 -i "session id" .codex-tasks/<task-name>.log

Read only `<task-name>.result.md`. Open the rest of the `.log` file only if the run failed or the result is empty.

When Codex runs in another folder, such as a worktree or scratch folder, keep the brief, log and result in the project's `.codex-tasks/`, using full paths, so that any tool watching that folder still sees the run.

## 4. Review
Inspect:
- Run `git status` and `git diff --stat`, then read the diff for the changed files. Check for new untracked files too.
- Check every acceptance criterion and every do-not-touch rule. Check that every listed test exists; the size of the test file is a quick hint.
- Scan new and changed files for U+FFFD (`grep -rl $'\xef\xbf\xbd' <paths>`) and for stray caches or build artefacts (package-manager caches, compiler build info) that don't belong in git.
- When the brief asked for pure ASCII, scan for any non-ASCII byte or BOM (`LC_ALL=C grep -l '[^[:print:][:space:]]' <paths>`). The U+FFFD scan misses both.

Run:
- Run the test command yourself, outside the sandbox, and don't trust Codex's report alone. Inside the sandbox some tools fail or need workarounds. Database and service tests usually run only on your side, so plan time for that.
- Treat a reported "passed" as unverified, even for checks Codex says it ran.
- An automatic gate must check the job's own acceptance cases, not only existing tests, and treat "I got stuck" as a failure. After two tool failures on one file, change the builder: a Claude agent can edit reliably and run the real suite.
- For privacy or security rules, read the tests themselves. Each case should name the exact secret, not just check that the input changed. Keep the output of an adversarial probe run as a baseline for later changes.
- For a server function or anything with runtime limits, also run it on the real runtime, repeatedly and from a cold start, and test each limit at its maximum. Use a local stand-in for a paid API. Count only rounds where the test setup itself worked.
- If a test that existed before now fails, the brief may be what's wrong. Check that before asking Codex to change the code.
- When "test fails first" matters, run the new tests against the old code (for example with `git stash`), because Codex often can't observe that step.

Probe:
- Ask of each important test: would it fail if the rule broke? Prove it for the key rules by breaking the code on purpose, running the tests, and restoring the code.
- Try messy cases with a throwaway test: reversed ranges, negatives, empty input, periods that don't line up with calendar months.
- For tasks that handle data, finish with an end-to-end run on real or realistic data through the real storage layer, locally, with cleanup. If the data is private, print counts only. Treat a small unexplained difference between runs as a bug until it is explained.
- For access-control code, attack the seams between rules: anything a policy trusts must itself be protected. Run the attack before and after the fix.
- For screens, run the real app in a browser and look at screenshots. Tests don't see layout problems.

## 5. Fix round (at most 2)
If something is wrong, send Codex a short, numbered, specific correction (also in the background). `resume` has no `--sandbox` flag, so set the sandbox through config. Put the correction in a file, and give each round its own result file, because `-o` overwrites:

    codex exec resume <session-id> -c sandbox_mode="workspace-write" -o .codex-tasks/<task-name>.fix1.result.md - < .codex-tasks/<task-name>.fix1.md 2>> .codex-tasks/<task-name>.log

Use `--last` instead of `<session-id>` only if you couldn't find the id. Then repeat step 4, including the broad tests, because a fix can break another case. If it is still wrong after two rounds, stop and report to the user instead of looping.

## 6. Second opinion
If the delegate-to-gemini skill is available, run a small read-only review of the finished code as a default step, beside the next task if that saves time. Verify each finding yourself.

## 7. Report
Tell the user what Codex did, what you checked, the test results, and anything you would still change. Do not commit unless the user asks.
