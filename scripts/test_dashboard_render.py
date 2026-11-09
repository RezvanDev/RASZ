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
        
        buf = ChartService.generate_full_dashboard(stats, summary, "Ноябрь 2026")
        with open("/tmp/dashboard_test.png", "wb") as f_out:
            f_out.write(buf.getvalue())
        print("Dashboard generated successfully! Size:", len(buf.getvalue()), "bytes")
        
        html = ChartService.generate_interactive_html(stats, summary, "Ноябрь 2026")
        with open("/tmp/dashboard_test.html", "w", encoding="utf-8") as f_html:
            f_html.write(html)
        print("HTML dashboard generated! Length:", len(html), "chars")

asyncio.run(main())
