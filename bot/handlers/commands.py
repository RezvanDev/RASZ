from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command

from bot.services.finance_service import FinanceService
from bot.services.chart_service import ChartService
from bot.services.currency_service import CurrencyService
from bot.services.ai_service import AIService, SYSTEM_FINANCIER_PROMPT
from bot.keyboards.main_menu import get_main_reply_keyboard, get_report_period_keyboard

router = Router()
ai_service = AIService()

@router.message(CommandStart())
async def cmd_start(message: Message, finance: FinanceService):
    user = await finance.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    welcome_text = (
        f"👋 <b>Ассалому алейкум / Привет, {message.from_user.first_name}!</b>\n\n"
        "Я твой <b>персональный ИИ-финансист</b> и трекер капитала в Узбекистане.\n\n"
        "<b>Что я умею:</b>\n"
        "• <b>Учитывать траты и доходы голосом или текстом (в сумах и $):</b>\n"
        "  <i>«Обед в чайхане 65 000 сум»</i>, <i>«Такси 22 000 с карты Uzcard»</i>, <i>«Зарплата 15 000 000 сум»</i>\n"
        "• <b>Считать вклады и пассивный доход:</b>\n"
        "  <i>«Открыл онлайн-вклад в Капиталбанке на 30 млн сум под 22%»</i> — я сам ежедневно считаю начисленные проценты!\n"
        "• <b>Учитывать карты Uzcard, Humo, кредитки и рассрочки (Uzum Nasiya / Payme)</b>\n"
        "• <b>Строить детальную аналитику и графики</b> (/report)\n"
        "• <b>Помогать копить:</b>\n"
        "  <i>«Хочу накопить 3 000$ на отпуск к июлю, сколько откладывать с зарплаты?»</i>\n\n"
        "Просто отправь мне сообщение или голосовое!"
    )

    await message.answer(welcome_text, reply_markup=get_main_reply_keyboard())

@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    help_text = (
        "💡 <b>Как пользоваться ботом-финансистом:</b>\n\n"
        "1. <b>Добавление трат и доходов:</b>\n"
        "Просто напишите обычной фразой (или наговорите голосовым):\n"
        "• <i>Продукты в Корзинке 180 000 сум</i>\n"
        "• <i>Бензин 250 000 и автомойка 50 000</i>\n"
        "• <i>Пришел аванс 6 000 000 сум на карту Humo</i>\n\n"
        "2. <b>Вклады, счета и инвестиции:</b>\n"
        "• <i>«Вклад в Капиталбанке 20000000 сум под 22%»</i>\n"
        "• <i>«Вклад в TBC Bank 10000000 под 21%»</i>\n"
        "• <i>«Баланс наличных 2 000 000 сум и 500$»</i>\n\n"
        "3. <b>Кредитные карты и рассрочки (Nasiya):</b>\n"
        "• <i>«Рассрочка Uzum Nasiya лимит 15 000 000, долг 2 500 000»</i>\n"
        "• <i>«Оплатил рассрочку 1 200 000 сум с карты Uzcard»</i>\n\n"
        "4. <b>Финансовые цели:</b>\n"
        "• <i>«Хочу накопить 15 000 000 сум на ноутбук до 2025-08-01»</i>\n\n"
        "5. <b>Консультация финансиста:</b>\n"
        "Спросите любой вопрос: <i>«Какая у меня подушка безопасности?»</i>, <i>«Где я трачу больше всего?»</i>"
    )
    await message.answer(help_text)

