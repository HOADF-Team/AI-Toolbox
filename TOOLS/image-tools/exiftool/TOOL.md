# ExifTool

- **ID:** `exiftool`
- **Category:** image-tools
- **Status:** `reviewed`
- **Publisher / maintainer:** Phil Harvey
- **Official website:** https://exiftool.sourceforge.net/
- **Source repository:** https://github.com/exiftool/exiftool
- **Documentation:** https://exiftool.org/
- **License:** Dual-licensed under the same terms as Perl: Perl Artistic License or GNU GPL (see the upstream distribution for exact notices)
- **Platforms:** Windows, macOS, Linux and other Perl-supported Unix platforms
- **Version reviewed:** 13.64 (official download page, 2026-11-16)
- **Last reviewed:** 2026-11-26

## What it does

ExifTool is a Perl library and command-line application for reading, writing, and editing metadata in images, audio, video, and many other file formats. It supports EXIF, GPS, IPTC, XMP, ICC profiles, camera maker notes, and many format-specific metadata fields.

## When an AI agent should use it

Use ExifTool to inspect image metadata, identify embedded GPS coordinates, audit camera and copyright fields, and remove or update metadata before publishing images. It is especially useful when preparing public portfolio or marketplace assets: inspect GPS/location data and personal metadata before upload.

Start with read-only inspection. Do not remove or rewrite metadata until the user has approved the intended changes and originals have been preserved.

## Requirements and costs

- Runtime / dependencies: Perl 5.004 or later for the full Perl distribution; the official Windows executable package includes its runtime.
- Account required: no.
- API key or token required: no.
- Paid features or usage costs: free software; no per-file fee.
- Network access: not required for local metadata operations.
- Permissions: reads file metadata; write operations modify the target file and may change timestamps or metadata structure.

## Installation

ExifTool can run directly from its extracted distribution without a system-wide installation. Follow the official [platform-specific installation instructions](https://exiftool.org/install.html). The official site publishes package checksums; verify the downloaded archive before use.

On Unix-like systems, the full Perl distribution can be tested and installed with its documented Perl/Make workflow. Windows users can use the standalone executable package. Uninstall using the original installation method; avoid deleting a shared Perl library directory unless its contents are confirmed to belong only to ExifTool.

## Basic usage

```bash
exiftool image.jpg
exiftool -GPS:all -a -G1 image.jpg
exiftool -all= -overwrite_original image-copy.jpg
```

The metadata-removal example is destructive to the target file. Use a copy, omit `-overwrite_original` when you want a backup, and inspect the result before publishing.

## Verification

- **Environment inspected:** Linux x86_64, current isolated execution container.
- **Date:** 2026-11-26.
- **Checks performed:** reviewed official project description, download page, installation instructions, checksums availability, and upstream copyright/license statement.
- **Availability:** `exiftool` was not found in PATH.
- **Installation tested:** no.
- **Runtime test:** not performed; no ExifTool binary or Perl package was installed.
- **Status rationale:** reviewed, not tested.

## Security and limitations

Metadata can contain sensitive information such as GPS coordinates, device identifiers, timestamps, author names, and editing history. Inspect files before publishing them. Writing metadata can be destructive or may invalidate signatures/embedded structures; preserve originals and verify output. ExifTool parses many complex formats, so process untrusted files in a restricted environment and keep it updated. Follow the selected Artistic/GPL license terms if redistributing it.

## Sources

- Official project and downloads: https://exiftool.sourceforge.net/
- Installation instructions: https://exiftool.org/install.html
- Upstream source and license statement: https://github.com/exiftool/exiftool
