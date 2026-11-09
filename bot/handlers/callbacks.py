from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile, InputMediaPhoto

from bot.services.finance_service import FinanceService
from bot.services.chart_service import ChartService
from bot.keyboards.main_menu import get_report_period_keyboard

router = Router()

@router.callback_query(F.data.startswith("report_"))
async def handle_report_callback(callback: CallbackQuery, finance: FinanceService):
    action = callback.data
    now = datetime.utcnow()
    user_id = callback.from_user.id

    if action == "report_web_html":
        start_date = datetime(now.year, now.month, 1)
        stats = await finance.get_financial_stats(user_id, start_date, now)
        summary = await finance.get_net_worth_summary(user_id)
        html = ChartService.generate_interactive_html(stats, summary, period_title="текущий месяц")
        doc = BufferedInputFile(html.encode("utf-8"), filename="financial_dashboard.html")
        await callback.message.answer_document(
            document=doc,
            caption="🌐 <b>Интерактивный Web-Дашборд (HTML5)</b>\nОткройте файл в любом браузере."
        )
        await callback.answer()
        return

    if action in ("report_dashboard", "report_income", "report_expense", "report_debts"):
        start_date = datetime(now.year, now.month, 1)
        period_title = "текущий месяц"
        stats = await finance.get_financial_stats(user_id, start_date, now)
        summary = await finance.get_net_worth_summary(user_id)

        type_map = {
            "report_dashboard": "GENERAL",
            "report_income": "INCOME",
            "report_expense": "EXPENSE",
            "report_debts": "DEBTS"
        }
        dash_type = type_map[action]
        dash_buf, title = ChartService.generate_specialized_dashboard(dash_type, stats, summary, period_title=period_title)

        caption = (
            f"<b>{title}</b> ({period_title})\n"
            "────────────────────────\n"
            f"💎 <b>Чистый капитал:</b> {summary['total_balance']:,.0f} сум\n"
            f"🟢 <b>Доходы:</b> +{stats['full_income']:,.0f} сум | 🔴 <b>Расходы:</b> -{stats['total_expense']:,.0f} сум\n"
            f"⚖️ <b>Обязательства:</b> -{summary['total_debt']:,.0f} сум | 🛡 <b>Подушка:</b> {stats['runway_months']} мес.\n"
            "────────────────────────\n"
            "<i>Выберите вид дашборда кнопками ниже или скачайте Web-версию.</i>"
        )

        media = InputMediaPhoto(
            media=BufferedInputFile(dash_buf.getvalue(), filename=f"dashboard_{dash_type.lower()}.png"),
            caption=caption
        )
        try:
            await callback.message.edit_media(media=media, reply_markup=get_report_period_keyboard())
        except Exception:
            pass
        await callback.answer()
        return

    if action == "report_this_month" or action == "report_refresh":
        start_date = datetime(now.year, now.month, 1)
        period_title = "текущий месяц"
    elif action == "report_30_days":
        start_date = now - timedelta(days=30)
        period_title = "последние 30 дней"
    elif action == "report_7_days":
        start_date = now - timedelta(days=7)
        period_title = "последние 7 дней"
    else:
        await callback.answer()
        return

    user_id = callback.from_user.id
    stats = await finance.get_financial_stats(user_id, start_date, now)

    text = (
        f"📊 <b>Финансовый отчет за {period_title}</b>\n"
        "────────────────────────\n"
        f"🟢 <b>Доходы:</b> +{stats['full_income']:,.0f} сум"
    )
    if stats['total_passive'] > 0:
        text += f" (включая пассивный доход: +{stats['total_passive']:,.0f} сум)"

    text += (
        f"\n🔴 <b>Расходы:</b> -{stats['total_expense']:,.0f} сум\n"
        f"💰 <b>Сбережения:</b> <b>{stats['savings']:,.0f} сум</b>\n"
        f"📈 <b>Норма сбережений (Savings Rate):</b> <b>{stats['savings_rate']}%</b>\n"
        f"📆 <b>Средний расход в день:</b> {stats['daily_avg_expense']:,.0f} сум\n"
        f"🛡 <b>Подушка безопасности (Runway):</b> ~{stats['runway_months']} мес.\n"
        "────────────────────────\n"
        "<b>Топ категорий расходов:</b>\n"
    )

    for cat in stats["categories"][:5]:
        text += f"{cat['icon']} {cat['name']}: <b>{cat['amount']:,.0f} сум</b> ({cat['percent']}%)\n"

    chart_buffer = ChartService.generate_expense_pie_chart(
        stats["categories"],
        title=f"Расходы ({period_title})"
    )

    try:
        if chart_buffer and callback.message.photo:
            media = InputMediaPhoto(
                media=BufferedInputFile(chart_buffer.getvalue(), filename="report.png"),
                caption=text
            )
            await callback.message.edit_media(media=media, reply_markup=get_report_period_keyboard())
        else:
            await callback.message.edit_text(text, reply_markup=get_report_period_keyboard())
    except Exception:
        pass  # Content hasn't changed

    await callback.answer()