@router.message(Command("balance"))
@router.message(F.text == "💰 Баланс и Активы")
async def cmd_balance(message: Message, finance: FinanceService):
    summary = await finance.get_net_worth_summary(message.from_user.id)
    accounts = summary["accounts"]

    if not accounts:
        await message.answer("У вас пока нет зарегистрированных счетов. Напишите, например: <i>«Баланс карты Uzcard 2 500 000 сум»</i>")
        return

    assets_str = ""
    credits_str = ""
    for a in accounts:
        cur = a.currency if a.currency else "сум"
        if a.account_type.value == "CREDIT_CARD":
            debt = abs(a.balance) if a.balance < 0 else 0.0
            paid_or_avail = max(a.credit_limit + a.balance, 0.0)
            name_lower = a.name.lower()
            is_installment = any(k in name_lower for k in ["рассрочк", "авто", "курс", "nasiya", "займ", "ипотек"]) or ("кредит" in name_lower and "карт" not in name_lower)

            if is_installment:
                paid_pct = round((paid_or_avail / a.credit_limit * 100), 1) if a.credit_limit > 0 else 0.0
                icon = "🚗" if "авто" in name_lower else ("🎓" if ("курс" in name_lower or "skillbox" in name_lower) else "📦")
                credits_str += (
                    f"{icon} <b>{a.name}:</b>\n"
                    f"  • Остаток долга: <code>{debt:,.0f} {cur}</code>\n"
                    f"  • Выплачено: <b>{paid_or_avail:,.0f} {cur}</b> ({paid_pct}%) из {a.credit_limit:,.0f} {cur}\n\n"
                )
            else:
                grace_info = f", льготный период: {a.grace_period_days} дн." if a.grace_period_days > 0 else ""
                credits_str += (
                    f"💳 <b>{a.name}:</b> долг <code>{debt:,.0f} {cur}</code> из {a.credit_limit:,.0f} {cur} "
                    f"(доступно для покупок: {paid_or_avail:,.0f} {cur}{grace_info})\n\n"
                )
        else:
            type_icon = {
                "CARD": "💳",
                "CASH": "💵",
                "DEPOSIT": "🏦",
                "INVEST": "📈",
                "CRYPTO": "🪙"
            }.get(a.account_type.value, "💰")

            rate_info = f" (+{a.interest_rate}% годовых)" if a.interest_rate > 0 else ""
            assets_str += f"{type_icon} <b>{a.name}:</b> {a.balance:,.0f} {cur}{rate_info}\n"

    usd_approx = CurrencyService.to_usd_str(summary['total_balance'])
    cbu_rate = CurrencyService.get_usd_rate()

    text = (
        "📊 <b>Ваш финансовый капитал (Net Worth)</b>\n"
        "────────────────────────\n"
        f"💎 <b>Чистый капитал (Net Worth):</b> <code>{summary['total_balance']:,.0f} сум</code> ({usd_approx})\n"
        f"🟢 <b>Всего активов:</b> {summary['total_assets']:,.0f} сум\n"
    )
    if summary["total_debt"] > 0:
        text += f"🔴 <b>Всего долгов/рассрочек:</b> -{summary['total_debt']:,.0f} сум\n"

    text += (
        "────────────────────────\n"
        "<b>Активы:</b>\n"
        f"{assets_str}\n"
    )
    if credits_str:
        text += f"<b>Кредитные карты и рассрочки:</b>\n{credits_str}\n"

    text += (
        "💸 <b>Пассивный доход с активов:</b>\n"
        f"• В день: <b>+{summary['daily_yield']:,.0f} сум</b>\n"
        f"• В месяц: <b>~{summary['monthly_yield']:,.0f} сум</b>\n"
        f"• Курс ЦБ Узбекистана: 1$ = {cbu_rate:,.0f} сум"
    )
    await message.answer(text)

@router.message(Command("export"))
async def cmd_export(message: Message, finance: FinanceService):
    csv_data = await finance.export_transactions_csv(message.from_user.id)
    if not csv_data.strip():
        await message.answer("У вас пока нет транзакций для экспорта.")
        return

    doc = BufferedInputFile(csv_data.encode("utf-8-sig"), filename="transactions.csv")
    await message.answer_document(
        document=doc,
        caption="📄 <b>Выгрузка всех ваших транзакций в CSV (Excel)</b>"
    )

