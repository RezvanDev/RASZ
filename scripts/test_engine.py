import asyncio
from datetime import datetime, date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from bot.database.models import Base, AccountType, TransactionType
from bot.services.finance_service import FinanceService
from bot.services.currency_service import CurrencyService
from bot.services.chart_service import ChartService

async def run_tests():
    print("🚀 [TEST] Запуск комплексного тестирования финансового ядра (Узбекистан)...")
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as session:
        service = FinanceService(session)

        # 1. Создание пользователя
        user = await service.get_or_create_user(telegram_id=77777, full_name="Анвар Тестов")
        print(f"✅ 1. Пользователь создан: {user.full_name} (Валюта: {user.currency})")

        # 2. Создание счетов в Узбекистане: Uzcard, Вклад Капиталбанк (22%), Рассрочка Uzum Nasiya
        card = await service.create_or_update_account(
            user_id=user.id,
            name="Карта Uzcard",
            account_type=AccountType.CARD,
            balance=15000000.0
        )
        deposit = await service.create_or_update_account(
            user_id=user.id,
            name="Вклад Капиталбанк",
            account_type=AccountType.DEPOSIT,
            balance=50000000.0,
            interest_rate=22.0
        )
        nasiya = await service.create_or_update_account(
            user_id=user.id,
            name="Рассрочка Uzum Nasiya",
            account_type=AccountType.CREDIT_CARD,
            balance=0.0,
            credit_limit=20000000.0,
            grace_period_days=90
        )
        print("✅ 2. Счета созданы: Uzcard (15 млн), Вклад Капиталбанк (50 млн @ 22%), Uzum Nasiya (Лимит 20 млн)")

        # 3. Установка лимита бюджета на кафе и проверка предупреждения
        cat = await service.set_category_budget(user_id=user.id, category_name="Кафе и рестораны", monthly_budget=2000000.0)
        assert cat.monthly_budget == 2000000.0
        print(f"✅ 3. Лимит на категорию '{cat.name}' установлен: {cat.monthly_budget:,.0f} сум")

        # 4. Трата с карты Uzcard
        tx1, acc1, alert1 = await service.add_transaction(
            user_id=user.id,
            amount=1750000.0,
            tx_type=TransactionType.EXPENSE,
            category_name="Кафе и рестораны",
            account_name="Карта Uzcard",
            description="Ужин с друзьями"
        )
        assert acc1.balance == 13250000.0
        assert alert1 is not None and "88%" in alert1
        print(f"✅ 4. Трата {tx1.amount:,.0f} сум: баланс {acc1.balance:,.0f} сум. Сработал алерт бюджета: {alert1}")

        # 5. Трата с рассрочки Uzum Nasiya
        tx2, acc2, _ = await service.add_transaction(
            user_id=user.id,
            amount=4500000.0,
            tx_type=TransactionType.EXPENSE,
            category_name="Техника и гаджеты",
            account_name="Рассрочка Uzum Nasiya",
            description="Смартфон"
        )
        assert acc2.balance == -4500000.0
        print(f"✅ 5. Покупка в рассрочку Uzum Nasiya: долг {abs(acc2.balance):,.0f} сум")

        # 6. Погашение части рассрочки с Uzcard (перевод без задвоения расходов)
        from_acc, to_acc, tr_tx = await service.transfer_funds(
            user_id=user.id,
            from_account_name="Карта Uzcard",
            to_account_name="Рассрочка Uzum Nasiya",
            amount=2000000.0,
            description="Платеж за рассрочку"
        )
        assert from_acc.balance == 11250000.0
        assert to_acc.balance == -2500000.0
        print(f"✅ 6. Платеж по рассрочке: остаток Uzcard {from_acc.balance:,.0f} сум, долг снизился до {abs(to_acc.balance):,.0f} сум")

        # 7. Ежедневное ночное начисление процентов по вкладу (22% годовых)
        accruals = await service.process_daily_deposit_yields(target_date=date.today())
        assert len(accruals) == 1
        expected_daily = round(50000000.0 * 0.22 / 365.0, 2)
        assert accruals[0]["amount"] == expected_daily
        print(f"✅ 7. Начислен пассивный доход по вкладу 22%: +{accruals[0]['amount']:,.0f} сум/день")

        # 8. Проверка расчета Net Worth и курса ЦБ
        summary = await service.get_net_worth_summary(user_id=user.id)
        rate = CurrencyService.get_usd_rate()
        usd_str = CurrencyService.to_usd_str(summary['total_balance'])
        print(f"✅ 8. Капитал (Net Worth):")
        print(f"   • Чистый капитал: {summary['total_balance']:,.0f} сум ({usd_str} по курсу ЦБ РУз {rate:,.0f})")
        print(f"   • Всего активов:  {summary['total_assets']:,.0f} сум")
        print(f"   • Обязательства:  -{summary['total_debt']:,.0f} сум")
        assert summary["total_debt"] == 2500000.0

        # 9. Генерация графического и HTML-дашборда
        now = datetime.utcnow()
        stats = await service.get_financial_stats(user.id, datetime(now.year, now.month, 1), now)

        dash_png = ChartService.generate_full_dashboard(stats, summary, "текущий месяц")
        assert len(dash_png.getvalue()) > 5000
        print(f"✅ 9. Графический HD-Дашборд успешно сгенерирован ({len(dash_png.getvalue())} байт PNG)")

        html_dash = ChartService.generate_interactive_html(stats, summary, "текущий месяц")
        assert "<!DOCTYPE html>" in html_dash and "chart.js" in html_dash.lower()
        print(f"✅ 10. Интерактивный HTML5 Web-Дашборд успешно сформирован ({len(html_dash)} символов)")

    print("\n🎉 ВСЕ ТЕСТЫ ДАШБОРДА И ФИНАНСОВОГО ЯДРА ПРОЙДЕНЫ НА 100%!")

if __name__ == "__main__":
    asyncio.run(run_tests())
