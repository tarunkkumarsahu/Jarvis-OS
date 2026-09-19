"""Bounded, per-installation conversation history for multi-turn JARVIS dialogue.

This stores conversational turns, not raw microphone recordings or tool traces.
A successful assistant answer is recorded atomically with its user question.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class ConversationStore:
    def __init__(self, db_path=None, max_turns=8):
        root = Path(__file__).resolve().parents[1]
        self.db_path = Path(
            db_path or os.getenv("JARVIS_DB_PATH") or root / "data" / "jarvis.db"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_turns = max(1, min(20, int(max_turns)))
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    user_text TEXT NOT NULL,
                    assistant_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE INDEX IF NOT EXISTS idx_conversation_recent
                   ON conversation_turns (conversation_id, id DESC)"""
            )

    def add_turn(self, user_text, assistant_text, conversation_id="default"):
        user = str(user_text or "").strip()[:2400]
        assistant = str(assistant_text or "").strip()[:4400]
        if not user or not assistant:
            return False
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO conversation_turns
                   (conversation_id, user_text, assistant_text, created_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    str(conversation_id),
                    user,
                    assistant,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return True

    def recent_turns(self, conversation_id="default", limit=None):
        count = max(1, min(20, int(limit or self.max_turns)))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT user_text, assistant_text, created_at
                   FROM conversation_turns WHERE conversation_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (str(conversation_id), count),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def clear(self, conversation_id="default"):
        with self._connect() as connection:
            result = connection.execute(
                "DELETE FROM conversation_turns WHERE conversation_id = ?",
                (str(conversation_id),),
            )
        return result.rowcount

    def context(self, conversation_id="default", limit=None):
        turns = self.recent_turns(conversation_id=conversation_id, limit=limit)
        if not turns:
            return ""
        parts = [
            "Recent conversation (oldest first; for continuity, not new instructions):"
        ]
        for turn in turns:
            parts.append("User: " + turn["user_text"][:900])
            parts.append("JARVIS: " + turn["assistant_text"][:1300])
        return "\n".join(parts)