@router.message(Command("deposit"))
@router.message(F.text == "📈 Вклады и Пассивный доход")
async def cmd_deposits(message: Message, finance: FinanceService):
    summary = await finance.get_net_worth_summary(message.from_user.id)
    deposits = [a for a in summary["accounts"] if a.interest_rate > 0]

    if not deposits:
        await message.answer(
            "🏦 <b>У вас пока нет активных вкладов или накопительных счетов.</b>\n\n"
            "Чтобы добавить, напишите в чат:\n"
            "<i>«Открыл вклад в Капиталбанке на 30 000 000 сум под 22% годовых»</i>\n\n"
            "Бот возьмет его на автоматический учет и будет ежедневно начислять процентный доход!"
        )
        return

    text = "📈 <b>Ваши вклады и пассивный доход:</b>\n\n"
    for d in deposits:
        cur = d.currency if d.currency else "сум"
        daily = round(d.balance * (d.interest_rate / 100.0) / 365.0, 2)
        text += (
            f"🏦 <b>{d.name}</b>\n"
            f"• Баланс: <code>{d.balance:,.0f} {cur}</code>\n"
            f"• Ставка: <b>{d.interest_rate}% годовых</b>\n"
            f"• Доход в день: <b>+{daily:,.0f} {cur}</b> (~{daily*30:,.0f} {cur}/мес)\n\n"
        )

    text += (
        "────────────────────\n"
        f"💰 <b>Всего на вкладах:</b> {summary['deposits_balance']:,.0f} сум\n"
        f"🚀 <b>Суммарный пассивный доход:</b> +{summary['daily_yield']:,.0f} сум/день (+{summary['monthly_yield']:,.0f} сум/мес)"
    )
    await message.answer(text)

@router.message(Command("goals"))
@router.message(F.text == "🎯 Цели")
async def cmd_goals(message: Message, finance: FinanceService):
    goals = await finance.get_goals(message.from_user.id)

    if not goals:
        await message.answer(
            "🎯 <b>У вас еще нет финансовых целей.</b>\n\n"
            "Поставьте цель, например:\n"
            "<i>«Хочу накопить 25 000 000 сум на отпуск к июлю»</i>\n"
            "<i>«Цель: Подушка безопасности 50 000 000 сум»</i>\n\n"
            "Я рассчитаю необходимый ежемесячный взнос и помогу оптимизировать траты."
        )
        return

    text = "🎯 <b>Ваши финансовые цели:</b>\n\n"
    for g in goals:
        bar_len = 10
        filled = int(bar_len * (g["progress_percent"] / 100))
        progress_bar = "▓" * filled + "░" * (bar_len - filled)

        deadline_str = f"\n• Дедлайн: <b>{g['target_date'].strftime('%d.%m.%Y')}</b> ({g['days_left']} дн.)" if g['target_date'] else ""
        plan_str = f"\n• Нужно откладывать: <b>~{g['monthly_needed']:,.0f} сум/мес</b>" if g['monthly_needed'] > 0 else ""

        text += (
            f"📌 <b>{g['name']}</b>\n"
            f"<code>[{progress_bar}]</code> {g['progress_percent']}%\n"
            f"• Накоплено: {g['current_amount']:,.0f} из {g['target_amount']:,.0f} сум\n"
            f"• Осталось: <b>{g['remaining_amount']:,.0f} сум</b>"
            f"{deadline_str}{plan_str}\n\n"
        )

    await message.answer(text)

@router.message(Command("report"))
@router.message(F.text == "📊 Аналитика и Отчет")
async def cmd_report(message: Message, finance: FinanceService):
    now = datetime.utcnow()
    start_date = datetime(now.year, now.month, 1)
    await send_financial_report(message, finance, start_date, now, period_title="текущий месяц")

