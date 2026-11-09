from datetime import datetime, date
from enum import Enum
from typing import Optional, List
from sqlalchemy import BigInteger, String, Float, Boolean, DateTime, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class AccountType(str, Enum):
    CASH = "CASH"                # Наличные
    CARD = "CARD"                # Дебетовая карта
    CREDIT_CARD = "CREDIT_CARD"  # Кредитная карта (с кредитным лимитом и задолженностью)
    DEPOSIT = "DEPOSIT"          # Банковский вклад / Накопительный счет (с процентами)
    INVEST = "INVEST"            # Брокерский счет / Акции / Облигации
    CRYPTO = "CRYPTO"            # Криптовалюта

class TransactionType(str, Enum):
    EXPENSE = "EXPENSE"               # Расход
    INCOME = "INCOME"                 # Доход (зарплата, подработка)
    TRANSFER = "TRANSFER"             # Перевод между своими счетами
    PASSIVE_INCOME = "PASSIVE_INCOME" # Начисленные проценты по вкладам / дивиденды

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="UZS")
    daily_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    accounts: Mapped[List["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    categories: Mapped[List["Category"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    goals: Mapped[List["Goal"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    account_type: Mapped[AccountType] = mapped_column(SQLEnum(AccountType), default=AccountType.CARD)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    interest_rate: Mapped[float] = mapped_column(Float, default=0.0)  # Годовая ставка (%)
    credit_limit: Mapped[float] = mapped_column(Float, default=0.0)   # Кредитный лимит (для кредиток)
    grace_period_days: Mapped[int] = mapped_column(default=0)          # Беспроцентный период (дней)
    currency: Mapped[str] = mapped_column(String(10), default="UZS")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_interest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="accounts")
    transactions: Mapped[List["Transaction"]] = relationship(
        back_populates="account",
        foreign_keys="[Transaction.account_id]"
    )

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), default=TransactionType.EXPENSE)
    icon: Mapped[str] = mapped_column(String(20), default="💳")
    monthly_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Месячный лимит расходов (в сумах)

    user: Mapped[Optional["User"]] = relationship(back_populates="categories")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="category")

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    to_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), default=TransactionType.EXPENSE)
    amount: Mapped[float] = mapped_column(Float)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped[Optional["Account"]] = relationship(
        back_populates="transactions",
        foreign_keys=[account_id]
    )
    to_account: Mapped[Optional["Account"]] = relationship(
        foreign_keys=[to_account_id]
    )
    category: Mapped[Optional["Category"]] = relationship(back_populates="transactions")

class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    target_amount: Mapped[float] = mapped_column(Float)
    current_amount: Mapped[float] = mapped_column(Float, default=0.0)
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="goals")

class DailyAccrualLog(Base):
    __tablename__ = "daily_accrual_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

