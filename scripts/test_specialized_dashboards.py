import asyncio
from datetime import datetime
from bot.database.db import AsyncSessionFactory
from bot.services.finance_service import FinanceService

async def check():
    async with AsyncSessionFactory() as session:
        f = FinanceService(session)
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)
        stats = await f.get_financial_stats(6934303640, start, now)
        summary = await f.get_net_worth_summary(6934303640)
        print("Data ready:", stats['full_income'], summary['total_debt'])

asyncio.run(check())
