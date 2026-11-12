"""Hide secret values in text shown to the learner."""
from __future__ import annotations


def redact(text: str, secrets: tuple[str, ...]) -> str:
    out = text
    for secret in secrets:
        if secret:
            out = out.replace(secret, "***")
    return out
