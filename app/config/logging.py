import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        for field in (
            "event",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "tool_name",
            "tool_calls",
            "tool_count",
            "source_count",
            "user_id",
            "planner_response",
            "planner_question",
            "history_count",
            "parsing_error",
            "raw_content",
            "raw_tool_calls",
            "raw_invalid_tool_calls",
            "raw_additional_kwargs",
            "raw_response",
            "response_metadata",
            "usage_metadata",
            "need_tool",
            "direct_answer",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    log_file = os.getenv("LOG_FILE", "logs/app.log")
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(file_handler)
