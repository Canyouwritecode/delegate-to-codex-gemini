# Delegate to Codex and Gemini

Two Claude Code skills that split the work between three agents, to save Claude usage:

- **Claude** plans the work and reviews the result.
- **Codex** writes the code.
- **Gemini** reads and reviews, without changing anything.

| Skill | Use it for | Runs |
|---|---|---|
| [`delegate-to-codex`](skills/delegate-to-codex/SKILL.md) | Well-specified building work: features, refactors, tests, migrations | `codex exec`, in a workspace-write sandbox |
| [`delegate-to-gemini`](skills/delegate-to-gemini/SKILL.md) | Read-only work: code reviews, summaries of large codebases, finding usages | `agy`, in plan mode with a sandbox |

The skills are not for architecture, unclear requirements, or debugging that needs judgment. Those stay with Claude.

Saw the animated office on [@pluggedwith.ai](https://www.instagram.com/pluggedwith.ai/) on Instagram? That's a separate repo. For the whole setup, install these skills first, then [agent-board-animated](https://github.com/Canyouwritecode/agent-board-animated).

## What you need

- [Claude Code](https://claude.com/claude-code)
- The Codex CLI, signed in, for `delegate-to-codex`
- The Antigravity CLI (`agy`), signed in, for `delegate-to-gemini`
- Python 3, for `run-gemini.py`, the Gemini runner
- A git repository with at least one commit, so every change can be reviewed as a diff

Each skill works without the other, but they are better together: `delegate-to-codex` asks for a Gemini review when it finishes.

## Install

Copy the two skill folders into your Claude Code skills folder.

macOS, Linux or Git Bash:

```
git clone https://github.com/Canyouwritecode/delegate-to-codex-gemini.git
cp -r delegate-to-codex-gemini/skills/* ~/.claude/skills/
```

Windows PowerShell:

```
git clone https://github.com/Canyouwritecode/delegate-to-codex-gemini.git
Copy-Item -Recurse delegate-to-codex-gemini\skills\* $HOME\.claude\skills\
```

Start a new Claude Code session afterwards.

## Use

Ask in plain words, or call a skill by name:

```
Delegate the CSV export to Codex, then have Gemini review it.
/delegate-to-gemini Summarise how authentication works in this repo
```

## How a job runs

1. Claude writes a brief that stands on its own, because the other agent sees none of your conversation.
2. The brief goes into `.codex-tasks/` or `.agent-tasks/`. Both folders stay out of git through `.git/info/exclude`, so they never show up in your diff.
3. The agent runs in the background and writes a log and a result file next to the brief. Gemini runs through `run-gemini.py`, which streams every step to a file and stops a run that has gone silent. It defaults to low effort, because higher effort stalled on long reviews. Low effort finishes reliably but makes more mistakes, so every finding gets checked.
4. Claude checks the work itself: it reads the diff, reruns the tests and verifies each review finding. A reported "passed" counts as unverified.
5. If something is wrong, Codex gets at most two fix rounds. After that, Claude stops and tells you.

## Watch your agents work

[Agent board animated](https://github.com/Canyouwritecode/agent-board-animated) is a separate Claude Code mod that shows these jobs as a small animated office. Running jobs sit at desks, idle agents wait in the coffee room, and every 10 finished jobs earn a pizza.

![The last job finishes, the office gets a pizza break, and the countdown resets](https://raw.githubusercontent.com/Canyouwritecode/agent-board-animated/main/media/pizza-break.gif)

The office only draws in the VS Code extension. In a terminal you get a text list instead.

It reads the same `.codex-tasks/` and `.agent-tasks/` folders, so it needs no setup with these skills:

```
claude plugin marketplace add https://github.com/Canyouwritecode/agent-board-animated.git
claude plugin install agent-board-animated@agent-board-animated
```

## Keeping private files private

Each brief lists paths the agent must never open, and `.env*` files are always on that list. Add your own project's rules when Claude writes a brief. Gemini's sandbox and plan mode enforce read-only use, but path rules in a brief are instructions, not a hard barrier, so keep real secrets out of the project folder.

## Licence

MIT. See [LICENSE](LICENSE).
