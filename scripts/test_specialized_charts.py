import asyncio
from datetime import datetime
from bot.database.db import init_db, AsyncSessionFactory
from bot.services.finance_service import FinanceService

async def main():
    await init_db()
    async with AsyncSessionFactory() as session:
        finance = FinanceService(session)
        user_id = 6934303640
        now = datetime.utcnow()
        start_date = datetime(now.year, now.month, 1)
        stats = await finance.get_financial_stats(user_id, start_date, now)
        summary = await finance.get_net_worth_summary(user_id)
        print("Stats:", stats)
        print("Summary keys:", summary.keys())

if __name__ == "__main__":
    asyncio.run(main())

