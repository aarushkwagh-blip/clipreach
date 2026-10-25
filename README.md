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

## Install the skill

[Download the skill ZIP](https://github.com/aarushkwagh-blip/clipreach/releases/latest/download/clipreach.zip), or use the source folder below. Extract it into your agent's skills directory; an attachment alone still needs an environment that can execute the scripts.

The portable skill is [`skills/clipreach`](skills/clipreach). It contains the instructions and Python script together. Copy that entire folder, not just `SKILL.md`.

For Codex, put it in `~/.codex/skills/clipreach`. For Claude Code, put it in `~/.claude/skills/clipreach` or your project's `.claude/skills/clipreach`. Other agents can read `SKILL.md` and use the script if they support shell commands and local files. Merely attaching the Markdown file to a chat-only AI will not give it video-processing capability.

Clone the repository first:

```sh
git clone https://github.com/aarushkwagh-blip/clipreach.git
cd clipreach
```

From that checkout:

```sh
# Codex (use a new destination; don't replace an existing skill accidentally)
mkdir -p ~/.codex/skills
cp -R skills/clipreach ~/.codex/skills/
```

Restart or reload your agent's skills, then ask:

> Use ClipReach to turn this video into three 30–60 second clips with captions. Choose moments that work on their own, and save the MP4s locally.

## Install processing tools once

Use Python 3.10+ and an FFmpeg build with libass, libx264, and AAC support.

```sh
# macOS
brew install ffmpeg
# Ubuntu/Debian (instead of Homebrew)
# sudo apt-get update && sudo apt-get install ffmpeg python3-venv

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python skills/clipreach/scripts/clipreach.py doctor
```

On Windows, install FFmpeg from a trusted distribution, add its `bin` directory to PATH, and use `.venv\Scripts\python.exe` instead of `.venv/bin/python`. The script uses argument arrays, not shell command strings.

Rendering with an existing transcript only needs Python and FFmpeg; both Python packages are optional. A copied skill can install its optional packages with `python -m pip install 'av<19' faster-whisper yt-dlp` in the environment used by the agent.

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

Unit tests cover timestamp validation and caption generation. FFmpeg integration tests generate their own synthetic media and check actual video output; they skip if the required tools are unavailable. They do not download third-party videos or speech models.

Primary dependencies: [FFmpeg](https://ffmpeg.org/), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and [yt-dlp](https://github.com/yt-dlp/yt-dlp). Each has its own license and installation requirements.
