# Poppler utilities

- **ID:** `poppler-utils`
- **Category:** documents
- **Status:** `tested`
- **Publisher / maintainer:** Poppler project contributors
- **Official website:** https://poppler.freedesktop.org/
- **Source repository:** https://gitlab.freedesktop.org/poppler/poppler
- **Documentation:** https://manpages.debian.org/unstable/poppler-utils/
- **License:** GNU GPL family; Poppler is GPL, not LGPL. Confirm exact notices for the distribution package and bundled components before redistribution.
- **Platforms:** Linux, Windows, macOS; package availability and utility names vary
- **Version observed in test environment:** 25.06.0 (Poppler command-line tools)
- **Last reviewed:** 2026-11-26

## What it does

Poppler is a PDF rendering and processing library. The Poppler utilities package provides command-line tools including:

- `pdftotext` — extract text from PDF files.
- `pdfinfo` — inspect PDF metadata and page information.
- `pdftoppm` / `pdftocairo` — render PDF pages to images.
- `pdftoppm` and other utilities can support downstream OCR and document workflows.

## When an AI agent should use it

Use Poppler utilities for local PDF inspection, text extraction, metadata checks, and page rendering. Combine `pdftotext` with Tesseract when a PDF is image-only: render pages to images first, then OCR them. Prefer native text extraction when the PDF already contains a text layer.

## Requirements and costs

- Runtime / dependencies: native Poppler utilities and supporting libraries; language/encoding data may be installed separately.
- Account required: no.
- API key or token required: no.
- Paid features or usage costs: open source; no per-file fee.
- Network access: not required for local PDF processing.
- Permissions: reads the selected PDF and writes extracted text or rendered images to the chosen output path.

## Installation

On Debian/Ubuntu, the utilities are typically packaged as `poppler-utils`:

```bash
sudo apt install poppler-utils
```

Use the official Poppler download page or the target OS package manager on other platforms. Verify with `pdftotext -v` and `pdfinfo -v`.

Uninstall through the same package manager. On Linux, avoid manually removing shared libraries used by other applications.

## Basic usage

```bash
pdfinfo input.pdf
pdftotext input.pdf output.txt
pdftotext -layout input.pdf output.txt
pdftoppm -png -r 150 input.pdf page
```

## Verification

- **Environment:** Debian GNU/Linux 13, Linux x86_64, current isolated execution container.
- **Date:** 2026-11-26.
- **Version:** 25.06.0.
- **Checks performed:** generated a one-page sample PDF; `pdfinfo` reported one page; `pdftotext` extracted the expected sentence and the output was checked.
- **Result:** PDF metadata inspection and text extraction smoke tests passed.
- **Installation tested:** no; Poppler utilities were pre-existing.
- **Not tested:** encrypted PDFs, malformed/adversarial PDFs, image rendering, complex fonts, Unicode edge cases, Windows/macOS packages.

## Security and limitations

PDF parsers process complex, potentially untrusted files. Keep Poppler updated and process untrusted PDFs in a sandbox with restricted filesystem and network access. Do not upload confidential documents to public bug trackers or external services. Poppler is GPL, not LGPL; review the license implications before embedding or linking it into another application or redistributing binaries.

## Sources

- Official project and releases: https://poppler.freedesktop.org/
- Upstream source repository: https://gitlab.freedesktop.org/poppler/poppler
- Project description and GPL licensing: https://github.com/innodatalabs/poppler
- Debian utilities documentation: https://manpages.debian.org/unstable/poppler-utils/
