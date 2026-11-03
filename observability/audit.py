"""Security-relevant audit events, kept separate from application logs."""
from .config import ObservabilityConfig
from .logging import get_logger

log = get_logger("audit")


def audit_event(event, *, operation=None, tool=None, status="recorded", **fields):
    if not ObservabilityConfig.from_env().enable_audit_log:
        return
    log.info(event, extra={"log_type": "audit", "component": "audit", "operation": operation or event, "tool": tool, "status": status, **fields})
