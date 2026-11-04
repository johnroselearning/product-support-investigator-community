"""Common async/sync tool-call instrumentation; arguments and bodies are omitted."""
from contextlib import contextmanager
from functools import wraps
from inspect import iscoroutinefunction
from time import monotonic
from .logging import get_logger

log = get_logger('tool_executor')

def _result_count(result):
    if isinstance(result, (list, tuple)):
        return len(result)
    return getattr(result, 'result_count', None)

@contextmanager
def tool_call(tool, operation, *, server=None, reason='Adapter selected a bounded read-only evidence operation'):
    from .trace import current_trace
    recorder = current_trace()
    call = dict(tool=tool, operation=operation, server=server or tool, status='started',
                safe_argument_summary='Arguments omitted', reason=reason)
    started = monotonic()
    if recorder:
        recorder.consider(tool, reason)
        call.update(correlation_id=recorder.trace.correlation_id, investigation_id=recorder.trace.investigation_id)
        recorder.trace.tools_called.append(call)
        recorder.event('tool_call_started', **call)
    else:
        log.info('tool_call_started', extra=call)
    try:
        yield call
    except BaseException as error:
        code = getattr(error, 'status', None)
        safe_codes = ('authentication_failed', 'permission_denied', 'unavailable', 'rate_limited', 'query_error', 'invalid_response', 'response_too_large')
        call.update(status='failed', error_type=type(error).__name__, error_code=code if isinstance(code, int) or code in safe_codes else None)
        if recorder:
            recorder.trace.errors.append({'tool': tool, 'error_type': call['error_type'], 'error_code': call['error_code']})
        raise
    else:
        call['status'] = 'success'
    finally:
        call['duration_ms'] = round((monotonic()-started)*1000, 2)
        event = 'tool_call_failed' if call['status'] == 'failed' else 'tool_call_completed'
        if recorder:
            recorder.event(event, **call)
        else:
            log.info(event, extra=call)

def logged_tool_call(tool, operation=None, *, server=None, reason='Adapter selected a bounded read-only evidence operation'):
    def decorator(function):
        name = operation or function.__name__
        @wraps(function)
        async def async_wrapper(*args, **kwargs):
            with tool_call(tool, name, server=server, reason=reason) as call:
                result = await function(*args, **kwargs)
                call['result_count'] = _result_count(result)
                return result
        @wraps(function)
        def wrapper(*args, **kwargs):
            with tool_call(tool, name, server=server, reason=reason) as call:
                result = function(*args, **kwargs)
                call['result_count'] = _result_count(result)
                return result
        return async_wrapper if iscoroutinefunction(function) else wrapper
    return decorator
