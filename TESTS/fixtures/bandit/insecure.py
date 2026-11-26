"""Intentionally unsafe source for Bandit static-scanner tests. Never execute."""
import pickle
import subprocess


def unsafe_deserialize(payload: bytes):
    return pickle.loads(payload)


def unsafe_shell_command(user_value: str):
    return subprocess.Popen("echo " + user_value, shell=True)