@router.callback_query(F.data.startswith("undo_tx_"))
async def handle_undo_tx_callback(callback: CallbackQuery, finance: FinanceService):
    tx_id_str = callback.data.split("_")[-1]
    if not tx_id_str.isdigit():
        await callback.answer("Ошибка отмены", show_alert=True)
        return

    tx_id = int(tx_id_str)
    result = await finance.delete_transaction(tx_id=tx_id, user_id=callback.from_user.id)
    if result:
        await callback.message.edit_text(
            f"🗑 <b>Операция успешно отменена:</b>\n"
            f"• Категория: {result['category']}\n"
            f"• Сумма: {result['amount']:,.0f} сум\n"
            f"• Баланс счета '{result['account']}': <b>{result['new_balance']:,.0f} сум</b>"
        )
        await callback.answer("Операция отменена")
    else:
        await callback.answer("Транзакция уже удалена или не найдена.", show_alert=True)

@router.callback_query(F.data.startswith("switch_acc_"))
async def handle_switch_acc_callback(callback: CallbackQuery, finance: FinanceService):
    parts = callback.data.split("_")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer("Ошибка запроса", show_alert=True)
        return

    tx_id = int(parts[2])
    target_acc_id = int(parts[3])
    user_id = callback.from_user.id

    res = await finance.switch_transaction_account(tx_id, user_id, target_acc_id)
    if not res:
        await callback.answer("Не удалось сменить счет (возможно, операция удалена)", show_alert=True)
        return

    from bot.handlers.messages import build_tx_action_keyboard
    all_accounts = await finance.get_accounts(user_id)
    reply_markup = build_tx_action_keyboard(tx_id, res["new_account"], all_accounts)

    text = (
        f"✅ <b>Записано:</b> {res['category']} -{res['amount']:,.0f} сум\n"
        f"💳 <b>Счет списания:</b> {res['new_account']} (остаток: <b>{res['new_balance']:,.0f} сум</b>)\n"
        f"<i>(Счет {res['old_account']} восстановлен: {res['old_balance']:,.0f} сум)</i>"
    )

    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        pass
    await callback.answer(f"Счет изменен на {res['new_account']}")

@router.callback_query(F.data == "adv_buffett")
async def handle_adv_buffett(callback: CallbackQuery):
    text = (
        "💼 <b>10 ЗОЛОТЫХ ПРАВИЛ ИНВЕСТИРОВАНИЯ УОРРЕНА БАФФЕТА</b>\n\n"
        "1. 📈 <b>Акции следуют за ценностью бизнеса</b> — покупая актив, вы покупаете долю в реальном бизнесе. Оценивайте полезность и прибыль, а не шум.\n\n"
        "2. 📉 <b>Не надейтесь на биржевую цену</b> — рынок эмоционален. Когда все паникуют, появляются лучшие цены для покупки качественных активов.\n\n"
        "3. 💸 <b>Обращайте внимание на дивиденды</b> — пассивный доход нужно <b>реинвестировать</b>, запуская сложный процент.\n\n"
        "4. 🎯 <b>На бирже нельзя доверять случайности</b> — забудьте о краткосрочных спекуляциях. Инвестируйте в то, что понимаете.\n\n"
        "5. ⛔️ <b>Не инвестируйте деньги, взятые в долг!</b>\n"
        "<i>«Безумно рисковать тем, что у вас есть, ради того, в чем вы действительно не нуждаетесь».</i>\n\n"
        "6. ✂️ <b>Избавляйтесь от неудачных активов</b> — если идея перестала работать, фиксируйте результат без жалости.\n\n"
        "7. 🛡 <b>Не сорите капиталом — держите резервы</b> — подушка безопасности позволит пережить любой спад и купить активы на дне.\n\n"
        "8. 🔭 <b>Смотрите в будущее компании, а не в прошлое</b> — важен будущий денежный поток.\n\n"
        "9. 🦈 <b>«Бойтесь, когда другие жадничают, и будьте жадными, когда другие боятся»</b>.\n\n"
        "10. 🧠 <b>Инвестированию можно научиться</b> — дисциплина, терпение и система бьют высокий IQ!"
    )
    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "adv_rules")
