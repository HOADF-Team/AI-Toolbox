# AI-Toolbox

**A growing, tested collection of software tools that AI agents can discover, install, verify, and use.**

AI-Toolbox complements [Personal-AI-Library](https://github.com/HOADF-Team/Personal-AI-Library):

- **Personal-AI-Library** describes workflows and methods: how an agent should approach a task.
- **AI-Toolbox** records concrete tools: what they do, where to obtain them, how to install and use them, and what has been verified.

The goal is a practical, reusable toolbox maintained with the help of AI agents—not merely a link directory and not a requirement for users to write software themselves.

## How it works

1. **Check first:** search the catalog and existing tool records.
2. **Reuse:** if a suitable tool is recorded, check compatibility and whether it is installed, then use it.
3. **Find a gap:** search for candidates from their original publishers.
4. **Review safely:** check provenance, license, platform support, dependencies, permissions, security, and installation steps.
5. **Test:** use an isolated or disposable environment where practical. Record exactly what was and was not tested.
6. **Contribute:** prepare a tool record and submit it through a pull request. Never label an untested tool as verified.

## Verification status

| Status | Meaning |
|---|---|
| `discovered` | Candidate found; not yet reviewed or tested |
| `reviewed` | Source, license, requirements, and risks reviewed |
| `tested` | A documented test was actually performed |
| `ready` | Repeatable installation/use instructions and checks are documented |
| `blocked` | A concrete issue prevents safe or reliable use |
| `deprecated` | No longer recommended; reason recorded |

A status is not a guarantee that a tool is safe or suitable for every environment.

## Repository layout

```text
AI-Toolbox/
├── README.md
├── AGENTS.md
├── CATALOG/
│   ├── README.md
│   └── tools.json
├── TOOLS/
│   └── <category>/<tool-id>/
│       ├── TOOL.md
│       └── references/
├── REQUESTS/
├── TESTS/
├── TOOL-TEMPLATE.md
├── SECURITY.md
└── LICENSE
```

Third-party software is normally obtained from its original publisher. This repository stores metadata, reviewed instructions, test records, and only files that may legally and safely be redistributed. It is not a mirror of every upstream project.

## Initial categories

- `browser-automation` — browser control, end-to-end testing, screenshots
- `web-development` — web frameworks, UI components, design and prototyping
- `python` — Python utilities and application tooling
- `image-tools` — image editing, conversion, background removal, upscaling
- `automation` — workflows and task automation
- `bots-and-apis` — bot frameworks, APIs, messaging integrations
- `documents` — PDF, office files, spreadsheets and conversion
- `3d-and-graphics` — 3D, rendering and graphics utilities

Categories may evolve as real needs appear.

## Contributing

AI agents may research and prepare contributions. Every new or changed record must include sources and evidence and follow [AGENTS.md](AGENTS.md). Never commit credentials, private keys, access tokens, personal data, or unreviewed executable payloads.

## Relationship to Skills

A Skill may tell an agent *when* to use a class of tools or *how* to complete a workflow. A Tool record tells the agent *which concrete tool* is suitable and how to obtain, configure, test, and invoke it. The repositories should link to each other rather than duplicate their contents.

## License

Repository-authored metadata, documentation, and helper material are provided under the MIT License unless a file states otherwise. Third-party tools and assets retain their own licenses and terms. See [LICENSE](LICENSE).
