# ClipReach

**Your AI agent picks the moments. Your computer makes the clips.**

ClipReach is an open-source skill for turning long videos into captioned vertical clips without a separate clipping-platform subscription. Give a capable AI agent a video, and it uses the transcript to select moments, then renders the files with local tools.

This is an independent project inspired by the video-repurposing workflow of services such as ScaleReach. It does not use their code, assets, accounts, or private APIs.

## What it does

- Takes a local video or downloads a supported video URL with yt-dlp.
- Transcribes speech locally with faster-whisper, or reuses an existing timestamped transcript.
- Lets your existing agent choose complete moments and explain its editorial choices.
- Renders 9:16 MP4s with captions, including word highlights when word timing is available.
- Preserves the full frame or uses an adjustable static crop.
- Outputs actual video files, caption files, and a JSON manifest. No watermark is added.

There is no required paid model API and no ClipReach subscription. Your host AI agent may have its own cost; rendering uses your hardware and transcription takes time. Model weights download on first use. This is a local editing workflow, not a cloud video-processing service.

## Install as a plugin, extension, or skill

**[Installation instructions for all supported agents](INSTALL.md)** — Codex and Claude Code plugins, a Gemini CLI extension, and native skills for OpenCode and Antigravity.

Give your agent this repository link and say:

> Install ClipReach for this agent using INSTALL.md, then clip this video: VIDEO_URL

The agent can handle installation and first-run setup when its permissions allow it. It still needs command execution, FFmpeg, and permission to download processing dependencies. Chat-only assistants cannot run these local tools just by reading a link.

For Codex:

```sh
codex plugin marketplace add https://github.com/aarushkwagh-blip/clipreach.git
codex plugin add clipreach@clipreach
```

For Claude Code:

```sh
claude plugin marketplace add aarushkwagh-blip/clipreach
claude plugin install clipreach@clipreach
```

For Gemini CLI:

```sh
gemini extensions install https://github.com/aarushkwagh-blip/clipreach
```

For OpenCode or Antigravity, clone this repository and run `python3 install.py --agent opencode` or `python3 install.py --agent antigravity`.

Download **[the plugin ZIP](https://github.com/aarushkwagh-blip/clipreach/releases/latest/download/clipreach-plugin.zip)** for the complete installable package, or **[the skill ZIP](https://github.com/aarushkwagh-blip/clipreach/releases/latest/download/clipreach.zip)** for a standalone skill folder. The packages share one clipping engine. These are GitHub distributions, not claims of acceptance into any official plugin store.

After installation, select the skill/plugin and ask:

> Use ClipReach to turn this video into three captioned vertical clips. Set up missing local dependencies with my permission, then give me the MP4s.

## Install processing tools once

Use Python 3.10+ and an FFmpeg build with libass, libx264, and AAC support. The installed skill's `scripts/setup.py --install` creates an isolated Python environment and prints the interpreter to use. See [setup instructions](INSTALL.md#processing-runtime).

For development from a checkout, a project venv also works:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python skills/clipreach/scripts/clipreach.py doctor
```

## The actual workflow

```sh
# Or start with your own local source.mp4 and skip downloading.
.venv/bin/python skills/clipreach/scripts/clipreach.py download \
  'https://your-authorized-video-link' --out work/source

.venv/bin/python skills/clipreach/scripts/clipreach.py transcribe \
  work/source/source.mp4 --out work/transcript.json

# The AI reads the transcript and writes work/plan.json.
# See skills/clipreach/references/formats.md for both JSON formats.

.venv/bin/python skills/clipreach/scripts/clipreach.py render \
  work/source/source.mp4 --transcript work/transcript.json \
  --plan work/plan.json --out output/clips
```

Clip selection is performed by your agent; `render` does not call an AI service or guess which moments are interesting. `examples/plan.json` illustrates the format, not real selections for your video.

The default render is 1080×1920. `--width 360` makes a smaller preview. Existing output paths are refused. Local videos and transcripts are not committed to this repository. Only use media you have permission to download and edit; some sites require additional downloader setup or reject downloads. No login or DRM bypass is provided.

## Current limits

This first version focuses on speech-driven clips. It does not include dynamic face tracking, B-roll generation, silence removal, social scheduling, or a measured virality score. Caption accuracy depends on the transcript, and editorial quality depends on the host agent. A static crop can miss a moving speaker; the default full-frame layout avoids cutting people out. Unusual scripts may require appropriate system fonts for caption rendering.

The scripts perform transcription and rendering locally after downloading source media and model weights. Your host agent's own privacy policy still applies when it reads your transcript.

## Verify

```sh
python3 -m unittest discover -s tests -v
```

Tests cover timestamp validation, captions, agent installation, runtime setup checks, and distributable packages. FFmpeg integration tests generate their own synthetic media and check actual video output; they skip if the required tools are unavailable. They do not download third-party videos or speech models.

Primary dependencies: [FFmpeg](https://ffmpeg.org/), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and [yt-dlp](https://github.com/yt-dlp/yt-dlp). Each has its own license and installation requirements.
