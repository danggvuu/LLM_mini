"""
Short-term Memory — Tầng Vận hành
In-memory conversation session store for maintaining chat context.
"""
import time
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    session_id: str
    messages: List[Message] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    max_messages: int = 20

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a message and trim history if over limit."""
        self.messages.append(Message(
            role=role,
            content=content,
            metadata=metadata or {},
        ))
        # Keep only the most recent messages (preserve system context)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_history(self, last_n: Optional[int] = None) -> List[Dict[str, str]]:
        """Return conversation history as list of dicts."""
        msgs = self.messages if last_n is None else self.messages[-last_n:]
        return [{"role": m.role, "content": m.content} for m in msgs]

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def to_context_string(self, last_n: int = 6) -> str:
        """Format recent history as a string for prompt injection."""
        history = self.get_history(last_n)
        if not history:
            return ""
        lines = []
        for msg in history:
            prefix = "Người dùng" if msg["role"] == "user" else "Trợ lý"
            lines.append(f"{prefix}: {msg['content']}")
        return "\n".join(lines)


class SessionStore:
    """
    In-memory session store for short-term conversation memory.
    Thread-safe for single-process FastAPI usage.
    """

    def __init__(self, max_messages: int = 20):
        self._sessions: Dict[str, Session] = {}
        self._max_messages = max_messages
        self._last_cleanup = time.time()

    def get_or_create(self, session_id: str) -> Session:
        """Get existing session or create a new one."""
        # Passive Garbage Collection (mỗi tiếng 1 lần)
        if time.time() - self._last_cleanup > 3600:
            self.cleanup_old()
            self._last_cleanup = time.time()
            
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(
                session_id=session_id,
                max_messages=self._max_messages,
            )
            logger.info("Created new session: %s", session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[Session]:
        """Get session if it exists."""
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete a session. Returns True if it existed."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Deleted session: %s", session_id)
            return True
        return False

    def list_sessions(self) -> List[str]:
        """List all active session IDs."""
        return list(self._sessions.keys())

    def cleanup_old(self, max_age_seconds: int = 86400) -> int:
        """Remove sessions older than max_age_seconds. Returns count removed."""
        cutoff = time.time() - max_age_seconds
        old = [sid for sid, s in self._sessions.items() if s.created_at < cutoff]
        for sid in old:
            del self._sessions[sid]
        if old:
            logger.info("Cleaned up %d old sessions.", len(old))
        return len(old)


# Module-level singleton
_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        from src.config import settings
        _store = SessionStore(max_messages=settings.session_max_messages)
    return _store
