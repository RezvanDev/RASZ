import io
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.enums import ChatAction

from bot.services.finance_service import FinanceService
from bot.services.ai_service import AIService
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
router = Router()
ai_service = AIService()

POPULAR_CATEGORIES = [
    ("🥤 Напитки", "drinks", "Напитки"),
    ("🚬 Табак/никотин", "tobacco", "Табак и никотин"),
    ("🛒 Продукты", "food", "Продукты и супермаркеты"),
    ("🍽️ Кафе и еда", "cafe", "Кафе, рестораны и доставка"),
    ("🚕 Такси/транспорт", "taxi", "Транспорт и такси"),
    ("💊 Аптека", "health", "Здоровье и аптеки"),
    ("🎉 Отдых", "fun", "Развлечения и отдых"),
    ("📦 Прочее", "other", "Прочие расходы"),
]

CATEGORY_CODE_MAP = {code: name for _, code, name in POPULAR_CATEGORIES}

def build_category_selection_keyboard(tx_id: int) -> InlineKeyboardMarkup:
    """Builds inline keyboard with popular categories for quick 1-tap switching."""
    buttons = []
    row = []
    for label, code, _ in POPULAR_CATEGORIES:
        row.append(InlineKeyboardButton(text=label, callback_data=f"set_cat_{tx_id}_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat_back_{tx_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_tx_action_keyboard(tx_id: int, current_account_name: str, accounts: list) -> InlineKeyboardMarkup:
    """Builds inline keyboard with quick account-switching buttons, category switcher, and undo button."""
    buttons = []
    switch_row = []
    for a in accounts:
        if a.name != current_account_name:
            switch_row.append(InlineKeyboardButton(
                text=f"💳 {a.name}",
                callback_data=f"switch_acc_{tx_id}_{a.id}"
            ))
            if len(switch_row) == 2:
                buttons.append(switch_row)
                switch_row = []
    if switch_row:
        buttons.append(switch_row)

    buttons.append([
        InlineKeyboardButton(text="🏷 Сменить категорию", callback_data=f"cat_menu_{tx_id}")
    ])

    buttons.append([
        InlineKeyboardButton(text="❌ Отменить операцию", callback_data=f"undo_tx_{tx_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# In-memory short-term context per user (last 6 messages)
user_histories = {}

@router.message(F.voice)
async def handle_voice_message(message: Message, bot: Bot, finance: FinanceService):
    """Handles voice messages, transcribes with Whisper, and processes as text."""
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    # 1. Download voice file
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_bytes_io = io.BytesIO()
    await bot.download_file(file.file_path, file_bytes_io)
    file_bytes = file_bytes_io.getvalue()

    # 2. Transcribe via Whisper
    try:
        user_text = await ai_service.transcribe_voice(file_bytes, filename="voice.ogg")
    except Exception as e:
        logger.error(f"Voice transcription failed: {e}")
        await message.answer("⚠️ Не удалось распознать голосовое сообщение. Попробуйте написать текстом.")
        return

    # Notify user what was heard
    await message.reply(f"🎙 <i>«{user_text}»</i>")

    # 3. Process transcribed text
    await process_text_finance(message, bot, finance, user_text)

@router.message(F.photo)
async def handle_photo_receipt(message: Message, bot: Bot, finance: FinanceService):
    """Handles photos of receipts/checks and records expenses using Multimodal Vision."""
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    # 1. Download highest-resolution photo
    photo_size = message.photo[-1]
    file = await bot.get_file(photo_size.file_id)
    photo_io = io.BytesIO()
    await bot.download_file(file.file_path, photo_io)
    photo_bytes = photo_io.getvalue()

    # 2. Process image with Vision
    result = await ai_service.process_receipt_image(
        finance=finance,
        user_id=message.from_user.id,
        image_bytes=photo_bytes,
        caption=message.caption
    )

    # 3. Attach Account switcher & Undo button if transaction was created
    reply_markup = None
    tx_actions = [a for a in result.get("actions", []) if a.get("type") == "transaction_added" and a.get("tx_id")]
    if len(tx_actions) == 1:
        tx_id = tx_actions[0]["tx_id"]
        current_acc = tx_actions[0].get("account", "")
        all_accounts = await finance.get_accounts(message.from_user.id)
        reply_markup = build_tx_action_keyboard(tx_id, current_acc, all_accounts)

    try:
        await message.reply(result["text"], reply_markup=reply_markup)
    except Exception as e:
        logger.warning(f"Error sending photo reply in HTML: {e}, falling back to plain text")
        await message.reply(result["text"], reply_markup=reply_markup, parse_mode=None)

@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message, bot: Bot, finance: FinanceService):
    """Handles natural language text inputs."""
    user_text = message.text.strip()
    await process_text_finance(message, bot, finance, user_text)

async def process_text_finance(message: Message, bot: Bot, finance: FinanceService, user_text: str):
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    user_id = message.from_user.id

    # Retrieve conversational history
    history = user_histories.get(user_id, [])

    # Process with AI
    result = await ai_service.process_user_input(
        finance=finance,
        user_id=user_id,
        user_message=user_text,
        conversation_history=history
    )

    # Update history
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": result["text"]})
    user_histories[user_id] = history[-10:]  # keep recent 10 messages

    # Check if dashboard generation was requested
    dash_actions = [a for a in result.get("actions", []) if a.get("type") == "show_dashboard"]
    if dash_actions:
        from datetime import datetime, timedelta
        from aiogram.types import BufferedInputFile
        from bot.services.chart_service import ChartService
        from bot.keyboards.main_menu import get_report_period_keyboard

        da = dash_actions[0]
        dash_type = da.get("dashboard_type", "GENERAL")
        period = da.get("period", "THIS_MONTH")
        now = datetime.utcnow()

        if period == "LAST_30_DAYS":
            start_date = now - timedelta(days=30)
            period_title = "последние 30 дней"
        elif period == "LAST_7_DAYS":
            start_date = now - timedelta(days=7)
            period_title = "последние 7 дней"
        else:
            start_date = datetime(now.year, now.month, 1)
            period_title = "текущий месяц"

        stats = await finance.get_financial_stats(user_id, start_date, now)
        summary = await finance.get_net_worth_summary(user_id)

        buf, title_text = ChartService.generate_specialized_dashboard(dash_type, stats, summary, period_title)
        photo = BufferedInputFile(buf.getvalue(), filename=f"dashboard_{dash_type.lower()}.png")

        reply_markup = get_report_period_keyboard()

        full_caption = f"<b>{title_text}</b> ({period_title})\n\n" + result["text"]
        if len(full_caption) > 1024:
            await message.answer_photo(
                photo=photo,
                caption=f"<b>{title_text}</b> ({period_title})",
                reply_markup=reply_markup
            )
            await message.answer(result["text"])
        else:
            try:
                await message.answer_photo(
                    photo=photo,
                    caption=full_caption,
                    reply_markup=reply_markup
                )
            except Exception:
                await message.answer_photo(
                    photo=photo,
                    caption=f"<b>{title_text}</b> ({period_title})",
                    reply_markup=reply_markup
                )
                await message.answer(result["text"], parse_mode=None)
        return

    # If transactions were added, offer Account Switcher and Undo button
    reply_markup = None
    tx_actions = [a for a in result.get("actions", []) if a.get("type") == "transaction_added" and a.get("tx_id")]
    if len(tx_actions) == 1:
        tx_id = tx_actions[0]["tx_id"]
        current_acc = tx_actions[0].get("account", "")
        all_accounts = await finance.get_accounts(user_id)
        reply_markup = build_tx_action_keyboard(tx_id, current_acc, all_accounts)

    # Send response
    try:
        await message.answer(result["text"], reply_markup=reply_markup)
    except Exception as e:
        logger.warning(f"Error sending text reply in HTML: {e}, falling back to plain text")
        await message.answer(result["text"], reply_markup=reply_markup, parse_mode=None)

