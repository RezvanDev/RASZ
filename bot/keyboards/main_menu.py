from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="📱 Финансовый Дашборд"),
            KeyboardButton(text="📊 Аналитика и Отчет")
        ],
        [
            KeyboardButton(text="💰 Баланс и Активы"),
            KeyboardButton(text="📈 Вклады и Пассивный доход")
        ],
        [
            KeyboardButton(text="🎯 Цели"),
            KeyboardButton(text="💡 Совет финансиста")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Напишите трату, доход или вопрос финансисту..."
    )

def get_report_period_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📱 Полный", callback_data="report_dashboard"),
            InlineKeyboardButton(text="🟢 Доходы", callback_data="report_income"),
            InlineKeyboardButton(text="🔴 Расходы", callback_data="report_expense"),
            InlineKeyboardButton(text="🚗 Долги", callback_data="report_debts")
        ],
        [
            InlineKeyboardButton(text="🌐 Интерактивный Web-Дашборд (HTML)", callback_data="report_web_html")
        ],
        [
            InlineKeyboardButton(text="🗓 Этот месяц", callback_data="report_this_month"),
            InlineKeyboardButton(text="📅 Последние 30 дней", callback_data="report_30_days")
        ],
        [
            InlineKeyboardButton(text="⚡️ За 7 дней", callback_data="report_7_days"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="report_refresh")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

