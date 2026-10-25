# Install ClipReach into your agent

Give your command-capable agent this repository link and the following request:

> Install ClipReach from https://github.com/aarushkwagh-blip/clipreach into this agent. Read INSTALL.md and use the native plugin/extension installation if supported, otherwise the portable skill installer. Follow this environment's installation approvals. Then use ClipReach to make three captioned clips from: VIDEO_URL

For the installing agent:

1. Clone the repository into a persistent user-approved directory, or use the native install command below. Read the package before executing it.
2. Install for the current agent, not every agent on the machine. Never change permissions or disable sandbox protections to make installation work.
3. Reload skills or ask the user to restart the host if necessary. Do not claim a skill was discovered until the host reports it.
4. Read `skills/clipreach/SKILL.md` and run its `scripts/setup.py`. If missing, install FFmpeg through the host-approved system package manager and run setup with `--install` to create its isolated Python environment. Keep the returned interpreter path for the clipping workflow.
5. With a local file or authorized supported video URL, follow the skill through actual MP4 delivery. Do not stop after returning a plan when the user asked for clips.

## Native installs

### Codex plugin

```sh
codex plugin marketplace add https://github.com/aarushkwagh-blip/clipreach.git
codex plugin add clipreach@clipreach
```

Select ClipReach in the host's plugin picker after installation/reload. The repository includes a Codex marketplace and portable plugin manifest. A GitHub marketplace install is separate from a listing in OpenAI's public directory.

### Claude Code plugin

```sh
claude plugin marketplace add aarushkwagh-blip/clipreach
claude plugin install clipreach@clipreach
```

Then invoke `/clipreach:clipreach` with the video URL, or ask Claude to use ClipReach. The same marketplace/install commands are available under `/plugin` inside an interactive Claude Code session.

### Gemini CLI extension

```sh
gemini extensions install https://github.com/aarushkwagh-blip/clipreach
```

The extension exposes the bundled skill. Reload Gemini CLI and ask it to use ClipReach. An existing installation can update with `gemini extensions update clipreach`.

### OpenCode and Antigravity

After cloning the repository, use the portable installer:

```sh
python3 install.py --agent opencode
# Or:
python3 install.py --agent antigravity
```

Then reload the host and ask it to use ClipReach. These are native discoverable skills, not fabricated JavaScript plugin adapters. Current Antigravity uses `.agents/skills` per workspace and `.gemini/config/skills` globally; older IDE builds may require their documented legacy skill directory instead.

## Portable installation for every supported agent

From a full checkout or the extracted plugin ZIP:

```sh
python3 install.py --agent codex
python3 install.py --agent claude-code
python3 install.py --agent gemini
python3 install.py --agent opencode
python3 install.py --agent antigravity
```

Pick one command. Add `--scope project --project /path/to/project` to install for one workspace instead of your user account. `--dry-run` shows destinations without writing. `--agent all` deliberately installs for all supported hosts. Existing different skills are never overwritten; back up or rename an older installation before replacing it. Native plugin managers should handle their own updates.

| Agent | User skill directory | Project skill directory |
| --- | --- | --- |
| Codex / generic Agent Skills | `~/.agents/skills/clipreach` | `.agents/skills/clipreach` |
| Claude Code | `~/.claude/skills/clipreach` | `.claude/skills/clipreach` |
| Gemini CLI | `~/.gemini/skills/clipreach` | `.gemini/skills/clipreach` |
| OpenCode | `~/.config/opencode/skills/clipreach` | `.opencode/skills/clipreach` |
| Antigravity (current) | `~/.gemini/config/skills/clipreach` | `.agents/skills/clipreach` |

The installer changes only the selected skill folder. It does not alter global prompts, tool permissions, account settings, or model settings.

## Processing runtime

The skill includes its own setup helper and requirements, including in both ZIP downloads:

```sh
python3 skills/clipreach/scripts/setup.py
# If the runtime is missing, after approving the dependency download:
python3 skills/clipreach/scripts/setup.py --install
```

This creates `~/.local/share/clipreach/venv` and installs the Python dependencies there. It returns a JSON object containing the interpreter and clipping-script paths. On Windows it returns the environment's `Scripts/python.exe` path. To use a different writable runtime location, pass `--runtime /path/to/venv` to setup on every call.

FFmpeg must be installed separately with libass and libx264. Package installation and video/model downloads require network access. The model's first download happens at transcription time. The agent's sandbox must allow the source files and output directory. Setup does not bypass those constraints.

## Compatibility evidence

Packaging and installer tests cover all named agents' destination paths, repeat installation, refusal to overwrite user edits, and clean ZIP contents. Claude Code's native manifest validator is also used during development. End-to-end agent discovery has not been tested in every product/version. Follow the host's actual tool output if its interface has changed.

Official installation formats: [Codex plugins](https://developers.openai.com/plugins/build/plugins), [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude Code plugins](https://code.claude.com/docs/en/plugins-reference), [Gemini CLI extensions](https://geminicli.com/docs/extensions/reference/), [OpenCode skills](https://opencode.ai/docs/skills/), [Antigravity skills](https://antigravity.google/docs/skills).
