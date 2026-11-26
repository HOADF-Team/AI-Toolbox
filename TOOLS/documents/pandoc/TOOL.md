# Pandoc

- **ID:** `pandoc`
- **Category:** documents
- **Status:** `tested`
- **Publisher / maintainer:** John MacFarlane and Pandoc contributors
- **Official website:** https://pandoc.org/
- **Source repository:** https://github.com/jgm/pandoc
- **Documentation:** https://pandoc.org/MANUAL.html
- **License:** GNU GPL version 2 or later (GPL-2.0-or-later); some bundled components and data have separate notices
- **Platforms:** Windows, macOS, Linux
- **Version observed in test environment:** 3.1.11.1
- **Last reviewed:** 2026-11-26

## What it does

Pandoc is a universal markup and document converter. It converts between Markdown, HTML, DOCX, ODT, EPUB, LaTeX, reStructuredText, and many other formats through a structured intermediate document model.

## When an AI agent should use it

Use Pandoc for repeatable document conversion, generating DOCX/HTML/EPUB from Markdown, extracting structured content from supported formats, and building documentation pipelines. It is especially useful for source-controlled documents.

Do not expect perfect round-trip fidelity. Conversions from more expressive formats into a simpler target may lose layout or document-specific features. Use LibreOffice when the final office rendering needs to be inspected or adjusted.

## Requirements and costs

- Runtime / dependencies: standalone Pandoc executable; some output formats require external tools such as LaTeX engines or PDF renderers.
- Account required: no.
- API key or token required: no.
- Paid features or usage costs: open source; external PDF engines or hosted infrastructure may have separate costs.
- Network access: not required for local conversion unless a filter, remote resource, or external service uses it.
- Permissions: reads input files and may write output, extracted media, or run explicitly configured filters.

## Installation

Use the official [installation instructions](https://pandoc.org/installing.html) or the OS distribution's package manager. Verify with `pandoc --version`. Prefer official release packages and keep a known version pinned in reproducible build environments.

Uninstall through the same package manager or installer used for installation.

## Basic usage

```bash
pandoc source.md -o output.docx
pandoc source.md -t html -o output.html
pandoc input.docx -t plain -o extracted.txt
```

For PDF output, select and configure an appropriate PDF engine; Pandoc does not itself render PDF pages.

## Verification

- **Environment:** Debian GNU/Linux 13, Linux x86_64, current isolated execution container.
- **Date:** 2026-11-26.
- **Version:** 3.1.11.1.
- **Checks performed:** converted a sample Markdown file to DOCX and HTML; verified both outputs were created and non-empty.
- **Result:** Markdown-to-DOCX and Markdown-to-HTML smoke tests passed.
- **Installation tested:** no; Pandoc was pre-existing.
- **Not tested:** complex tables, citations, filters, math rendering, EPUB, PDF engines, round-trip fidelity.

## Security and limitations

Pandoc filters and Lua filters can execute code. Review filters and templates before running them, especially when processing untrusted input. Remote images and included resources may trigger network access. Conversion is not guaranteed to preserve every formatting feature; inspect the final output. Pandoc and bundled components have separate copyright and license notices.

## Sources

- Official website and installation: https://pandoc.org/
- User's Guide: https://pandoc.org/MANUAL.html
- Source repository and license: https://github.com/jgm/pandoc
- License and copyright details: https://github.com/jgm/pandoc/blob/main/COPYRIGHT
