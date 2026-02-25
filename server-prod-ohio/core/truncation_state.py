# -*- coding: utf-8 -*-

# Kiro Gateway
# https://github.com/jwadow/kiro-gateway
# Copyright (C) 2025 Jwadow
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
File-based cache for truncation recovery state.

Uses JSON files for cross-worker persistence (uvicorn --workers N).
Each truncation entry is stored as a separate file for atomic read/delete.

Tracks truncated tool calls and content by stable identifiers:
- Tool calls: tracked by tool_call_id (stable across requests)
- Content: tracked by hash of truncated assistant message (stable)
"""

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional

from loguru import logger


# Cache directory (relative to working directory, i.e. /opt/apollo/)
_CACHE_DIR = Path("_truncation_cache")


def _ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ToolTruncationInfo:
    tool_call_id: str
    tool_name: str
    truncation_info: Dict
    timestamp: float


@dataclass
class ContentTruncationInfo:
    message_hash: str
    content_preview: str
    timestamp: float


def save_tool_truncation(tool_call_id: str, tool_name: str, truncation_info: Dict) -> None:
    """Save truncation info for a tool call. File-based for cross-worker access."""
    try:
        _ensure_cache_dir()
        # Sanitize tool_call_id for filename
        safe_id = tool_call_id.replace("/", "_").replace("\\", "_")
        filepath = _CACHE_DIR / f"tool_{safe_id}.json"
        data = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "truncation_info": truncation_info,
            "timestamp": time.time(),
        }
        filepath.write_text(json.dumps(data), encoding="utf-8")
        logger.debug(f"Saved tool truncation for {tool_call_id} ({tool_name})")
    except Exception as e:
        logger.warning(f"Failed to save tool truncation: {e}")


def get_tool_truncation(tool_call_id: str) -> Optional[ToolTruncationInfo]:
    """Get and remove truncation info for a tool call. One-time retrieval."""
    try:
        safe_id = tool_call_id.replace("/", "_").replace("\\", "_")
        filepath = _CACHE_DIR / f"tool_{safe_id}.json"
        if not filepath.exists():
            return None
        data = json.loads(filepath.read_text(encoding="utf-8"))
        filepath.unlink(missing_ok=True)  # Delete after read
        logger.debug(f"Retrieved tool truncation for {tool_call_id}")
        return ToolTruncationInfo(
            tool_call_id=data["tool_call_id"],
            tool_name=data["tool_name"],
            truncation_info=data["truncation_info"],
            timestamp=data["timestamp"],
        )
    except Exception as e:
        logger.warning(f"Failed to get tool truncation: {e}")
        return None


def save_content_truncation(content: str) -> str:
    """Save truncation info for content. Returns hash for tracking."""
    content_for_hash = content[:500]
    message_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()[:16]
    try:
        _ensure_cache_dir()
        filepath = _CACHE_DIR / f"content_{message_hash}.json"
        data = {
            "message_hash": message_hash,
            "content_preview": content[:200],
            "timestamp": time.time(),
        }
        filepath.write_text(json.dumps(data), encoding="utf-8")
        logger.debug(f"Saved content truncation with hash {message_hash}")
    except Exception as e:
        logger.warning(f"Failed to save content truncation: {e}")
    return message_hash


def get_content_truncation(content: str) -> Optional[ContentTruncationInfo]:
    """Get and remove truncation info for content. One-time retrieval."""
    content_for_hash = content[:500]
    message_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()[:16]
    try:
        filepath = _CACHE_DIR / f"content_{message_hash}.json"
        if not filepath.exists():
            return None
        data = json.loads(filepath.read_text(encoding="utf-8"))
        filepath.unlink(missing_ok=True)  # Delete after read
        logger.debug(f"Retrieved content truncation for hash {message_hash}")
        return ContentTruncationInfo(
            message_hash=data["message_hash"],
            content_preview=data["content_preview"],
            timestamp=data["timestamp"],
        )
    except Exception as e:
        logger.warning(f"Failed to get content truncation: {e}")
        return None


def get_cache_stats() -> Dict[str, int]:
    """Get current cache statistics."""
    try:
        if not _CACHE_DIR.exists():
            return {"tool_truncations": 0, "content_truncations": 0, "total": 0}
        tool_count = len(list(_CACHE_DIR.glob("tool_*.json")))
        content_count = len(list(_CACHE_DIR.glob("content_*.json")))
        return {
            "tool_truncations": tool_count,
            "content_truncations": content_count,
            "total": tool_count + content_count,
        }
    except Exception:
        return {"tool_truncations": 0, "content_truncations": 0, "total": 0}
