# Tesseract OCR

- **ID:** `tesseract`
- **Category:** documents
- **Status:** `tested`
- **Publisher / maintainer:** Tesseract OCR contributors; originally open-sourced by HP, later maintained by Google and the community
- **Official website:** https://tesseract-ocr.github.io/
- **Source repository:** https://github.com/tesseract-ocr/tesseract
- **Documentation:** https://tesseract-ocr.github.io/tessdoc/
- **License:** Apache License 2.0; language traineddata files and third-party components may have separate terms
- **Platforms:** Windows, macOS, Linux
- **Version observed in test environment:** 5.5.0
- **Last reviewed:** 2026-11-26

## What it does

Tesseract is an optical character recognition (OCR) engine with a command-line interface and a C/C++ API. It extracts machine-readable text from images and scanned documents. Language recognition depends on installed traineddata files.

## When an AI agent should use it

Use Tesseract when a PDF or image contains text as pixels rather than a selectable text layer. For PDFs, render pages with Poppler first, then OCR each page. If the PDF already has a text layer, use Poppler text extraction instead.

Tesseract supports many languages. The traineddata must be available for each requested language; language names are passed with `-l` (for example, `eng`, `rus`, or `fin`).

## Requirements and costs

- Runtime / dependencies: Tesseract executable, image processing libraries, and language traineddata.
- Account required: no.
- API key or token required: no.
- Paid features or usage costs: open source; no per-page fee.
- Network access: not required for local OCR after the engine and language data are installed.
- Permissions: reads source images and writes recognized text or other selected output formats.

## Installation

Use the official [installation guide](https://tesseract-ocr.github.io/tessdoc/Installation.html) or your OS package manager. Install the engine and the required language data packages separately where your distribution splits them.

Verify the engine with `tesseract --version` and list installed languages with `tesseract --list-langs`.

Uninstall the engine and language data through the package manager or installer used to install them.

## Basic usage

```bash
tesseract scan.png output -l eng
tesseract scan.png output -l rus
tesseract scan.png output -l fin
tesseract scan.png output pdf
```

OCR accuracy depends on image quality, layout, font, language model, rotation, and preprocessing. Inspect extracted text rather than assuming recognition is exact.

## Verification

- **Environment:** Debian GNU/Linux 13, Linux x86_64, current isolated execution container.
- **Date:** 2026-11-26.
- **Version:** 5.5.0.
- **Checks performed:** generated a synthetic image containing the phrase “Tesseract OCR smoke test”; ran OCR with English language data; verified the expected phrase appeared in the output. Confirmed `eng`, `rus`, and `fin` are listed as installed languages.
- **Result:** English OCR smoke test passed; Russian and Finnish traineddata were detected but not separately accuracy-tested.
- **Installation tested:** no; Tesseract and its language data were pre-existing.
- **Not tested:** handwriting, low-resolution scans, multi-column layouts, tables, rotated pages, real-world Russian/Finnish accuracy, searchable PDF generation.

## Security and limitations

OCR output is probabilistic and must be checked for important names, numbers, legal or financial information. Poor scans, handwriting, unusual fonts, skew, and complex layouts reduce accuracy. Process untrusted image files in a restricted environment. Language traineddata is separate from the engine and may have its own packaging and license notices.

## Sources

- Official project and Apache-2.0 license: https://github.com/tesseract-ocr/tesseract/
- User manual: https://tesseract-ocr.github.io/tessdoc/
- Installation and language data guidance: https://tesseract-ocr.github.io/tessdoc/Installation.html
- Command-line usage: https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html
