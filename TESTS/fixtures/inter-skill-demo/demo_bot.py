"""Synthetic fixture only. Never execute this file.

The intentionally unsafe logging pattern is a code-audit finding.
"""
import logging
import os


def report_status() -> None:
    # Deliberately unsafe: exposes the configured credential in application logs.
    logging.info("Exchange credential: %s", os.environ.get("EXCHANGE_API_KEY", ""))


if __name__ == "__main__":
    report_status()
