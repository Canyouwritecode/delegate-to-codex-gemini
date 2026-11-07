---
name: delegate-to-gemini
description: "Delegate read-only, context-heavy work to Gemini via Antigravity CLI (agy) to save Claude usage: summarizing large codebases or docs, finding usages across many files, second-opinion code reviews. Not for edits; use delegate-to-codex for implementation."
allowed-tools: Read Write Bash(git *) Bash(agy *) Bash(mkdir *) Bash(grep *) Bash(echo *) Bash(cat *)
---

# Delegate to Gemini (read-only)

Use this as a default small review after each finished implementation task, not only at the end of a batch. It can run beside the next task. Good fits: code reviews, cross-file consistency checks, and security reviews.

## 1. Prepare
- Make sure this is a git repo with at least one commit (`git rev-parse HEAD`). If not, stop and ask the user.
- Check `git status`. If there are uncommitted changes, or your own delegated work is running, save `git status` and file hashes first, so you can tell agy's changes from everything else. Don't edit the files under review during the run.
- Keep the task folder out of git so it never shows up as a change: if `.agent-tasks/` is not already in `.git/info/exclude`, append it (`echo ".agent-tasks/" >> .git/info/exclude`). This is local-only and never committed.
- If you are resuming after a break, check earlier result and log files first. A background run can be cut off when a session ends.

## 2. Write the brief
Write a self-contained brief to `.agent-tasks/<task>.md`. Keep it small: the report is only written at the very end, so a run that dies loses everything. Split big reviews into several briefs.

Start it with: "Do not modify, create or delete any files. Only read and report. Do not run ANY shell command, not even git; use only your built-in file reading, listing and search tools. Do not use subagents. Stay inside this project folder: never read anything outside it, including your own earlier transcripts or notes."

Headless agy auto-denies commands and then gives up with no output; even `git log -n 5` was denied although `git log` was allow-listed. If the task truly needs git history, paste it into the brief.

Then add any paths it must never open, copied word for word from the project's rules if it has any (for example "Never open `secrets/` or `*.pdf`."), and always `.env*` files.

Gemini has none of this conversation's context. A brief that works well for a code review has:
- the goal, and the project rules that matter for judging the answer;
- the commit under review, and the exact files to read, with each source file's test file;
- a summary of what is defined elsewhere, because reviewing a slice blind produces false gaps;
- the intended rules, written out;
- what to look for: wrong results, a rule with no real test, edge cases;
- a concrete input for every finding. For access-control code, ask for test cases you can run, not opinions. Word it as a correctness review of your own code: words like "attacker" can trip Gemini's safety filter;
- "If you aren't sure of a calculation, say so." It can't run code, and its arithmetic can be wrong;
- one `## Final report` section at the very end, because agy writes its working notes into the output first.

## 3. Run it
Run it in the background (Bash tool, `run_in_background: true`). `--mode plan` and `--sandbox` enforce read-only instead of relying on the brief, and `--print-timeout` stops a stuck run:

    python ~/.claude/skills/delegate-to-gemini/run-gemini.py .agent-tasks/<task>.md --effort low --schema ~/.claude/skills/delegate-to-gemini/review-schema.json

The runner keeps `--mode plan --sandbox`, streams every step to `<task>.stream.jsonl`, stops a silent run after `--idle` seconds, and writes `<task>.result.md` and `<task>.status.txt`. Default to `--effort low`: on a long code review, medium and high stalled in one silent thinking step, while low finished in about 30 seconds. Low effort produces more false findings, so run every finding. Leave out `--schema` for summaries. A stopped run can continue with `--resume <conversation id>` from the status file.

Never add `--dangerously-skip-permissions`.

Model: without `--model`, agy uses its default (check the `cli.log` line "selected model override"). `agy models` lists what the account offers, and `--effort` sets reasoning effort. Use a stronger model for reviews that matter, if the user agrees: other models may use a different allowance, and a model from the same family as the planner is a less independent second opinion.

A sleeping computer kills a run, so keep it awake.

## 4. If it fails
The run failed if the result file is empty or has no `## Final report` (a safety filter returns one short line), it timed out, or the log says a permission was auto-denied. Report that, and don't retry more than once.

Check the timestamps in `~/.gemini/antigravity-cli/cli.log` first. A dropped connection or a long gap means the network or a sleeping computer, so retry the same brief. A denied command or read means the brief must change before the retry.

## 5. Check the repo
Run `git status`. If tracked files changed that you can't explain, list them, revert only those files (`git checkout -- <file> ...`), and tell the user. If agy created untracked files, list them for the user rather than deleting them.

## 6. Use the result
Read from `## Final report`. Verify every claim against the current code before relying on it, and run anything that can be run. To check a claimed test gap, break that rule on purpose and see whether a test fails. Then summarize for the user.
Its knowledge of external APIs can be out of date, so check such claims against current docs or a real run. If you ask which rules have no test, list every relevant test file, or the gaps it reports may be false.
