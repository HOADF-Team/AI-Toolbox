# Podman

- **ID:** `podman`
- **Category:** container-runtime
- **Status:** `reviewed`
- **Publisher / maintainers:** Podman community; project currently hosted under the podman-container-tools GitHub organization
- **Official website:** https://podman.io/
- **Source repository:** https://github.com/podman-container-tools/podman
- **Documentation:** https://docs.podman.io/
- **License:** Apache-2.0
- **Platforms:** Linux; Windows and macOS through Podman Machine (a managed Linux VM)
- **Version reviewed:** 6.2.0
- **Last reviewed:** 2026-11-26

## What it does

Podman is an OCI container and pod engine. Unlike Docker Engine, it does not require a persistent central daemon for ordinary local container operations. It supports rootless containers, image builds, pods, volumes, networks, and a Docker-compatible CLI/API surface for many workflows.

On Linux, Podman can run containers directly. On Windows and macOS, the CLI connects to a Linux guest managed by `podman machine`; Windows uses WSL2 as its machine provider. Podman is useful for creating disposable environments to inspect and test tools without installing all of their dependencies into the host environment.

## Why it is the first container runtime to evaluate

- Rootless execution is a first-class workflow and avoids making a long-running root-owned daemon the default.
- It is available in mainstream Linux distribution repositories and supports Windows/macOS through a managed Linux VM.
- Its CLI is intentionally familiar to Docker users; many Docker-oriented tools can use Podman's Docker-compatible API socket.
- It complements the existing inventory, CI smoke tests, and tool records by enabling isolated installation and execution.

Docker Engine remains a compatibility alternative. Its daemon can also be configured for rootless operation, but the default client/server model and Docker Desktop subscription terms make Podman the first candidate for this toolbox's local agent workflows.

## When an AI agent should use it

Use Podman when an agent needs a disposable Linux environment, a reproducible tool test, or an OCI image without modifying the host's language environment.

Typical safe workflow:

1. Inspect the image source, digest, Dockerfile/Containerfile, entrypoint, and requested permissions.
2. Prefer a pinned image digest or trusted publisher and a narrow, bounded container command.
3. Run rootless and disable networking when the task does not need it:

   ```bash
   podman run --rm --network=none \
     --read-only --cap-drop=all \
     --security-opt=no-new-privileges \
     docker.io/library/alpine:3.22 \
     sh -c 'cat /etc/alpine-release'
   ```

4. Mount only the minimum required project directory. Avoid mounting the host home directory, SSH agent, Docker/Podman sockets, or credential stores.
5. Remove disposable containers and temporary images when no longer needed.

For Windows/macOS, initialize and start the VM explicitly:

```bash
podman machine init
podman machine start
podman info
```

## Requirements, installation, and cost

- **Linux:** install from the distribution package repository where possible. Debian 11+ and Ubuntu 20.10+ provide Podman packages in their repositories; Fedora/RHEL family uses DNF.
- **Windows/macOS:** install the official Podman package, then create and start a Podman Machine.
- **Runtime components:** OCI runtime such as `crun` or `runc`; rootless networking/storage helpers vary by distribution and version.
- **Cost:** open-source under Apache-2.0; no license fee for the engine. Container images and third-party components have their own licenses.
- **Account/API key:** not required for local use. Private registries may require authentication.
- **Network:** registry access is needed to pull images; containers can run with `--network=none` when they do not need networking.
- **Privileges:** rootless containers are preferred. Initial installation may require administrator privileges, and machine/VM setup requires host virtualization support on Windows/macOS.

## Security and limitations

- Rootless containers reduce host privilege exposure but are not a complete security boundary; containers still share the Linux kernel.
- Never use `--privileged` for ordinary tool tests. Avoid host PID/network namespaces and broad bind mounts.
- Treat images as executable third-party code. Verify publisher, digest, provenance/signature where available, and image license before execution.
- Use `--read-only`, `--cap-drop=all`, `--security-opt=no-new-privileges`, and `--network=none` where compatible with the task.
- Do not mount secrets or host sockets into untrusted containers.
- Docker CLI/API compatibility is substantial but not universal; validate any Docker-specific workflow before assuming it works unchanged.
- Podman Machine adds a Linux VM layer on Windows/macOS; networking, filesystem performance, and volume paths differ from native Linux.
- A container test does not prove the tool is safe or compatible on every host OS/kernel.

## Verification

- **Review date:** 2026-11-26.
- **Source/license review:** official installation guidance, release information, repository, and Apache-2.0 license reviewed.
- **Installation test:** pending pinned distribution package installation in GitHub Actions.
- **Runtime test:** pending rootless container execution using a small public image with networking disabled after image pull.
- **Status:** `reviewed`; do not treat as installed or runtime-tested until the workflow passes.

## Sources

- Official installation matrix and platform guidance: https://podman.io/docs/installation
- Official downloads and current release: https://podman.io/downloads
- Upstream releases: https://github.com/podman-container-tools/podman/releases
- CLI and engine documentation: https://docs.podman.io/
- Upstream source and Apache-2.0 license: https://github.com/podman-container-tools/podman
