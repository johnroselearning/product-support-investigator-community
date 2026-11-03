"""Common async/sync tool-call instrumentation."""
from functools import wraps
from time import monotonic
from .logging import get_logger

log = get_logger("tool_executor")


def _result_count(result):
    if isinstance(result, (list, tuple, dict)):
        return len(result)
    return getattr(result, "result_count", None)


def logged_tool_call(tool, operation=None):
    def decorator(function):
        name = operation or function.__name__
        if getattr(function, "__code__", None) and function.__code__.co_flags & 0x80:
            @wraps(function)
            async def async_wrapper(*args, **kwargs):
                return await _run(function, args, kwargs, tool, name, True)
            return async_wrapper
        @wraps(function)
        def wrapper(*args, **kwargs):
            return _run_sync(function, args, kwargs, tool, name)
        return wrapper
    return decorator


async def _run(function, args, kwargs, tool, operation, is_async):
    started = monotonic(); log.info("tool_call_started", extra={"component": "tool_executor", "operation": operation, "tool": tool, "status": "started"})
    try:
        result = await function(*args, **kwargs)
        log.info("tool_call_completed", extra={"component": "tool_executor", "operation": operation, "tool": tool, "status": "success", "duration_ms": round((monotonic()-started)*1000, 2), "result_count": _result_count(result)})
        return result
    except Exception as error:
        log.error("tool_call_failed", extra={"component": "tool_executor", "operation": operation, "tool": tool, "status": "failure", "duration_ms": round((monotonic()-started)*1000, 2), "error_type": type(error).__name__})
        raise


def _run_sync(function, args, kwargs, tool, operation):
    started = monotonic(); log.info("tool_call_started", extra={"component": "tool_executor", "operation": operation, "tool": tool, "status": "started"})
    try:
        result = function(*args, **kwargs)
        log.info("tool_call_completed", extra={"component": "tool_executor", "operation": operation, "tool": tool, "status": "success", "duration_ms": round((monotonic()-started)*1000, 2), "result_count": _result_count(result)})
        return result
    except Exception as error:
        log.error("tool_call_failed", extra={"component": "tool_executor", "operation": operation, "tool": tool, "status": "failure", "duration_ms": round((monotonic()-started)*1000, 2), "error_type": type(error).__name__})
        raise
