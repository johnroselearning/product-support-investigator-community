"""Environment-backed observability configuration with safe defaults."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ObservabilityConfig:
    level: str = "INFO"
    log_format: str = "json"
    destination: str = "stdout"
    environment: str = "local"
    redact_sensitive_data: bool = True
    enable_audit_log: bool = True
    log_raw_evidence: bool = False
    log_file: str | None = None
    loki_url: str | None = None
    service: str = "product-support-investigator"

    @classmethod
    def from_env(cls):
        def boolean(name, default):
            value = os.getenv(name)
            return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}

        return cls(
            level=os.getenv("PSI_LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("PSI_LOG_FORMAT", "json").lower(),
            destination=os.getenv("PSI_LOG_DESTINATION", "stdout").lower(),
            environment=os.getenv("PSI_ENVIRONMENT", "local"),
            redact_sensitive_data=boolean("PSI_REDACT_SENSITIVE_DATA", True),
            enable_audit_log=boolean("PSI_ENABLE_AUDIT_LOG", True),
            log_raw_evidence=boolean("PSI_LOG_RAW_EVIDENCE", False),
            log_file=os.getenv("PSI_LOG_FILE"),
            loki_url=os.getenv("PSI_LOKI_URL"),
        )
