# rembg

- **ID:** `rembg`
- **Category:** image-tools
- **Status:** `tested`
- **Publisher / maintainer:** Daniel Gatis and contributors
- **Official website:** https://github.com/danielgatis/rembg
- **Source repository:** https://github.com/danielgatis/rembg
- **Documentation:** https://github.com/danielgatis/rembg#readme
- **License:** MIT for the rembg package. The selected `u2netp` model weights are covered by Apache-2.0 according to the U-2-Net maintainer; training dataset terms remain separate.
- **Platforms:** Windows, Linux, macOS (subject to Python and ONNX Runtime wheel support)
- **Version reviewed:** 2.0.88 (PyPI release, 2026-11-24)
- **Version tested:** rembg 2.0.88 with ONNX Runtime 1.32.0
- **Last reviewed:** 2026-11-26

## What it does

rembg removes image backgrounds using local ONNX inference. It can be used as a command-line tool, Python library, HTTP server, or Docker container. Model weights are downloaded on first use and cached locally.

## When an AI agent should use it

Use rembg for automated background removal from product images, illustrations, and other raster assets. Select the model deliberately: model quality, memory use, download size, and license terms vary. For confidential images, prefer local inference and do not use cloud-backed model providers unless the user explicitly approves sending the image to an external service.

## Requirements and costs

- Runtime / dependencies: Python 3.11+; ONNX Runtime. For CPU use the project documents the `cpu` extra. The exact supported Python range should be confirmed against the selected release and ONNX Runtime wheels.
- Account required: no for local models.
- API key or token required: no for local models; remote providers require credentials.
- Paid features or usage costs: local package and U2-Net model have no per-image API fee; remote model providers may charge.
- Network access: required to install packages and download model weights initially; not required for subsequent local inference when the model is cached.
- Permissions: reads input images, writes output images, and stores model files in the rembg cache directory.

## Installation

Create an isolated Python environment and install the CPU backend. Pin the version for reproducible automation:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install "rembg[cpu,cli]==2.0.88"
```

Windows activation uses `.venv\\Scripts\\activate`. Check the official README for GPU-specific installation; GPU support requires a compatible ONNX Runtime, driver, and accelerator stack.

## Basic usage

Specify a model explicitly rather than silently relying on the package default:

```bash
rembg i -m u2netp input.png output.png
```

The `u2netp` weights are downloaded on first use. The upstream implementation pins a model URL and MD5 checksum for its automatic download. Keep the model cache between runs to avoid repeated downloads.

## Verification

- **Environment:** GitHub Actions hosted runner, Ubuntu 26.04.1, CPython 3.13.18, CPU backend.
- **Date:** 2026-11-26.
- **Installed versions:** rembg 2.0.88; ONNX Runtime 1.32.0.
- **Checks performed:** installed the pinned `rembg[cpu,cli]==2.0.88` package; generated a synthetic 160×160 RGB PNG; downloaded the `u2netp` model through the upstream loader; ran CLI background removal; verified PNG output, RGBA mode, dimensions, and a non-uniform alpha channel.
- **Result:** package installation, model download, CPU inference, and alpha-output validation passed.
- **Not tested:** GPU backends, Windows/macOS behavior, other model licenses, or output quality on real-world photographs.


## Security and limitations

- Model weights are separate artifacts with terms independent of the rembg package. The U-2-Net maintainer stated that released code and models follow Apache-2.0, while noting that training dataset licenses are outside the project's control. Review the applicable dataset terms for commercial or redistribution-sensitive use.
- The default model can change between releases and may be substantially larger than `u2netp`; specify a model explicitly for predictable resource use.
- Remote backends send images to third-party services. Do not use them for private images without explicit approval.
- Treat model files as executable-adjacent ML artifacts: obtain them from the upstream URL, retain checksum verification, and avoid disabling it.

## Sources

- PyPI release: https://pypi.org/project/rembg/2.0.88/
- Official project: https://github.com/danielgatis/rembg
- u2netp model loader and checksum: https://github.com/danielgatis/rembg/blob/main/rembg/sessions/u2netp.py
- U-2-Net license: https://github.com/xuebinqin/U-2-Net/blob/master/LICENSE
- Maintainer's model license clarification: https://github.com/xuebinqin/U-2-Net/issues/208
