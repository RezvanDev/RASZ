import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib
matplotlib.use("Agg")
import asyncio
from datetime import datetime
from bot.database.db import AsyncSessionFactory
from bot.services.finance_service import FinanceService
from bot.services.chart_service import ChartService

async def main():
    async with AsyncSessionFactory() as session:
        f = FinanceService(session)
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)
        stats = await f.get_financial_stats(6934303640, start, now)
        summary = await f.get_net_worth_summary(6934303640)
        
        # Test all specialized dashboards
        for dtype in ["GENERAL", "INCOME", "EXPENSE", "DEBTS"]:
            buf, title = ChartService.generate_specialized_dashboard(dtype, stats, summary, "Ноябрь 2026")
            print(f"Generated {dtype}: {title}, size={len(buf.getvalue())} bytes")

asyncio.run(main())
