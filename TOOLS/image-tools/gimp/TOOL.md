# GIMP

- **ID:** `gimp`
- **Category:** image-tools
- **Status:** `reviewed`
- **Publisher / maintainer:** The GIMP Team
- **Official website:** https://www.gimp.org/
- **Source repository:** https://gitlab.gnome.org/GNOME/gimp
- **Documentation:** https://docs.gimp.org/3.0/
- **License:** GPL-3.0-or-later for GIMP; bundled plug-ins and third-party components may have separate notices
- **Platforms:** GNU/Linux, Windows, macOS
- **Version reviewed:** 3.2.8 (2026-11-02)
- **Last reviewed:** 2026-11-26

## What it does

GIMP is a raster graphics editor for retouching, compositing, working with layers and masks, and preparing images. GIMP 3 provides non-interactive batch execution through its command-line interface and batch interpreters.

## When an AI agent should use it

Use GIMP when a task requires layered raster editing, advanced retouching, compositing, masks, or an established desktop image editor. For simple resizing and format conversion, lighter command-line tools may be more efficient.

## Requirements and costs

- Runtime / dependencies: platform-specific GIMP package and its bundled libraries; Linux packages may depend on GTK and GEGL.
- Account required: no.
- API key or token required: no.
- Paid features or usage costs: no license fee.
- Network access: not required for local editing after installation.
- Permissions: reads and writes local image files; plug-ins may have additional capabilities.

## Installation

Use the official [download page](https://www.gimp.org/downloads/) and select the package for the target OS and architecture. On Linux, the official project offers AppImage, Flatpak, and Snap options; the current AppImage requirements are listed on the download page. Verify published SHA-256 checksums when provided.

Do not assume that a distribution package is the latest upstream release. Record the actual installed version and package source. Avoid third-party download sites.

## Basic usage

Interactive launch:

```bash
gimp
```

GIMP 3 supports non-interactive batch commands. The official manual documents `--batch`, `--batch-interpreter`, `--no-interface`, and `--quit`. The Script-Fu interpreter can be invoked explicitly, for example:

```bash
gimp --no-interface --batch-interpreter=plug-in-script-fu-eval \
  --batch='(gimp-message "Batch mode is available")' --quit
```

For file conversion or editing, use a tested GIMP 3 batch script and verify both the process exit code and the output file. Do not copy GIMP 2.x PDB examples into GIMP 3 without checking API compatibility.

## Verification

- **Environment:** not yet tested in AI-Toolbox CI.
- **Date:** 2026-11-26.
- **Checks performed:** reviewed the official GIMP 3.2.8 release information, official download page, and GIMP 3 command-line/batch documentation.
- **Result:** batch mode is documented and appears suitable for headless CI testing; no installation or image-processing test has yet run.
- **Not tested:** installation, actual batch processing, Windows/macOS behavior, plug-in compatibility, and packaged third-party components.

## Security and limitations

GIMP can load complex and potentially malformed image files and third-party plug-ins. Prefer trusted packages and keep the application updated. Treat plug-ins as executable code and review their origin before installing them. Batch-mode availability depends on the installed build and interpreter plug-ins.

## Sources

- Official project and downloads: https://www.gimp.org/downloads/
- GIMP 3.2.8 release: https://www.gimp.org/release/3.2.8/
- Command-line manual: https://www.gimp.org/man/gimp.html
- GIMP 3 batch scripting documentation: https://developer.gimp.org/resource/script-fu/scriptfu-tools/
- License: https://gitlab.gnome.org/GNOME/gimp/-/blob/master/COPYING
