"""Ephemeral local RFC 3161 TSA and CRL fixture for offline security tests.

All keys, certificates, CRLs, requests, and responses are created beneath the
caller's temporary directory. No public TSA or network connection is used.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


class LocalRfc3161TSA:
    """One temporary local TSA that can issue tokens and CA-signed CRLs."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self.root = root
        self.ca_key = root / "tsa-root.key"
        self.ca_cert = root / "tsa-root.pem"
        self.tsa_key = root / "tsa-signer.key"
        self.tsa_csr = root / "tsa-signer.csr"
        self.tsa_cert = root / "tsa-signer.pem"
        self.tsa_ext = root / "tsa-signer.ext"
        self.ca_config = root / "ca.cnf"
        self.config = root / "tsa.cnf"
        self.serial = root / "tsa.srl"
        self.ca_serial = root / "serial"
        self.database = root / "index.txt"
        self.crl_number = root / "crlnumber"
        self.new_certs = root / "newcerts"
        self.historical_crl = root / "tsa-historical.crl"
        self.counter = 0

        self.new_certs.mkdir()
        self.database.write_text("", encoding="ascii")
        self.ca_serial.write_text("1000\n", encoding="ascii")
        self.serial.write_text("01\n", encoding="ascii")
        self.crl_number.write_text("1000\n", encoding="ascii")
        self._run_openssl(
            "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(self.ca_key), "-out", str(self.ca_cert),
            "-subj", "/CN=HOADF Ephemeral Test Root", "-days", "3",
            "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign",
            "-addext", "subjectKeyIdentifier=hash",
        )
        self._run_openssl(
            "req", "-new", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(self.tsa_key), "-out", str(self.tsa_csr),
            "-subj", "/CN=HOADF Ephemeral Test TSA",
        )
        self.tsa_ext.write_text(
            "[ v3_tsa ]\n"
            "basicConstraints = critical,CA:FALSE\n"
            "keyUsage = critical,digitalSignature,nonRepudiation\n"
            "extendedKeyUsage = critical,timeStamping\n"
            "subjectKeyIdentifier = hash\n"
            "authorityKeyIdentifier = keyid,issuer\n",
            encoding="utf-8",
        )
        self.ca_config.write_text(
            "[ ca ]\n"
            "default_ca = CA_default\n"
            "[ CA_default ]\n"
            f"dir = {root}\n"
            "database = $dir/index.txt\n"
            "new_certs_dir = $dir/newcerts\n"
            "certificate = $dir/tsa-root.pem\n"
            "private_key = $dir/tsa-root.key\n"
            "serial = $dir/serial\n"
            "crlnumber = $dir/crlnumber\n"
            "default_md = sha256\n"
            "default_days = 2\n"
            "default_crl_days = 2\n"
            "policy = policy_any\n"
            "x509_extensions = v3_tsa\n"
            "unique_subject = no\n"
            "[ policy_any ]\n"
            "commonName = supplied\n"
            "[ v3_tsa ]\n"
            "basicConstraints = critical,CA:FALSE\n"
            "keyUsage = critical,digitalSignature,nonRepudiation\n"
            "extendedKeyUsage = critical,timeStamping\n"
            "subjectKeyIdentifier = hash\n"
            "authorityKeyIdentifier = keyid,issuer\n"
            "[ v3_intermediate_ca ]\n"
            "basicConstraints = critical,CA:TRUE,pathlen:0\n"
            "keyUsage = critical,keyCertSign,cRLSign\n"
            "subjectKeyIdentifier = hash\n"
            "authorityKeyIdentifier = keyid,issuer\n",
            encoding="utf-8",
        )
        self._run_openssl(
            "ca", "-batch", "-notext", "-config", str(self.ca_config),
            "-extensions", "v3_tsa", "-in", str(self.tsa_csr),
            "-out", str(self.tsa_cert),
        )
        self.serial.write_text("01\n", encoding="ascii")
        self.config.write_text(
            "[ tsa ]\n"
            "default_tsa = tsa_config1\n"
            "[ tsa_config1 ]\n"
            f"serial = {self.serial}\n"
            "crypto_device = builtin\n"
            f"signer_cert = {self.tsa_cert}\n"
            f"certs = {self.ca_cert}\n"
            f"signer_key = {self.tsa_key}\n"
            "signer_digest = sha256\n"
            "default_policy = 1.2.3.4.1\n"
            "digests = sha256, sha384, sha512\n"
            "accuracy = secs:1\n"
            "ordering = yes\n"
            "tsa_name = yes\n"
            "ess_cert_id_chain = no\n",
            encoding="utf-8",
        )
        self.generate_crl(self.historical_crl)

    @staticmethod
    def _run_openssl(*args: str) -> None:
        completed = subprocess.run(
            ["openssl", *args], check=False, capture_output=True, text=True, timeout=30
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"OpenSSL command failed: {args!r}; "
                f"stdout={completed.stdout}; stderr={completed.stderr}"
            )

    def issue(self, data: bytes) -> Path:
        """Issue one RFC 3161 token for exact data bytes."""
        if not isinstance(data, bytes) or not data:
            raise ValueError("timestamp data must be non-empty bytes")
        self.counter += 1
        stem = f"timestamp-{self.counter:03d}"
        data_path = self.root / f"{stem}.bin"
        request_path = self.root / f"{stem}.tsq"
        response_path = self.root / f"{stem}.tsr"
        data_path.write_bytes(data)
        self._run_openssl(
            "ts", "-query", "-data", str(data_path), "-sha256", "-cert",
            "-out", str(request_path),
        )
        self._run_openssl(
            "ts", "-reply", "-config", str(self.config), "-queryfile",
            str(request_path), "-out", str(response_path),
        )
        return response_path

    def issue_intermediate_ca(self, name: str = "intermediate") -> Path:
        """Issue a temporary CA certificate signed by the fixture root."""
        key = self.root / f"{name}.key"
        csr = self.root / f"{name}.csr"
        certificate = self.root / f"{name}.pem"
        self._run_openssl(
            "req", "-new", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key), "-out", str(csr), "-subj",
            f"/CN=HOADF Ephemeral {name}",
        )
        self._run_openssl(
            "ca", "-batch", "-notext", "-config", str(self.ca_config),
            "-extensions", "v3_intermediate_ca", "-in", str(csr),
            "-out", str(certificate),
        )
        return certificate

    def revoke_certificate(self, certificate: Path) -> None:
        """Revoke any certificate issued by this fixture CA."""
        self._run_openssl(
            "ca", "-batch", "-config", str(self.ca_config),
            "-revoke", str(certificate),
        )

    def revoke_tsa_certificate(self) -> None:
        """Revoke the TSA signer certificate in the local test CA database."""
        self._run_openssl(
            "ca", "-batch", "-config", str(self.ca_config),
            "-revoke", str(self.tsa_cert),
        )

    def generate_crl(self, destination: Path | None = None) -> Path:
        """Generate a fresh CA-signed CRL, optionally at an explicit path."""
        output = destination or self.root / "tsa-current.crl"
        self._run_openssl(
            "ca", "-batch", "-config", str(self.ca_config),
            "-gencrl", "-out", str(output),
        )
        return output


def issue_local_rfc3161_timestamp(data: bytes, root: Path) -> tuple[Path, Path, Path]:
    """Issue a response and return response, trusted CA, and TSA certificate paths."""
    tsa = LocalRfc3161TSA(root)
    response = tsa.issue(data)
    return response, tsa.ca_cert, tsa.tsa_cert
