import asyncio
import shutil
from pathlib import Path
from bot.database.db import init_db, engine
from bot.database.models import Base

async def reset_database():
    db_file = Path("data/finance.db")
    backup_file = Path("data/finance_backup_pre_deploy.db")

    if db_file.exists():
        print(f"📦 Создаю резервную копию текущей БД -> {backup_file}...")
        shutil.copy2(db_file, backup_file)

    print("🗑 Очищаю старые файлы БД и тестовые дашборды...")
    # Close connections
    await engine.dispose()

    # Remove db files
    for p in Path("data").glob("finance.db*"):
        try:
            p.unlink()
            print(f"  Удален: {p.name}")
        except Exception as e:
            print(f"  Не удалось удалить {p.name}: {e}")

    # Remove temporary test png/html files
    for tmp_file in Path("data").glob("*_test.*"):
        tmp_file.unlink(missing_ok=True)
    for tmp_html in Path("data").glob("test_*.html"):
        tmp_html.unlink(missing_ok=True)

    print("🌱 Инициализирую чистую базу данных со всеми таблицами и дефолтными категориями...")
    await init_db()
    print("✅ База данных полностью очищена и готова к развертыванию на боевом сервере!")

if __name__ == "__main__":
    asyncio.run(reset_database())