async def handle_adv_rules(callback: CallbackQuery):
    text = (
        "📜 <b>ФУНДАМЕНТ БОГАТСТВА: 50 ПРАВИЛ ФИНАНСОВОЙ ГРАМОТНОСТИ</b>\n\n"
        "<b>1. Основы и дисциплина</b>\n"
        "• <i>Учет 100% трат:</i> знайте, куда уходит каждый сум.\n"
        "• <i>Живите по средствам:</i> тратьте строго меньше, чем зарабатываете.\n"
        "• <i>Платите сначала себе:</i> 20-30% от дохода откладывайте в капитал в день получения зарплаты.\n\n"
        "<b>2. Долги и кредиты</b>\n"
        "• Избегайте потребительских кредитов на статус и роскошь.\n"
        "• <i>Принцип Лавины:</i> долги с высоким процентом (кредитки) гасите первыми.\n"
        "• Карты с льготным периодом закрывайте строго вовремя, не допуская штрафов.\n\n"
        "<b>3. Накопления и инвестиции</b>\n"
        "• <i>Подушка 3–6 месяцев:</i> неприкосновенный запас на непредвиденный случай.\n"
        "• Начинайте откладывать рано: время умножает сложный процент.\n"
        "• Инвестируйте в себя: навыки и экспертиза — лучший щит от инфляции.\n"
        "• Диверсифицируйте: распределяйте капитал между сумами, валютой и активами.\n\n"
        "<b>4. Контроль расходов</b>\n"
        "• <i>Правило 24–72 часов:</i> перед покупкой не первой необходимости дайте эмоциям остыть.\n"
        "• Покупайте качественные вещи, служащие долго, и отменяйте неиспользуемые подписки."
    )
    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "adv_fire")
async def handle_adv_fire(callback: CallbackQuery, finance: FinanceService):
    user_id = callback.from_user.id
    summary = await finance.get_net_worth_summary(user_id)
    cur_debts = summary["total_debt"]

    text = (
        "🚀 <b>ПУТЬ К ФИНАНСОВОЙ НЕЗАВИСИМОСТИ (FIRE) В УЗБЕКИСТАНЕ</b>\n\n"
        "Финансовая свобода наступает тогда, когда пассивный доход от капитала полностью покрывает ваш образ жизни.\n\n"
        "<b>Четыре ступени к свободе:</b>\n\n"
        "1️⃣ <b>СТУПЕНЬ 1: Защитный купол (Подушка безопасности)</b>\n"
        "Накопить запас на 3-6 месяцев (от 36 000 000 сум) на накопительном счете.\n\n"
        f"2️⃣ <b>СТУПЕНЬ 2: Ликвидация токсичных долгов ({cur_debts:,.0f} сум)</b>\n"
        "• Шаг A: закрыть кредитку TEZ в льготный период (0% переплат).\n"
        "• Шаг B: закрыть курс Skillbox (высвободить ежемесячный платеж).\n"
        "• Шаг C: направить освободившийся денежный поток на автокредит.\n\n"
        "3️⃣ <b>СТУПЕНЬ 3: Снежный ком сложного процента</b>\n"
        "Когда долги закрыты, 100% ежемесячного платежа направляется на вклады под 21-23% годовых в банках РУз с реинвестированием.\n\n"
        "4️⃣ <b>СТУПЕНЬ 4: Капитал свободы</b>\n"
        "При капитале 500 млн сум банковский процент дает <b>~9 000 000 сум в месяц</b> чистейшего пассивного дохода без необходимости работать!"
    )
    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "adv_compound")
async def handle_adv_compound(callback: CallbackQuery):
    text = (
        "🧮 <b>СИЛА СЛОЖНОГО ПРОЦЕНТА В УЗБЕКИСТАНЕ (22% ГОДОВЫХ)</b>\n\n"
        "Альберт Эйнштейн назвал сложный процент восьмым чудом света, а Уоррен Баффет сколотил на нем 99% своего состояния.\n\n"
        "<b>Правило 72:</b>\n"
        "Разделите 72 на процентную ставку, чтобы узнать, через сколько лет капитал <b>удвоится</b>:\n"
        "<code>72 / 22% ≈ 3.3 года!</code> Каждые 39 месяцев ваши деньги удваиваются!\n\n"
        "<b>Если откладывать 3 000 000 сум в месяц под 22% с капитализацией:</b>\n"
        "• Через 1 год: <b>40 500 000 сум</b> (из них проценты: +4 500 000 сум)\n"
        "• Через 3 года: <b>152 400 000 сум</b> (из них проценты: +44 400 000 сум)\n"
        "• Через 5 лет: <b>325 800 000 сум</b> (из них проценты: +145 800 000 сум)\n"
        "• Через 10 лет: <b>1 280 000 000 сум</b> (из них проценты: +920 000 000 сум!)\n\n"
        "💡 <i>Через 10 лет вы внесете своими деньгами всего 360 млн, а получите почти 1.3 миллиарда сум благодаря магии сложного процента!</i>"
    )
    await callback.message.answer(text)
    await callback.answer()


