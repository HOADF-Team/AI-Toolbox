# Local Ollama runtime: zero-API-cost evaluation path

## Purpose

This document describes an optional way to connect a locally running language model to the Skill-selection benchmark. It is intended for a machine the user controls. It does not install software, download model weights, start a server, or run a benchmark by itself.

Ollama is a local model runner with an HTTP API. A local model can be queried without an Inference Provider API key. Model weights still need to be downloaded, which consumes disk space and internet bandwidth. Performance depends on available RAM, GPU/VRAM, model size, and context length.

Official references:
- https://ollama.com/download
- https://docs.ollama.com/quickstart
- https://docs.ollama.com/api/introduction
- https://docs.ollama.com/faq

## Cost and network boundary

- Use a local model name only. Do not select a model whose name ends in `:cloud`.
- Do not create an Ollama API key or sign in for this local-only workflow.
- The local API defaults to `http://127.0.0.1:11434`; keep it bound to loopback.
- Do not set `OLLAMA_HOST=0.0.0.0`, expose port 11434 to the internet, or configure a public tunnel.
- Ollama software and many model weights are available without an inference charge, but downloads use bandwidth and local inference uses the machine's resources. This is not a promise of zero electricity, data, or storage cost.
- Do not download a model until the target machine's free disk space and memory have been checked.
- The Toolbox must never silently install Ollama, download weights, or start a model service.

## Preflight on the target machine

First identify the operating system, total and available RAM, GPU model and VRAM (if present), and free disk space. Choose a model only after checking its published size and the machine's capacity.

The Ollama quickstart lists small examples such as Llama 3.2 1B (about 1.3 GB of model data) and 3B (about 2.0 GB). Those figures are download sizes, not guaranteed runtime RAM requirements. As a general reference, Ollama documentation recommends at least 8 GB available RAM for 7B models, 16 GB for 13B, and 32 GB for 33B. Larger context windows require additional memory.

## Manual setup (only after the user chooses the machine and model)

1. Install Ollama from the official download page for Windows, macOS, or Linux.
2. Start the local Ollama application/service.
3. Download a selected local model explicitly, for example:

   ```bash
   ollama pull llama3.2:1b
   ```

4. Confirm the model is present:

   ```bash
   ollama list
   ```

5. Confirm the service responds locally:

   ```bash
   curl http://127.0.0.1:11434/api/tags
   ```

6. Run one local smoke prompt:

   ```bash
   ollama run llama3.2:1b "Reply with the single word READY."
   ```

The example is illustrative, not a recommendation that this model will perform adequately on every machine. Do not continue to the benchmark if the machine is memory-constrained or the smoke test fails.

## Connecting to the Toolbox benchmark

The existing exchange protocol remains the source of truth:

1. Pin a full 40-character Personal-AI-Library commit SHA.
2. Export the gold-label-free request bundle with `scripts/skill_selection_runtime_eval.py prepare`.
3. The local host must verify its trusted Skills checkout is exactly the pinned commit and load canonical `skills/<id>/SKILL.md` files from that checkout.
4. Send only task text, candidate Skill IDs, and the canonical manifests to the local model. Never send `benchmark.json`, expected decisions, required/acceptable/excluded Skill labels, annotation rationales, or human-review labels.
5. Validate model output against the response schema, then score it offline with `scripts/skill_selection_runtime_eval.py score`.

The current repository does not yet include an Ollama invocation adapter. The benchmark bridge prepares and scores JSON exchanges; it does not call Ollama or any other model. A separate adapter implementation and an actual successful local run are required before claiming that a model is connected or evaluated.

## Security requirements for a future adapter

- Accept only a loopback URL by default; reject non-loopback hosts unless an explicit, separately reviewed configuration is introduced.
- Never send Skills, task data, or outputs to a cloud model or external endpoint.
- Never transmit credentials, API keys, passwords, private keys, approval tokens, or private customer data.
- Treat model output as untrusted. Validate JSON, case IDs, decisions, Skill IDs, duplicates, and complete case coverage before scoring.
- Keep the benchmark evaluator separate from operational workflows. Benchmark selection never grants permission to install tools, access a VPS, change production, or perform financial actions.
- Record the model identifier, Ollama version, host OS, hardware summary, pinned Skills revision, and run ID. Treat these as caller-supplied metadata unless independently attested.
- Preserve the raw response bundle and report. Do not claim that rationale presence proves rationale correctness.

## What counts as a successful connection

A connection is confirmed only when all of the following are observed on the user's target machine:

- Ollama is installed and its version is recorded.
- The selected model is present in `ollama list`.
- The local API responds on loopback.
- A smoke prompt completes successfully.
- The adapter loads canonical Skill manifests from the exact pinned commit.
- A complete response bundle is produced and accepted by the existing evaluator.

Until those checks are performed, status is **prepared, not connected**.
