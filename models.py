from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, func, ForeignKey
from datetime import datetime

engine = create_engine("sqlite:///store.db", echo=False)  # echo=True prints SQL, great for learning
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[str] = mapped_column(unique=True)
    phone_number: Mapped[str] = mapped_column(String(20),unique=True)
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

# Base.metadata.create_all(engine)

if __name__ == "__main__":
    print('Deploy')