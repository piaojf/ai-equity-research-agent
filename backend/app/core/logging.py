import json
import logging
import sys


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        fields = {
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        request_id = getattr(record, "request_id", None)
        if request_id is not None:
            fields["request_id"] = request_id
        for field_name in (
            "method",
            "path",
            "status_code",
            "latency_ms",
            "ticker",
            "provider",
            "operation",
            "status",
            "error_code",
        ):
            value = getattr(record, field_name, None)
            if value is not None:
                fields[field_name] = value
        return json.dumps(fields, ensure_ascii=False, separators=(",", ":"))


def configure_logging(log_level: str) -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
