# LibreOffice

- **ID:** `libreoffice`
- **Category:** documents
- **Status:** `tested`
- **Publisher / maintainer:** The Document Foundation and LibreOffice community
- **Official website:** https://www.libreoffice.org/
- **Source repository:** https://git.libreoffice.org/core
- **Documentation:** https://help.libreoffice.org/
- **License:** Mozilla Public License 2.0 (MPL-2.0); the distribution includes components under additional licenses
- **Platforms:** Windows, macOS, Linux
- **Version observed in test environment:** 25.2.3.2
- **Last reviewed:** 2026-11-26

## What it does

LibreOffice is an office productivity suite for word processing, spreadsheets, presentations, drawing, and database tasks. Its command-line interface can convert supported document formats in headless mode.

## When an AI agent should use it

Use LibreOffice when a task requires editing or converting office documents, spreadsheets, or presentations, especially when an actual office rendering engine is needed. It complements format-specific Python libraries: use those for structured data manipulation, and LibreOffice when document layout/rendering or cross-format conversion matters.

## Requirements and costs

- Runtime / dependencies: desktop application with platform-specific native dependencies; headless conversion still requires the LibreOffice installation.
- Account required: no.
- API key or token required: no.
- Paid features or usage costs: free software; hosting or support services may have separate costs.
- Network access: not required for local document conversion.
- Permissions: reads input documents and writes output files; office documents can contain macros and external links.

## Installation

Download installers from the official [LibreOffice download page](https://www.libreoffice.org/download/download-libreoffice/), or use the supported package manager for the target operating system. Verify with `libreoffice --version`.

For automated headless conversions, use a dedicated temporary user profile to avoid locking or interfering with a user's interactive LibreOffice session:

```bash
mkdir -p ./converted ./lo-profile
libreoffice -env:UserInstallation=file://"$PWD/lo-profile" \
  --headless --convert-to pdf --outdir ./converted ./input.docx
```

Uninstall through the original OS package manager or installer. Do not delete system-managed files manually.

## Basic usage

```bash
libreoffice --version
libreoffice --headless --convert-to pdf --outdir ./out document.docx
```

Check the generated file and visually inspect layout when formatting fidelity matters.

## Verification

- **Environment:** Debian GNU/Linux 13, Linux x86_64, current isolated execution container.
- **Date:** 2026-11-26.
- **Version:** 25.2.3.2.
- **Checks performed:** created a sample DOCX with python-docx; ran LibreOffice headless conversion to PDF using a dedicated temporary user profile; verified that the output PDF exists and is non-empty.
- **Result:** DOCX-to-PDF conversion smoke test passed.
- **Installation tested:** no; LibreOffice was pre-existing.
- **Not tested:** complex layouts, macros, embedded objects, spreadsheet formulas, presentation rendering, Windows/macOS packages.

## Security and limitations

Do not enable or execute macros in untrusted documents. Treat external links, embedded files, and document metadata as potentially sensitive. Conversion fidelity varies by source format, fonts, and layout features. Headless conversion should use an isolated profile and restricted filesystem access when processing untrusted documents. The application bundle contains components under multiple licenses; inspect the installed license information for redistribution.

## Sources

- Official website and downloads: https://www.libreoffice.org/
- Official help: https://help.libreoffice.org/
- Licensing information: https://www.libreoffice.org/licenses/
- Source repository: https://git.libreoffice.org/core
