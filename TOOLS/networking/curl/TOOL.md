# curl

- **ID:** `curl`
- **Category:** networking
- **Status:** `tested`
- **Publisher / maintainer:** curl project
- **Official website:** https://curl.se/
- **Source repository:** https://github.com/curl/curl
- **Documentation:** https://curl.se/docs/
- **License:** curl license (MIT-like, but not identical to MIT; SPDX identifier `curl`)
- **Platforms:** Linux, macOS, Windows
- **Version reviewed:** 8.23.0 (upstream stable release, 2026-10-14)
- **Runtime version tested:** 8.10.1 in the current isolated assistant runtime
- **Last reviewed:** 2026-11-26

## What it does

curl transfers data to and from URLs. It supports HTTP(S) APIs, redirects, headers, cookies, authentication, multipart uploads, downloads, and many additional protocols. The `curl` CLI uses libcurl.

## When an AI agent should use it

Use curl to:
- call REST endpoints and inspect HTTP status/headers;
- send JSON requests and form or multipart uploads;
- download files from trusted URLs;
- reproduce API requests without introducing a language-specific dependency;
- diagnose DNS, TLS, redirects, timeouts, and response behavior.

For complex API contracts, authentication flows, or repeatable collections, use an OpenAPI-aware client or a dedicated test framework in addition to curl.

## Requirements and costs

- Runtime: native curl executable; no Python or Node.js required.
- Account / API key: only when the target API requires one.
- Cost: open source; API services, bandwidth, and compute may have separate costs.
- Network: required for remote endpoints; local HTTP tests do not require external access.
- Permissions: network access and read/write access to files explicitly named in arguments.

## Installation

Prefer the operating system's trusted package manager or the official platform distribution.

Debian / Ubuntu:

```bash
sudo apt-get update
sudo apt-get install curl
```

macOS (Homebrew):

```bash
brew install curl
```

Windows includes curl in supported modern releases. In Windows PowerShell 5.1, use `curl.exe` because `curl` may be an alias for `Invoke-WebRequest`.

Verify:

```bash
curl --version
```

## Basic usage

GET JSON and fail on HTTP 4xx/5xx:

```bash
curl --fail --silent --show-error https://api.example.com/items
```

Send JSON:

```bash
curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  -d '{"name":"example"}' \
  https://api.example.com/items
```

Inspect response headers:

```bash
curl --head --show-error https://example.com/
```

## Verification

- **Current isolated runtime:** Debian-based Linux x86_64; curl 8.10.1 available at `/usr/local/bin/curl`.
- **Local functional test:** GET request to a local test HTTP server; JSON POST with content type; successful HTTP response handling. All passed.
- **CI test:** workflow reinstalls curl from the Ubuntu package repository, then exercises GET and JSON POST against a local Python HTTP fixture. The workflow also checks `curl --fail` behavior on an HTTP 404 response.
- **Status scope:** these checks verify the tested Linux runtime and command behavior only. They do not establish availability on the user's computer or verify every supported protocol/build option.

## Security and limitations

- Never put API tokens, passwords, or private data directly into committed scripts, shell history, or logs.
- Avoid placing secrets in command-line arguments where other local processes may inspect them. Use an appropriately permission-restricted config or secret-injection mechanism.
- Do not use `--insecure` / `-k` to bypass TLS verification as a routine workaround.
- Treat URLs and redirects as untrusted input. Restrict allowed schemes, hosts, and destination networks in automation to prevent SSRF and unintended access to local or internal services.
- Set connection and total timeouts for automation; use bounded retries only for idempotent operations.
- curl supports many protocols. Restrict the allowed protocols when processing untrusted URLs and avoid passing user-controlled arguments through a shell.

## Sources

- Official website and release information: https://curl.se/
- Official manual: https://curl.se/docs/manpage.html
- Official license statement and source: https://github.com/curl/curl
- Official install guidance: https://curl.se/docs/install.html
