# -*- coding: utf-8 -*-
"""
Debug logging module for requests.

Supports modes:
- off: logging disabled
- errors: logs are saved only on errors
- all: logs are saved for every request
- trace:<username>: logs are saved for EVERY request from <username>,
  each request gets its own timestamped folder under trace_logs/<username>/

The trace mode saves all data flows per request:
1. request_body.json — Cursor -> Gateway (raw)
2. kiro_request_body.json — Gateway -> Kiro (processed)
3. response_stream_raw.bin — Kiro -> Gateway (raw binary)
4. response_stream_modified.txt — Gateway -> Cursor (processed SSE)
5. app_logs.txt — application logs during this request
6. error_info.json — error details (if any)

IMPORTANT: Uses contextvars.ContextVar for per-request isolation in asyncio.
threading.local() does NOT work in single-thread asyncio because all coroutines
share the same thread — concurrent requests would overwrite each other's context.
ContextVar is properly isolated per asyncio Task.
"""

import contextvars
import io
import json
import shutil
import time
import threading
from pathlib import Path
from typing import Optional
from loguru import logger

from core.config import DEBUG_MODE, DEBUG_DIR


def _get_trace_username() -> Optional[str]:
    """If DEBUG_MODE is 'trace:<username>', return the username. Else None."""
    if DEBUG_MODE and DEBUG_MODE.startswith("trace:"):
        return DEBUG_MODE[6:].strip()
    return None


class DebugContext:
    """Per-request debug context. Each request gets its own instance."""

    def __init__(self, request_dir: Path):
        self.dir = request_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self._app_logs = io.StringIO()
        self._loguru_sink_id: Optional[int] = None
        self._setup_app_logs()

    def _setup_app_logs(self):
        self._loguru_sink_id = logger.add(
            self._app_logs,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="DEBUG",
            colorize=False,
        )

    def log_request_body(self, body: bytes):
        self._write_json(self.dir / "request_body.json", body)

    def log_kiro_request_body(self, body: bytes):
        self._write_json(self.dir / "kiro_request_body.json", body)

    def log_raw_chunk(self, chunk: bytes):
        try:
            with open(self.dir / "response_stream_raw.bin", "ab") as f:
                f.write(chunk)
        except Exception:
            pass

    def log_modified_chunk(self, chunk: bytes):
        try:
            with open(self.dir / "response_stream_modified.txt", "ab") as f:
                f.write(chunk)
        except Exception:
            pass

    def log_final_chunk(self, chunk: bytes):
        """Log the final chunk actually sent to Cursor (after proxy post-processing)."""
        try:
            with open(self.dir / "response_final_to_cursor.txt", "ab") as f:
                f.write(chunk)
        except Exception:
            pass

    def log_error_info(self, status_code: int, error_message: str = ""):
        try:
            with open(self.dir / "error_info.json", "w", encoding="utf-8") as f:
                json.dump({"status_code": status_code, "error_message": error_message}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def flush_on_error(self, status_code: int, error_message: str = ""):
        self.log_error_info(status_code, error_message)
        self._write_app_logs()

    def finish(self):
        """Called when request completes (success or error). Writes app logs and cleans up."""
        self._write_app_logs()
        self._cleanup_sink()

    def _write_json(self, path: Path, body: bytes):
        try:
            json_obj = json.loads(body)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(json_obj, f, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, Exception):
            try:
                with open(path, "wb") as f:
                    f.write(body)
            except Exception:
                pass

    def _write_app_logs(self):
        try:
            content = self._app_logs.getvalue()
            if content.strip():
                with open(self.dir / "app_logs.txt", "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception:
            pass

    def _cleanup_sink(self):
        if self._loguru_sink_id is not None:
            try:
                logger.remove(self._loguru_sink_id)
            except ValueError:
                pass
            self._loguru_sink_id = None


# ContextVar for per-request isolation in asyncio
_current_debug_ctx: contextvars.ContextVar[Optional[DebugContext]] = contextvars.ContextVar(
    '_current_debug_ctx', default=None
)


class DebugLogger:
    """
    Factory that creates per-request DebugContext instances.

    Uses contextvars.ContextVar to store the current request's context,
    so concurrent async requests don't interfere with each other.
    (threading.local() doesn't work in single-thread asyncio — all coroutines
    share the same thread, so prepare_new_request() from request B would
    overwrite request A's context while A is still streaming.)
    """

    def __init__(self):
        self.debug_dir = Path(DEBUG_DIR)
        self._seq_lock = threading.Lock()
        self._request_seq = 0

    @property
    def _ctx(self) -> Optional[DebugContext]:
        return _current_debug_ctx.get()

    @_ctx.setter
    def _ctx(self, value):
        _current_debug_ctx.set(value)

    # ==================== Mode checks ====================

    def _is_enabled(self) -> bool:
        return DEBUG_MODE in ("errors", "all") or _get_trace_username() is not None

    # ==================== Public API ====================

    def prepare_new_request(self, username: str = ""):
        """Prepare for a new request. Creates a per-request DebugContext."""
        trace_user = _get_trace_username()

        # Trace mode: only trace the specified user
        if trace_user:
            if username != trace_user:
                self._ctx = None
                return
            with self._seq_lock:
                self._request_seq += 1
                seq = self._request_seq
            ts = time.strftime("%H%M%S", time.localtime())
            dir_name = "req_%s_%03d" % (ts, seq)
            req_dir = Path("trace_logs") / trace_user / dir_name
            self._ctx = DebugContext(req_dir)
            logger.info("[DebugLogger] Trace: saving to %s" % req_dir)
            return

        # all mode
        if DEBUG_MODE == "all":
            try:
                if self.debug_dir.exists():
                    shutil.rmtree(self.debug_dir)
            except Exception:
                pass
            self._ctx = DebugContext(self.debug_dir)
            return

        # errors mode: create context but don't write until error
        if DEBUG_MODE == "errors":
            self._ctx = DebugContext(self.debug_dir)
            return

        self._ctx = None

    def log_request_body(self, body: bytes):
        if self._ctx:
            self._ctx.log_request_body(body)

    def log_kiro_request_body(self, body: bytes):
        if self._ctx:
            self._ctx.log_kiro_request_body(body)

    def log_raw_chunk(self, chunk: bytes):
        if self._ctx:
            self._ctx.log_raw_chunk(chunk)

    def log_modified_chunk(self, chunk: bytes):
        if self._ctx:
            self._ctx.log_modified_chunk(chunk)

    def log_final_chunk(self, chunk: bytes):
        if self._ctx:
            self._ctx.log_final_chunk(chunk)

    def log_error_info(self, status_code: int, error_message: str = ""):
        if self._ctx:
            self._ctx.log_error_info(status_code, error_message)

    def flush_on_error(self, status_code: int, error_message: str = ""):
        if self._ctx:
            self._ctx.flush_on_error(status_code, error_message)

    def discard_buffers(self):
        """Called when request completes successfully. Writes app logs."""
        if self._ctx:
            self._ctx.finish()
            self._ctx = None


# Global instance
debug_logger = DebugLogger()
