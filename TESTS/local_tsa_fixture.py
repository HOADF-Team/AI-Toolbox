"""Ephemeral local RFC 3161 TSA fixture for end-to-end tests.

All keys, certificates, requests, and responses are created beneath the caller's
temporary directory. No public TSA or network connection is used.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def issue_local_rfc3161_timestamp(data: bytes, root: Path) -> tuple[Path, Path, Path]:
    """Issue a real RFC 3161 response for data using a temporary local TSA."""
    if not isinstance(data, bytes) or not data:
        raise ValueError("timestamp data must be non-empty bytes")
    root.mkdir(parents=True, exist_ok=True)
    ca_key = root / "tsa-root.key"
    ca_cert = root / "tsa-root.pem"
    tsa_key = root / "tsa-signer.key"
    tsa_csr = root / "tsa-signer.csr"
    tsa_cert = root / "tsa-signer.pem"
    tsa_ext = root / "tsa-signer.ext"
    config = root / "tsa.cnf"
    serial = root / "tsa.srl"
    data_path = root / "timestamped-data.bin"
    request_path = root / "request.tsq"
    response_path = root / "response.tsr"
    data_path.write_bytes(data)

    def run_openssl(*args: str) -> None:
        completed = subprocess.run(
            ["openssl", *args], check=False, capture_output=True, text=True, timeout=30
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"OpenSSL command failed: {args!r}; "
                f"stdout={completed.stdout}; stderr={completed.stderr}"
            )

    run_openssl(
        "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(ca_key), "-out", str(ca_cert),
        "-subj", "/CN=HOADF Ephemeral Test Root", "-days", "2",
        "-addext", "basicConstraints=critical,CA:TRUE",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign",
        "-addext", "subjectKeyIdentifier=hash",
    )
    run_openssl(
        "req", "-new", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(tsa_key), "-out", str(tsa_csr),
        "-subj", "/CN=HOADF Ephemeral Test TSA",
    )
    tsa_ext.write_text(
        "[ v3_tsa ]\n"
        "basicConstraints = critical,CA:FALSE\n"
        "keyUsage = critical,digitalSignature,nonRepudiation\n"
        "extendedKeyUsage = critical,timeStamping\n"
        "subjectKeyIdentifier = hash\n"
        "authorityKeyIdentifier = keyid,issuer\n",
        encoding="utf-8",
    )
    run_openssl(
        "x509", "-req", "-in", str(tsa_csr), "-CA", str(ca_cert),
        "-CAkey", str(ca_key), "-CAcreateserial", "-out", str(tsa_cert),
        "-days", "1", "-sha256", "-extfile", str(tsa_ext), "-extensions", "v3_tsa",
    )
    serial.write_text("01\n", encoding="ascii")
    config.write_text(
        "[ tsa ]\n"
        "default_tsa = tsa_config1\n"
        "[ tsa_config1 ]\n"
        f"serial = {serial}\n"
        "crypto_device = builtin\n"
        f"signer_cert = {tsa_cert}\n"
        f"certs = {ca_cert}\n"
        f"signer_key = {tsa_key}\n"
        "signer_digest = sha256\n"
        "default_policy = 1.2.3.4.1\n"
        "digests = sha256, sha384, sha512\n"
        "accuracy = secs:1\n"
        "ordering = yes\n"
        "tsa_name = yes\n"
        "ess_cert_id_chain = no\n",
        encoding="utf-8",
    )
    run_openssl(
        "ts", "-query", "-data", str(data_path), "-sha256", "-cert",
        "-out", str(request_path),
    )
    run_openssl(
        "ts", "-reply", "-config", str(config), "-queryfile",
        str(request_path), "-out", str(response_path),
    )
    return response_path, ca_cert, tsa_cert
