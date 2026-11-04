"""Async-safe investigation context using contextvars."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from uuid import uuid4
from functools import wraps
import inspect


@dataclass(frozen=True)
class InvestigationContext:
    correlation_id: str
    investigation_id: str | None = None
    trace_id: str | None = None
    request_type: str | None = None
    issue_key: str | None = None
    actor_type: str | None = None

    @classmethod
    def create(cls, **values):
        return cls(correlation_id=values.pop("correlation_id", None) or f"corr-{uuid4().hex}", **values)

    def as_dict(self):
        return {key: value for key, value in asdict(self).items() if value is not None}


_current: ContextVar[InvestigationContext | None] = ContextVar("psi_investigation_context", default=None)


def get_context():
    return _current.get()


@contextmanager
def investigation_context(context: InvestigationContext | None = None, **values):
    token = _current.set(context or InvestigationContext.create(**values))
    try:
        yield _current.get()
    finally:
        _current.reset(token)


def ensure_investigation_context(function):
    """Give standalone provider/tool calls a context without replacing a parent context."""
    @wraps(function)
    async def async_wrapper(*args, **kwargs):
        if get_context() is not None:
            return await function(*args, **kwargs)
        with investigation_context():
            return await function(*args, **kwargs)

    @wraps(function)
    def sync_wrapper(*args, **kwargs):
        if get_context() is not None:
            return function(*args, **kwargs)
        with investigation_context():
            return function(*args, **kwargs)

    return async_wrapper if inspect.iscoroutinefunction(function) else sync_wrapper
