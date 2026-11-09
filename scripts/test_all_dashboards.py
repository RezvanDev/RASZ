import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib
matplotlib.use("Agg")
import asyncio
from datetime import datetime
from bot.database.db import AsyncSessionFactory
from bot.services.finance_service import FinanceService

async def main():
    async with AsyncSessionFactory() as session:
        f = FinanceService(session)
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)
        stats = await f.get_financial_stats(6934303640, start, now)
        summary = await f.get_net_worth_summary(6934303640)
        print("Ready to implement specialized dashboards!")

asyncio.run(main())
