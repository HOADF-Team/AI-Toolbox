# Environment discovery

Use [inventory.py](../scripts/inventory.py) before proposing an installation.

```bash
python3 scripts/inventory.py --pretty
```

The script uses the Python standard library only. It checks a curated set of command-line tools on `PATH`, probes versions or short help output where possible, checks selected Python modules with import discovery (including Ruff and mypy), and resolves selected Node.js packages from the current working directory. It emits JSON and does not install, update, remove, or configure anything. It makes no network requests.

## Interpret the result correctly

The report's `scope` is always `current_process_environment_only`. It describes only the environment in which the script ran.

Keep these facts separate:

1. **Catalog record exists** — the tool has documentation in AI-Toolbox. This does not mean it is installed.
2. **Available in current runtime** — the executable, Python module, or Node.js package was detected in this process environment.
3. **Available on the user's computer** — must be checked on that computer through an explicitly available and authorized mechanism. Never infer it from a cloud/container runtime.
4. **Available through a connector or hosted service** — a service capability, not a locally installed executable.

A missing command means only that its name was not found on the current PATH. A missing Python module means it was not discoverable by the active interpreter. A missing Node.js package means it could not be resolved from the current working directory's Node module resolution paths; global package stores are not scanned. A detected tool may still be incompatible, misconfigured, or unusable for the requested task.

## Agent procedure

1. Identify the actual execution target: current runtime, project container, VPS, or user's device.
2. Run discovery in that target, if authorized and technically possible.
3. Match detected tools to the catalog by stable ID and check version/platform compatibility.
4. Reuse a suitable existing installation. Do not reinstall merely because a catalog record exists.
5. If absent or unsuitable, research the official upstream source and review license, security, dependencies, permissions, and installation effects before proposing or performing installation.
6. Never install on the user's device without explicit authorization and a clear target.
7. Record the exact target and evidence. Do not promote a catalog status based on discovery alone.

## Current limitations

Ruff and mypy are checked as both PATH commands and discoverable Python modules. Their presence does not mean that lint or type checks have been run.\n\nThe inventory is intentionally curated, not a complete software inventory. It does not inspect arbitrary directories, package managers, GUI applications, services, containers, remote hosts, other users' environments, or global Node.js package stores. Python module detection reports import discoverability, not successful imports or functional correctness. Node package resolution is relative to the current working directory and may not detect packages installed only in other projects. Version/help probes are best-effort and may return no output even when a command exists.
