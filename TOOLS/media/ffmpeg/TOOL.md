# FFmpeg

- **ID:** `ffmpeg`
- **Category:** media
- **Status:** `tested`
- **Publisher / maintainer:** FFmpeg Project
- **Official website:** https://ffmpeg.org/
- **Source repository:** https://github.com/FFmpeg/FFmpeg
- **Documentation:** https://ffmpeg.org/documentation.html
- **License:** LGPL-2.1-or-later by default; optional GPL components change the applicable license to GPL-2.0-or-later. Check the exact build configuration and bundled libraries.
- **Platforms:** Linux, Windows, macOS and other supported systems
- **Version reviewed:** upstream FFmpeg 9.1 (released 2026-11-20); current isolated runtime has FFmpeg 7.1.5
- **Last reviewed:** 2026-11-26

## What it does

FFmpeg is a multimedia framework and collection of command-line tools for decoding, encoding, transcoding, muxing, demuxing, filtering, streaming, and inspecting audio/video media. The main commands are:

- `ffmpeg` — convert and process media.
- `ffprobe` — inspect container and stream metadata.
- `ffplay` — play media for testing and preview.

The available codecs, formats, filters, hardware acceleration, and licensing obligations depend on how the binary was built.

## When an AI agent should use it

Use FFmpeg for:
- converting between audio/video containers and codecs;
- resizing, cropping, trimming, concatenating, and filtering media;
- extracting audio or individual frames;
- generating preview clips, thumbnails, and optimized web video;
- probing file duration, dimensions, codecs, frame rates, and stream metadata.

Use `ffprobe` before conversion when the input format, streams, duration, or codec parameters are unknown.

## Requirements and costs

- Runtime: native FFmpeg binaries; no Python or Node.js runtime is required for CLI use.
- Account or API key: not required.
- Cost: open source; local execution has no per-conversion fee. Compute, storage, and CI infrastructure may have costs.
- Network: not required for local files; required to install packages or access remote media sources.
- Permissions: reads input files and writes output files. Some protocols can access network resources, so restrict protocol access when processing untrusted input.

## Installation

Prefer the operating system's package manager or a trusted build that documents its codec and license configuration.

Debian / Ubuntu:

```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

Verify the installation:

```bash
ffmpeg -version
ffprobe -version
ffmpeg -buildconf
```

The upstream download page describes official source releases and links to platform-specific builds:

https://ffmpeg.org/download.html

## Basic usage

Inspect a media file:

```bash
ffprobe -v error -show_format -show_streams input.mp4
```

Convert to H.264 video and AAC audio in MP4 (only if the selected build includes the required encoders):

```bash
ffmpeg -i input.mov -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k output.mp4
```

Extract audio:

```bash
ffmpeg -i input.mp4 -vn -c:a libmp3lame -q:a 2 output.mp3
```

## Verification

- **Local runtime inspected:** Debian GNU/Linux 13, Linux x86_64; FFmpeg and ffprobe 7.1.5 were available in PATH.
- **Local smoke test:** generated a one-second MP4 with synthetic video and audio, inspected both streams with ffprobe, and decoded the file to a null output. All steps passed.
- **Build configuration:** the inspected binary was built with `--enable-gpl`; treat that binary as GPL-licensed and review the bundled libraries' notices before redistribution.
- **CI environment:** GitHub-hosted Ubuntu 26.04 runner; FFmpeg and ffprobe 8.0.1-3ubuntu2.
- **CI installation:** installed successfully from the Ubuntu package repository.
- **CI runtime test:** generated a one-second MP4 with synthetic video and audio; ffprobe confirmed video dimensions 160×90 and audio sample rate 44,100 Hz; FFmpeg decoded the file successfully.
- **Result:** encode, probe, and decode smoke test passed. Run: https://github.com/HOADF-Team/AI-Toolbox/actions/runs/45836085028
- **Build configuration:** the CI binary includes `--enable-gpl`; treat that binary as GPL-licensed and review bundled library notices before redistribution.
- **Scope:** CI verified only the tested Linux package and codecs. The current assistant runtime's FFmpeg 7.1.5 also passed a separate local encode/probe/decode test. Neither result implies installation on the user's computer.

## Security and limitations

- Keep FFmpeg updated. Media parsers process complex, often attacker-controlled binary formats; use a patched build.
- Treat input media, playlists, manifests, subtitles, and metadata as untrusted.
- Run conversion of untrusted files in a restricted process/container with limited filesystem and network access.
- Do not allow arbitrary remote protocols or playlists unless the workflow explicitly requires them.
- Codec availability is build-dependent. A command using `libx264`, `libmp3lame`, or a hardware encoder will fail if that encoder is not present.
- FFmpeg is not a substitute for a media editor's timeline, compositing, or project-file workflow.
- Review the build's configuration and third-party license notices. Enabling GPL components changes the applicable FFmpeg license from LGPL to GPL.

## Sources

- Official download page and current releases: https://ffmpeg.org/download.html
- Official documentation: https://ffmpeg.org/documentation.html
- Official license explanation: https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md
- Source repository: https://github.com/FFmpeg/FFmpeg
