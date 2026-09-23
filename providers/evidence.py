"""Vendor-neutral evidence envelopes and bounded, best-effort sanitization."""
import re
from typing import Protocol
from datetime import datetime, timezone

class EvidenceProvider(Protocol):
    """Acquisition interface shared by local providers and platform bridges."""

    def retrieve(self, request: dict) -> dict:
        """Return a normalized envelope; never classify application root cause."""
        ...


MAX_OBSERVATIONS = 100
MAX_TEXT = 2000
MAX_LABELS = 20
SENSITIVE = re.compile(r'authorization|cookie|password|passwd|secret|token|api[_-]?key|credential|signature', re.I)


def redact(text, secrets=()):
    text = str(text)
    for secret in secrets:
        if secret:
            text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?(?:-----END [^-]*PRIVATE KEY-----|$)', '[REDACTED]', text, flags=re.S)
    text = re.sub(r'(?i)\b(?:authorization|cookie|set-cookie)\s*[=:]\s*[^\r\n]+', '[REDACTED HEADER]', text)
    text = re.sub(r'''(?ix)(["']?(?:password|passwd|secret|token|access_token|api[_-]?key|credentials?)["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,;}]+)''', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)\bBearer\s+\S+', 'Bearer [REDACTED]', text)
    text = re.sub(r'https?://[^\s"<>]+', lambda m: m[0].split('?')[0].split('#')[0] + ('?[REDACTED]' if '?' in m[0] or '#' in m[0] else ''), text)
    text = re.sub(r'(https?://)[^/\s@]+@', r'\1[REDACTED]@', text)
    return text


def sanitize(value, secrets=(), limitations=None, depth=0):
    """Redact before truncation; bounds apply to all model-visible metadata too."""
    limitations = limitations if limitations is not None else []
    def limited():
        if 'Output truncated; retained observations are incomplete.' not in limitations:
            limitations.append('Output truncated; retained observations are incomplete.')
    if depth > 8:
        limited()
        return '[TRUNCATED]'
    if isinstance(value, dict):
        if len(value) > MAX_LABELS:
            limited()
        return {redact(k, secrets)[:200]: '[REDACTED]' if SENSITIVE.search(str(k)) else sanitize(v, secrets, limitations, depth + 1)
                for k, v in list(value.items())[:MAX_LABELS]}
    if isinstance(value, list):
        if len(value) > MAX_OBSERVATIONS:
            limited()
        return [sanitize(v, secrets, limitations, depth + 1) for v in value[:MAX_OBSERVATIONS]]
    if isinstance(value, str):
        clean = redact(value, secrets)
        if len(clean) > MAX_TEXT:
            limited()
            return clean[:MAX_TEXT] + '[TRUNCATED]'
        return clean
    return value


def envelope(provider, request):
    return {
        'schema_version': '1', 'provider': provider,
        'evidence_id': request.get('evidence_id'),
        'source_type': request.get('operation', 'unknown'),
        'query_purpose': request.get('purpose'),
        'query_scope': request.get('scope', {}),
        'identifiers': request.get('identifiers', {}),
        'provenance': {}, 'observations': [],
        'retrieval_status': 'unavailable',
        'retrieved_at': datetime.now(timezone.utc).isoformat(),
        'read_only': True, 'trust': 'untrusted_data', 'limitations': [],
    }


def finalize(result, secrets=()):
    limits = list(result['limitations'])
    result = sanitize(result, secrets, limits)
    result['limitations'] = limits
    return result