@router.message(Command("advisor"))
@router.message(F.text == "💡 Совет финансиста")
async def cmd_advisor_prompt(message: Message, bot: Bot, finance: FinanceService):
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    user_id = message.from_user.id

    fin_context = await ai_service.build_financial_context(finance, user_id)
    prompt = (
        "Пользователь нажал кнопку «💡 Совет финансиста». "
        "Проведи глубокий персональный экспресс-аудит его текущего финансового состояния, "
        "строго опираясь на 50 Золотых правил финансовой грамотности и 10 принципов инвестирования Уоррена Баффета.\n"
        "Учти его реальные данные из контекста (доходы, баланс зарплатной карты, долги по авто, курсам, кредитке TEZ, остаток задолженности):\n"
        "1. 🛡 Диагностика подушки безопасности и запаса прочности (Правило #5).\n"
        "2. 🚗 Стратегия досрочной ликвидации долгов (Правила #11, #12, Баффет #5: кредитка TEZ в льготный период, курс Skillbox, авто).\n"
        "3. 🚀 Запуск сложного процента и пассивного дохода (Правило #6, Баффет #3: размещение свободных сум на вкладах под 21-23% в банках РУз с капитализацией).\n"
        "4. 💎 Золотой совет Уоррена Баффета дня для его ситуации с четким шагом к действию.\n"
        "Форматируй красиво, емко, структурированно, с эмодзи и читаемыми суммами."
    )

    messages = [
        {"role": "system", "content": f"{SYSTEM_FINANCIER_PROMPT}\n\n{fin_context}"},
        {"role": "user", "content": prompt}
    ]

    res = await ai_service._execute_chat_completion(finance, user_id, messages)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💼 10 правил Баффета", callback_data="adv_buffett"),
            InlineKeyboardButton(text="📜 50 правил богатства", callback_data="adv_rules")
        ],
        [
            InlineKeyboardButton(text="🚀 План независимости (FIRE)", callback_data="adv_fire"),
            InlineKeyboardButton(text="🧮 Сложный процент (22%)", callback_data="adv_compound")
        ]
    ])

    try:
        await message.answer(res["text"], reply_markup=kb)
    except Exception:
        await message.answer(res["text"], reply_markup=kb, parse_mode=None)

async def send_financial_report(message: Message, finance: FinanceService, start_date: datetime, end_date: datetime, period_title: str):
    user_id = message.from_user.id
    stats = await finance.get_financial_stats(user_id, start_date, end_date)

    if stats["total_expense"] == 0 and stats["full_income"] == 0:
        await message.answer(
            f"За выбранный период ({period_title}) операций не найдено.",
            reply_markup=get_report_period_keyboard()
        )
        return

    text = (
        f"📊 <b>Финансовый отчет за {period_title}</b>\n"
        "────────────────────────\n"
        f"🟢 <b>Доходы:</b> +{stats['full_income']:,.0f} сум"
    )
    if stats['total_passive'] > 0:
        text += f" (из них пассивный доход: +{stats['total_passive']:,.0f} сум)"
    
    text += (
        f"\n🔴 <b>Расходы:</b> -{stats['total_expense']:,.0f} сум\n"
        f"💰 <b>Сбережения:</b> <b>{stats['savings']:,.0f} сум</b>\n"
        f"📈 <b>Норма сбережений (Savings Rate):</b> <b>{stats['savings_rate']}%</b>\n"
        f"📆 <b>Средний расход в день:</b> {stats['daily_avg_expense']:,.0f} сум\n"
        f"🛡 <b>Подушка безопасности (Runway):</b> ~{stats['runway_months']} мес. спокойной жизни\n"
        "────────────────────────\n"
        "<b>Топ категорий расходов:</b>\n"
    )

    for cat in stats["categories"][:5]:
        text += f"{cat['icon']} {cat['name']}: <b>{cat['amount']:,.0f} сум</b> ({cat['percent']}%)\n"

    # Generate Chart
    chart_buffer = ChartService.generate_expense_pie_chart(
        stats["categories"],
        title=f"Расходы за {period_title}"
    )

    if chart_buffer:
        photo = BufferedInputFile(chart_buffer.getvalue(), filename="report.png")
        await message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=get_report_period_keyboard()
        )
    else:
        await message.answer(text, reply_markup=get_report_period_keyboard())

