"""Redact secrets and common personal data before they reach a log sink."""
import re
from collections.abc import Mapping

SECRET_KEY = re.compile(r"authorization|bearer|api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|passwd|secret|credential|cookie|private[_-]?key|github|jira", re.I)
PRIVATE_KEY = re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----.*?(?:-----END [^-]*PRIVATE KEY-----|$)", re.S)
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
BEARER = re.compile(r"(?i)\bBearer\s+[^\s,;]+")
HEADER = re.compile(r"(?im)\b(?:authorization|proxy-authorization|cookie|set-cookie)\s*[:=]\s*[^\s,;]+")
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)")
KEY_VALUE = re.compile(r'''(?ix)(["']?(?:password|passwd|secret|token|api[_-]?key|access[_-]?token|client[_-]?secret|credentials?)["']?\s*[:=]\s*)("[^"]*"|'[^']*'|[^\s,;}]+)''')


def redact(value, secrets=(), *, redact_pii=True):
    text = str(value)
    for secret in secrets:
        if secret:
            text = text.replace(str(secret), "[REDACTED_SECRET]")
    text = PRIVATE_KEY.sub("[REDACTED_SECRET]", text)
    text = BEARER.sub("Bearer [REDACTED_TOKEN]", text)
    text = JWT.sub("[REDACTED_TOKEN]", text)
    text = HEADER.sub("[REDACTED_SECRET]", text)
    text = KEY_VALUE.sub(r"\1[REDACTED_SECRET]", text)
    if redact_pii:
        text = EMAIL.sub("[REDACTED_EMAIL]", text)
        text = PHONE.sub("[REDACTED_PHONE]", text)
    return text


def redact_mapping(value, secrets=(), *, redact_pii=True, max_depth=8):
    if max_depth < 0:
        return "[REDACTED]"
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            safe_key = redact(key, secrets, redact_pii=redact_pii)
            result[safe_key] = "[REDACTED_SECRET]" if SECRET_KEY.search(str(key)) else redact_mapping(item, secrets, redact_pii=redact_pii, max_depth=max_depth - 1)
        return result
    if isinstance(value, (list, tuple)):
        return [redact_mapping(item, secrets, redact_pii=redact_pii, max_depth=max_depth - 1) for item in value]
    return redact(value, secrets, redact_pii=redact_pii) if isinstance(value, str) else value
