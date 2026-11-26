# ImageMagick

- **ID:** `imagemagick`
- **Category:** image-tools
- **Status:** `tested`
- **Publisher / maintainer:** ImageMagick Studio LLC and contributors
- **Official website:** https://imagemagick.org/
- **Source repository:** https://github.com/ImageMagick/ImageMagick
- **Documentation:** https://imagemagick.org/
- **License:** ImageMagick License (custom permissive license; attribution and license-copy requirements apply to redistribution)
- **Platforms:** Linux, macOS, Windows
- **Version observed in test environment:** 7.1.2-1 Q16-HDRI
- **Last reviewed:** 2026-11-26

## What it does

ImageMagick is a command-line image processing suite and library. It can create, resize, crop, compose, annotate, inspect, and convert images across many formats. Its main command in version 7 is `magick`; `identify` inspects image properties.

## When an AI agent should use it

Use ImageMagick for repeatable image operations, batch conversion, thumbnails, resizing, compositing, format normalization, and image metadata inspection. It is a useful command-line complement to Pillow for Python workflows and GIMP for manual pixel-level editing.

Use explicit input and output paths, specify output formats, and inspect results. For tasks requiring layered editing or detailed manual retouching, use a full graphics editor instead.

## Requirements and costs

- Runtime / dependencies: native ImageMagick executable; optional format support depends on delegates and libraries installed in the build.
- Account required: no.
- API key or token required: no.
- Paid features or usage costs: free software; no per-image fee.
- Network access: not required for local image operations. Some coders or delegates may support remote resources; disable these when not needed.
- Permissions: reads input files and writes output files; may use substantial memory, CPU, and disk cache.

## Installation

Use the official [download page](https://imagemagick.org/download/) or a supported package manager. Verify with `magick -version` and inspect available formats using `magick identify -list format`.

On macOS, the official site documents Homebrew installation; Windows installers and Linux binaries are also provided. For Linux, distribution packages may be older than the upstream release.

Uninstall through the same package manager or installer used for installation.

## Basic usage

```bash
magick input.jpg -resize 1200x800\> output.jpg
magick input.png -strip output.png
magick identify -format '%m %wx%h\n' output.png
magick montage image1.png image2.png -tile 2x -geometry 320x240+8+8 contact-sheet.png
```

The `-strip` option removes profiles and metadata; preserve a copy of the original if metadata may be needed.

## Verification

- **Environment:** Linux x86_64, current isolated execution container.
- **Date:** 2026-11-26.
- **Version:** 7.1.2-1 Q16-HDRI.
- **Checks performed:** generated a PNG image, resized it from 160×100 to 80×50, and inspected both files with `magick identify`.
- **Result:** image creation, resizing, and identification smoke test passed.
- **Installation tested:** no; ImageMagick was pre-existing.
- **Not tested:** JPEG/WebP/AVIF delegates, animated images, color profiles, RAW formats, SVG/PDF coders, large batch workloads, Windows/macOS builds.

## Security and limitations

ImageMagick's security model is permissive unless restricted by its policy. Before processing untrusted uploads or running on a public server, review `policy.xml`, disable unnecessary coders/delegates (especially remote and document formats), set memory/disk/time limits, and restrict file paths. Process untrusted files in a sandbox. Do not assume that a successful conversion means all embedded metadata is safe or appropriate to publish.

The ImageMagick License requires attribution and a copy of the license when redistributing ImageMagick. Do not imply endorsement by ImageMagick Studio LLC.

## Sources

- Official website and downloads: https://imagemagick.org/
- License: https://imagemagick.org/license/
- Security policy: https://imagemagick.org/security-policy/
- Supported formats: https://imagemagick.org/formats/
- Source repository: https://github.com/ImageMagick/ImageMagick