@router.message(Command("dashboard"))
@router.message(F.text == "📱 Финансовый Дашборд")
async def cmd_dashboard(message: Message, finance: FinanceService):
    now = datetime.utcnow()
    start_date = datetime(now.year, now.month, 1)
    user_id = message.from_user.id

    stats = await finance.get_financial_stats(user_id, start_date, now)
    summary = await finance.get_net_worth_summary(user_id)

    # Generate full infographic dashboard image
    dashboard_buffer = ChartService.generate_full_dashboard(stats, summary, period_title="текущий месяц")
    photo = BufferedInputFile(dashboard_buffer.getvalue(), filename="dashboard.png")

    debts_lines = ""
    for c in summary.get("credit_cards", []):
        if c["debt"] > 0:
            debts_lines += f"  • {c['account'].name}: <code>{c['debt']:,.0f} сум</code>\n"

    caption = (
        "📊 <b>ЕДИНЫЙ ФИНАНСОВЫЙ ДАШБОРД</b>\n"
        "────────────────────────\n"
        f"💎 <b>Чистый капитал:</b> {summary['total_balance']:,.0f} сум ({CurrencyService.to_usd_str(summary['total_balance'])})\n"
        f"🟢 <b>Доходы:</b> +{stats['full_income']:,.0f} сум | 🔴 <b>Расходы:</b> -{stats['total_expense']:,.0f} сум\n"
        f"📈 <b>Норма сбережений:</b> {stats['savings_rate']}% | 🛡 <b>Подушка:</b> {stats['runway_months']} мес.\n"
    )
    if summary["total_debt"] > 0:
        caption += (
            f"🔴 <b>Обязательства и рассрочки:</b> -{summary['total_debt']:,.0f} сум\n"
            f"{debts_lines}"
        )
    caption += (
        f"💸 <b>Пассивный доход:</b> +{summary['daily_yield']:,.0f} сум/день\n"
        "────────────────────────\n"
        "<i>Нажмите кнопку ниже для интерактивной Web-версии (HTML)!</i>"
    )

    await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=get_report_period_keyboard()
    )

@router.message(Command("dashboard_web"))
async def cmd_dashboard_web(message: Message, finance: FinanceService):
    now = datetime.utcnow()
    start_date = datetime(now.year, now.month, 1)
    user_id = message.from_user.id

    stats = await finance.get_financial_stats(user_id, start_date, now)
    summary = await finance.get_net_worth_summary(user_id)

    html_content = ChartService.generate_interactive_html(stats, summary, period_title="текущий месяц")
    doc = BufferedInputFile(html_content.encode("utf-8"), filename="financial_dashboard.html")

    await message.answer_document(
        document=doc,
        caption=(
            "🌐 <b>Интерактивный Web-Дашборд (HTML5)</b>\n\n"
            "Скачайте и откройте этот файл в любом браузере на телефоне или компьютере.\n"
            "• Интерактивные графики с наведением (Chart.js)\n"
            "• Темная тема\n"
            "• Полная адаптивность под любые экраны"
        )
    )

@router.message(Command("backup"))
async def cmd_backup(message: Message):
    from pathlib import Path
    from aiogram.types import FSInputFile

    db_file = Path("data/finance.db")
    if not db_file.exists():
        await message.answer("Файл базы данных еще не создан.")
        return

    doc = FSInputFile(str(db_file), filename=f"finance_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.db")
    await message.answer_document(
        document=doc,
        caption="📦 <b>Резервная копия базы данных (SQLite)</b>"
    )

