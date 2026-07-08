import json
from typing import Any, Dict, Optional
from datetime import datetime

from sqlalchemy import create_engine, String, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column, scoped_session

from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.fsm.state import State

engine = create_engine("sqlite:///store.db", echo=False)  # echo=True prints SQL, great for learning
SessionLocal = sessionmaker(bind=engine)
Session = scoped_session(SessionLocal)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[str] = mapped_column(unique=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True)
    barcode: Mapped[str] = mapped_column(unique=True)
    cashback_balance: Mapped[float] = mapped_column(default=0.0)
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    purchase_amount: Mapped[float]
    cashback_earned: Mapped[float]
    admin_id: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class FSMRecord(Base):
    """One row per Telegram chat/user the FSM has touched.

    Replaces aiogram's in-memory FSM storage so state + data survive a worker
    process being recycled (which Passenger does on shared hosting when the
    app sits idle), instead of silently reverting to None mid-conversation.
    """

    __tablename__ = "fsm_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int]
    chat_id: Mapped[int]
    user_id: Mapped[int]
    thread_id: Mapped[Optional[int]]
    destiny: Mapped[str] = mapped_column(default="default")
    state: Mapped[Optional[str]]
    data: Mapped[Optional[str]]  # JSON-encoded dict, e.g. {"user": 5}

    __table_args__ = (
        UniqueConstraint("bot_id", "chat_id", "user_id", "thread_id", "destiny", name="uq_fsm_key"),
    )


def _key_filter(key: StorageKey) -> dict:
    return {
        "bot_id": key.bot_id,
        "chat_id": key.chat_id,
        "user_id": key.user_id,
        "thread_id": getattr(key, "thread_id", None),
        "destiny": getattr(key, "destiny", "default"),
    }


class SQLiteStorage(BaseStorage):
    """Persists FSM state + data into store.db instead of process memory."""

    async def set_state(self, key: StorageKey, state=None) -> None:
        state_str = state.state if isinstance(state, State) else state
        with SessionLocal() as session:
            record = session.query(FSMRecord).filter_by(**_key_filter(key)).first()
            if record is None:
                record = FSMRecord(**_key_filter(key))
                session.add(record)
            record.state = state_str
            session.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        with SessionLocal() as session:
            record = session.query(FSMRecord).filter_by(**_key_filter(key)).first()
            return record.state if record else None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        with SessionLocal() as session:
            record = session.query(FSMRecord).filter_by(**_key_filter(key)).first()
            if record is None:
                record = FSMRecord(**_key_filter(key))
                session.add(record)
            record.data = json.dumps(data)
            session.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        with SessionLocal() as session:
            record = session.query(FSMRecord).filter_by(**_key_filter(key)).first()
            if record is None or not record.data:
                return {}
            return json.loads(record.data)

    async def close(self) -> None:
        pass


# Idempotent — only creates tables that don't already exist yet (e.g. fsm_states
# on first deploy of this change). Safe to leave uncommented and run on every
# start, which matters here since there's no separate migration step available.
Base.metadata.create_all(engine)


if __name__ == "__main__":
    print('Deploy')