import asyncio
from bot.database.db import init_db, AsyncSessionFactory
from bot.services.finance_service import FinanceService
from bot.services.ai_service import AIService

async def test_prompts():
    await init_db()
    ai = AIService()
    user_id = 6934303640

    test_queries = [
        "Сделай дашборд дохода",
        "Сделай дашборд за месяц по категориям",
        "Сделай дашборд по долгам"
    ]

    async with AsyncSessionFactory() as session:
        finance = FinanceService(session)
        for q in test_queries:
            print(f"\n--- Testing Query: '{q}' ---")
            res = await ai.process_user_input(
                finance=finance,
                user_id=user_id,
                user_message=q,
                conversation_history=[]
            )
            print("Actions returned:", res.get("actions"))
            print("Response text excerpt:", res.get("text")[:150])

if __name__ == "__main__":
    asyncio.run(test_prompts())

