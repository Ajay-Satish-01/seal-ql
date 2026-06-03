"""Postgres-backed persistent chat session store (seal_app schema)."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from seal_core.chat.models import ChatMessage
from seal_core.chat.session.base import BaseSessionStore
from seal_core.chat.session.ids import parse_session_id
from seal_core.chat.session.listing import SessionListPage
from seal_core.chat.session.models import SessionState, SessionSummary

logger = logging.getLogger(__name__)


def _ts_to_float(value: datetime) -> float:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).timestamp()
    return value.timestamp()


class PostgresSessionStore(BaseSessionStore):
    """Persistent chat sessions in seal_app (same DATABASE_URL as workspace)."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        self._pool: Any = None
        self._pool_lock = asyncio.Lock()

    async def _pool_get(self) -> Any:
        if self._pool is not None:
            return self._pool
        async with self._pool_lock:
            if self._pool is None:
                import asyncpg

                self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=3)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @staticmethod
    def _find_migration() -> Path | None:
        """Walk ancestors looking for ``scripts/migrate_chat_sessions.sql``."""
        cursor = Path(__file__).resolve().parent
        for _ in range(10):
            candidate = cursor / "scripts" / "migrate_chat_sessions.sql"
            if candidate.is_file():
                return candidate
            parent = cursor.parent
            if parent == cursor:
                break
            cursor = parent
        return None

    async def ensure_schema(self) -> None:
        migrate_path = self._find_migration()
        if migrate_path is None:
            logger.warning(
                "Chat session migration not found — "
                "run scripts/migrate_chat_sessions.sql manually or set CHAT_SESSION_STORE=memory",
            )
            return
        pool = await self._pool_get()
        sql = migrate_path.read_text(encoding="utf-8")
        async with pool.acquire() as conn:
            await conn.execute(sql)
        logger.info("Applied chat session schema from %s", migrate_path)

    async def create_session(self) -> str:
        """Return a new session id; row is created on first append."""
        return str(uuid.uuid4())

    async def _load_session_row(self, conn: Any, session_id: str) -> SessionState | None:
        row = await conn.fetchrow(
            """
            SELECT session_id, title, database_id, summary, summary_through_index,
                   created_at, updated_at
            FROM seal_app.chat_sessions
            WHERE session_id = $1::uuid
            """,
            session_id,
        )
        if row is None:
            return None
        msg_rows = await conn.fetch(
            """
            SELECT role, content, created_at
            FROM seal_app.chat_messages
            WHERE session_id = $1::uuid
            ORDER BY created_at ASC, id ASC
            """,
            session_id,
        )
        messages = [ChatMessage(role=r["role"], content=r["content"]) for r in msg_rows]
        message_timestamps = [_ts_to_float(r["created_at"]) for r in msg_rows]
        return SessionState(
            messages=messages,
            message_timestamps=message_timestamps,
            summary=row["summary"],
            summary_through_index=row["summary_through_index"] or 0,
            database_id=row["database_id"],
            title=row["title"],
            created_at=_ts_to_float(row["created_at"]),
            updated_at=_ts_to_float(row["updated_at"]),
        )

    async def get_or_create(self, session_id: str | None) -> tuple[str, SessionState]:
        if session_id is not None:
            sid = parse_session_id(session_id)
            pool = await self._pool_get()
            async with pool.acquire() as conn:
                state = await self._load_session_row(conn, sid)
                if state is not None:
                    return sid, state
            return sid, SessionState(created_at=time.time(), updated_at=time.time())
        return await self.create_session(), SessionState(
            created_at=time.time(), updated_at=time.time()
        )

    async def append(self, session_id: str, message: ChatMessage) -> None:
        self._validate_message_role(message)
        sid = parse_session_id(session_id)
        pool = await self._pool_get()
        now = datetime.now(UTC)
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute(
                """
                INSERT INTO seal_app.chat_sessions (
                    session_id, title, database_id, summary, summary_through_index,
                    created_at, updated_at
                )
                VALUES ($1::uuid, NULL, NULL, NULL, 0, $2, $2)
                ON CONFLICT (session_id) DO NOTHING
                """,
                sid,
                now,
            )

            await conn.execute(
                """
                INSERT INTO seal_app.chat_messages (session_id, role, content, created_at)
                VALUES ($1::uuid, $2, $3, $4)
                """,
                sid,
                message.role,
                message.content,
                now,
            )

            if message.role == "user":
                await conn.execute(
                    """
                    UPDATE seal_app.chat_sessions
                    SET updated_at = $2,
                        title = COALESCE(title, LEFT($3, 80))
                    WHERE session_id = $1::uuid
                    """,
                    sid,
                    now,
                    message.content,
                )
            else:
                await conn.execute(
                    """
                    UPDATE seal_app.chat_sessions SET updated_at = $2
                    WHERE session_id = $1::uuid
                    """,
                    sid,
                    now,
                )

            max_msgs = self._max_messages()
            await conn.execute(
                """
                DELETE FROM seal_app.chat_messages
                WHERE id IN (
                    SELECT id FROM seal_app.chat_messages
                    WHERE session_id = $1::uuid
                    ORDER BY created_at DESC, id DESC
                    OFFSET $2
                )
                """,
                sid,
                max_msgs,
            )

    async def list_sessions(
        self,
        database_id: str | None = None,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> SessionListPage:
        page_size = self._list_limit(limit)
        pool = await self._pool_get()
        query = """
            SELECT s.session_id, s.title, s.database_id, s.created_at, s.updated_at,
                   COUNT(m.id)::int AS message_count
            FROM seal_app.chat_sessions s
            INNER JOIN seal_app.chat_messages m ON m.session_id = s.session_id
        """
        params: list[Any] = []
        if database_id is not None:
            query += " WHERE (s.database_id IS NULL OR s.database_id = $1)"
            params.append(database_id)
        limit_idx = len(params) + 1
        offset_idx = len(params) + 2
        query += f"""
            GROUP BY s.session_id, s.title, s.database_id, s.created_at, s.updated_at
            ORDER BY s.updated_at DESC
            LIMIT ${limit_idx} OFFSET ${offset_idx}
        """
        params.extend([page_size + 1, max(offset, 0)])

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        has_more = len(rows) > page_size
        rows = rows[:page_size]
        sessions = [
            SessionSummary(
                session_id=str(r["session_id"]),
                title=r["title"],
                database_id=r["database_id"],
                message_count=r["message_count"] or 0,
                created_at=_ts_to_float(r["created_at"]),
                updated_at=_ts_to_float(r["updated_at"]),
            )
            for r in rows
        ]
        return SessionListPage(sessions=sessions, has_more=has_more)

    async def get_session(self, session_id: str) -> SessionState | None:
        sid = parse_session_id(session_id)
        pool = await self._pool_get()
        async with pool.acquire() as conn:
            return await self._load_session_row(conn, sid)

    async def delete_session(self, session_id: str) -> bool:
        sid = parse_session_id(session_id)
        pool = await self._pool_get()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM seal_app.chat_sessions WHERE session_id = $1::uuid",
                sid,
            )
        return result == "DELETE 1"

    async def _set_session_database_id(self, session_id: str, database_id: str) -> None:
        pool = await self._pool_get()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE seal_app.chat_sessions
                SET database_id = $2, updated_at = NOW()
                WHERE session_id = $1::uuid AND database_id IS NULL
                """,
                uuid.UUID(session_id),
                database_id,
            )
