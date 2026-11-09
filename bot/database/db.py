import logging
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy import event, text, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings
from bot.database.models import Base, Category, TransactionType

logger = logging.getLogger(__name__)

# Ensure data directory exists
data_path = Path("data")
data_path.mkdir(exist_ok=True, parents=True)

engine = create_async_engine(
    settings.DB_URL,
    echo=False,
    future=True
)

# Enable WAL mode and foreign keys for SQLite
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

AsyncSessionFactory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session

DEFAULT_CATEGORIES = [
    # Расходы
    ("Продукты и супермаркеты", TransactionType.EXPENSE, "🛒"),
    ("Кафе, рестораны и доставка", TransactionType.EXPENSE, "🍽️"),
    ("Транспорт и такси", TransactionType.EXPENSE, "🚕"),
    ("Жилье и коммуналка", TransactionType.EXPENSE, "🏠"),
    ("Здоровье и аптеки", TransactionType.EXPENSE, "💊"),
    ("Одежда и обувь", TransactionType.EXPENSE, "👔"),
    ("Подписки и сервисы", TransactionType.EXPENSE, "📱"),
    ("Развлечения и отдых", TransactionType.EXPENSE, "🎉"),
    ("Путешествия", TransactionType.EXPENSE, "✈️"),
    ("Техника и гаджеты", TransactionType.EXPENSE, "💻"),
    ("Образование и книги", TransactionType.EXPENSE, "📚"),
    ("Прочие расходы", TransactionType.EXPENSE, "📦"),
    # Доходы
    ("Зарплата и аванс", TransactionType.INCOME, "💼"),
    ("Фриланс и подработка", TransactionType.INCOME, "💻"),
    ("Пассивный доход и вклады", TransactionType.PASSIVE_INCOME, "📈"),
    ("Подарки и прочее", TransactionType.INCOME, "🎁"),
]

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed default categories if empty
    async with AsyncSessionFactory() as session:
        stmt = select(Category).where(Category.user_id.is_(None))
        result = await session.execute(stmt)
        existing = result.scalars().all()
        if not existing:
            for name, c_type, icon in DEFAULT_CATEGORIES:
                session.add(Category(name=name, type=c_type, icon=icon, user_id=None))
            await session.commit()
            logger.info("Default categories seeded successfully.")

