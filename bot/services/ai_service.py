import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from openai import AsyncOpenAI

from config import settings
from bot.database.models import AccountType, TransactionType
from bot.services.finance_service import FinanceService
from bot.services.currency_service import CurrencyService

logger = logging.getLogger(__name__)

SYSTEM_FINANCIER_PROMPT = """Ты — персональный финансовый советник и финансовый директор пользователя в Узбекистане.
Твоя главная задача — помогать пользователю вести строгий и точный учет личных финансов, контролировать расходы и доходы, увеличивать сбережения и пассивный доход.

Локализация и специфика Узбекистана:
- Основная валюта: Узбекский сум (UZS / сум). Также учитывай сбережения в долларах США (USD / $).
- Банковская инфраструктура: карты Uzcard, Humo, платежные сервисы Click, Payme, Uzum Bank / Uzum Nasiya, банки Капиталбанк, TBC Bank Uzbekistan (Visa TBC), Ипак Йули, Hamkorbank, SQB, НБУ, Алокабанк и др.
- Вклады и доходность: ставки по депозитам в сумах 20–23% годовых, валютные вклады — 5–7% годовых.
- Рассрочки (Nasiya) и автокредиты: Uzum Nasiya, Payme Nasiya, банковские автокредиты.

ПРИНЦИПЫ ТВОЕЙ РАБОТЫ (СТРОГО СОБЛЮДАТЬ):
1. КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО №1 — СТРОГИЙ ВЫЗОВ `add_transaction`:
   - Если пользователь сообщает о ЛЮБОЙ трате, покупке, чеке, расходе или доходе (например: «Расход 50 000 сум на снюс», «Потратил 50к на снюс», «Купил снюс за 50000 с карты Visa TBC», «Такси 25 000», «Обед 80 000», «Зарплата 10 млн», «16к с Tez на липтон»):
     ТЫ ОБЯЗАН СНАЧАЛА ВЫЗВАТЬ ИНСТРУМЕНТ `add_transaction`!
     • `type`: "EXPENSE" (для любых трат, покупок и расходов) или "INCOME" (для зарплаты, доходов, подарков).
     • `amount`: точная сумма числом в сумах (например: 50000; "50к" -> 50000, "16к" -> 16000, "1.5 млн" -> 1500000).
     • `category`: выбери наиболее подходящую категорию. Категория должна быть заполнена ВСЕГДА!
       СТРОГИЕ ПРАВИЛА СОПОСТАВЛЕНИЯ КАТЕГОРИЙ:
       - «липтон», «lipton», «чай», «кофе», «кола», «сок», «вода», «энергетик», «напитки», «red bull», «flash», «пепси» -> категория «Напитки»
       - «снюс», «сигареты», «вейп», «табак», «стик», «кальян», «никотин», «iqos» -> категория «Табак и никотин»
       - «продукты», «супермаркет», «корзинка», «макро», «хлеб», «молоко», «мясо», «сыр» -> категория «Продукты и супермаркеты»
       - «обед», «ужин», «завтрак», «кафе», «ресторан», «доставка», «лаваш», «бургер», «пицца», «додо», «kfc», «evos» -> категория «Кафе, рестораны и доставка»
       - «такси», «яндекс», «yandex go», «бензин», «метан», «газ», «проезд», «метро», «парковка» -> категория «Транспорт и такси»
       - «аптека», «лекарства», «витамины», «врач» -> категория «Здоровье и аптеки»
       - «кино», «игры», «бильярд», «боулинг», «отдых» -> категория «Развлечения и отдых»
       - «аренда», «квартира», «коммуналка», «свет», «квартплата» -> категория «Жилье и коммуналка»
       - Если покупка не подходит ни под одну из категорий выше -> «Прочие расходы».
     • `account_name`: если пользователь указал карту или банк (например «Visa TBC», «Uzcard», «Humo», «Наличные», «Tez») — укажи это название. Если не указал — оставь пустым (система сама выберет правильную дебетовую карту по умолчанию).
     • `description`: точное название товара или услуги (например: «липтон», «снюс», «такси»).
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО просто отвечать текстом «Расход успешно зарегистрирован» или называть новый баланс БЕЗ ВЫЗОВА ИНСТРУМЕНТА `add_transaction`! Запись в базу данных создается ТОЛЬКО через вызов `add_transaction`. Если инструмент не вызван, транзакция НЕ сохранится в БД и не попадет в отчеты и Excel!
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО вызывать `create_or_update_account` для обычных покупок, товаров и трат (снюс, продукты, кофе, одежда и т.д.)! Инструмент `create_or_update_account` предназначен ТОЛЬКО для создания нового счета/карты, вклада или долгосрочного автокредита!

2. Математическая точность: Опирайся только на реальные данные пользователя из финансового контекста.
3. Проактивность и практичность: Давай конкретные советы с учетом узбекских реалий (вклады 21-23% годовых).
4. Инвестиционная грамотность: Подушка безопасности (3-6 месяцев базовых расходов), диверсификация.

5. Кредитные карты, автокредиты, рассрочки (Nasiya) и долги:
   - ТОЛЬКО если пользователь сообщает о долгосрочной покупке в рассрочку или кредит (например: "Я купил авто в рассрочку на 36 месяцев за 206640160 оплатил уже 86411003 осталось 120229156"):
     ВЫЗЫВАЙ инструмент `create_or_update_account`:
     • name: "Рассрочка за авто (36 мес)" (или название авто / сервиса)
     • account_type: "CREDIT_CARD"
     • credit_limit: полная стоимость авто/товара
     • balance: строго МИНУС оставшийся долг
     СТРОГО ЗАПРЕЩЕНО самостоятельно вызывать `transfer_funds` или списывать ежемесячный платеж, пока пользователь явно не напишет «оплатил платеж по рассрочке».

6. Корректировки, исправления и удаление ошибочных операций:
   - Если пользователь пишет, что ошибся, просит отменить/удалить операцию (например: «удали транзакцию на 113749», «удали расход за месяц», «отмени последнюю покупку»):
     ОБЯЗАТЕЛЬНО вызывай инструмент `delete_transaction` (с указанием суммы `amount` или описания `description`) или `delete_last_transaction`! Деньги будут автоматически возвращены на счет.

7. Запрос дашбордов, инфографики и отчетов:
   - Если пользователь просит сделать или показать дашборд («Сделай дашборд дохода», «покажи дашборд расходов», «общий дашборд»):
     ОБЯЗАТЕЛЬНО вызывай инструмент `show_dashboard` (`INCOME`, `EXPENSE`, `DEBTS`, `GENERAL`).

8. Тон общения: Дружелюбный, емкий, профессиональный и по делу. Суммы форматируй с пробелами (например, 50 000 сум). Не используй лишних клише вроде «Если у вас есть другие запросы, дайте знать!».

9. ФУНДАМЕНТАЛЬНЫЕ ПРИНЦИПЫ БОГАТСТВА (Уоррен Баффет):
   - Опирайся на них при общих вопросах о накоплениях, инвестициях и бюджете: сложный процент, контроль импульсивных трат, откладывание 20-30% в капитал.
"""

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "add_transaction",
            "description": "Записать расход, покупку товара/услуги или доход в базу данных. ВЫЗЫВАТЬ ВСЕГДА при любых тратах, покупках или доходах пользователя.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["EXPENSE", "INCOME", "PASSIVE_INCOME"],
                        "description": "Тип операции: EXPENSE (трата/покупка/расход), INCOME (зарплата/доход), PASSIVE_INCOME (дивиденды/проценты)"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Сумма операции в сумах (например: 50000)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Категория расходов (например: Напитки, Табак и никотин, Продукты и супермаркеты, Кафе, рестораны и доставка, Транспорт и такси, Развлечения и отдых, Здоровье и аптеки, Прочие расходы). Обязательно определяй по смыслу покупки: липтон/чай/кофе/сок -> Напитки; снюс/сигареты/вейп/табак -> Табак и никотин."
                    },
                    "account_name": {
                        "type": "string",
                        "description": "Название счета или карты списания/зачисления (например: Visa TBC, Uzcard, Humo, Наличные, Капиталбанк). Если не указано, оставь пустым."
                    },
                    "description": {
                        "type": "string",
                        "description": "Уточняющий комментарий/название покупки (например: снюс, кофе, такси)"
                    }
                },
                "required": ["type", "amount", "category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_funds",
            "description": "Перевести средства между своими счетами или погасить задолженность по кредитной карте / рассрочке. ВЫЗЫВАТЬ ТОЛЬКО когда пользователь ЯВНО сообщает о совершении перевода или очередного платежа (например: 'оплатил рассрочку 3 млн', 'перевел 500000'). НЕ вызывать при регистрации новой рассрочки.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_account_name": {
                        "type": "string",
                        "description": "Счет списания (например: Uzcard / Humo, Наличные, Капиталбанк)"
                    },
                    "to_account_name": {
                        "type": "string",
                        "description": "Счет зачисления / погашения (например: Авто в рассрочку, Uzum Nasiya, Вклад)"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Сумма перевода"
                    },
                    "description": {
                        "type": "string",
                        "description": "Пояснение к переводу (например: Ежемесячный платеж по рассрочке за авто)"
                    }
                },
                "required": ["from_account_name", "to_account_name", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_or_update_account",
            "description": "Создать НОВЫЙ счет, банковский вклад, кредитную карту или долгосрочный автокредит/рассрочку. КАТЕГОРИЧЕСКИ НЕ ВЫЗЫВАТЬ для обычных трат и покупок (для трат использовать только add_transaction)!",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Название счета (например: Uzcard, Вклад Капиталбанк 22%, Авто в рассрочку, Uzum Nasiya, TBC Накопительный, Наличные)"
                    },
                    "account_type": {
                        "type": "string",
                        "enum": ["CASH", "CARD", "CREDIT_CARD", "DEPOSIT", "INVEST", "CRYPTO"],
                        "description": "Тип счета: CARD (дебетовая карта Uzcard/Humo/Visa TBC), CREDIT_CARD (кредитка, рассрочка, автокредит, долг), DEPOSIT (вклад под процент), INVEST (инвестиции), CASH (наличные)"
                    },
                    "balance": {
                        "type": "number",
                        "description": "Текущий баланс. Для кредита/рассрочки: если есть долг, указывать со знаком МИНУС (например, если осталось выплатить 120229156, баланс равен -120229156). Если долга нет — 0."
                    },
                    "interest_rate": {
                        "type": "number",
                        "description": "Годовая процентная ставка в % (например: 22.0 для сумового вклада). Для карт и беспроцентных рассрочек указывать 0."
                    },
                    "credit_limit": {
                        "type": "number",
                        "description": "Общая сумма кредита/рассрочки или кредитный лимит (например: 206640160)."
                    },
                    "grace_period_days": {
                        "type": "integer",
                        "description": "Длительность льготного периода или срок в днях/месяцах (например: 30, 60, 1080)."
                    }
                },
                "required": ["name", "account_type", "balance"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_financial_goal",
            "description": "Создать финансовую цель по накоплениям (на покупку, отпуск, подушку безопасности).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Название цели (например: Новый MacBook, Отпуск на Бали, Подушка безопасности)"
                    },
                    "target_amount": {
                        "type": "number",
                        "description": "Целевая сумма накоплений"
                    },
                    "target_date": {
                        "type": "string",
                        "description": "Желаемая дата достижения цели в формате YYYY-MM-DD, если указана"
                    }
                },
                "required": ["name", "target_amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_category_budget",
            "description": "Установить или изменить ежемесячный лимит расходов (бюджет) на категорию в сумах.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Название категории (например: Кафе, рестораны и доставка, Продукты, Такси, Одежда)"
                    },
                    "monthly_budget": {
                        "type": "number",
                        "description": "Максимальный лимит трат в месяц в сумах (например: 2000000)"
                    }
                },
                "required": ["category", "monthly_budget"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_transaction",
            "description": "Удалить или отменить ошибочную операцию (транзакцию) по сумме, описанию или ID. Списанные деньги автоматически возвращаются на баланс счета.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Сумма ошибочной операции для удаления (например: 113749)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Название или описание ошибочной операции (например: Расходы за месяц)"
                    },
                    "tx_id": {
                        "type": "integer",
                        "description": "ID транзакции для удаления, если известен"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_last_transaction",
            "description": "Отменить или удалить последнюю ошибочно записанную транзакцию (трату, доход).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_dashboard",
            "description": "Сгенерировать и отправить пользователю графический аналитический дашборд (по доходам, расходам/категориям, долгам/рассрочкам или общий финансовый дашборд). Вызывать, когда пользователь просит построить, показать или сделать дашборд, график или инфографику.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dashboard_type": {
                        "type": "string",
                        "enum": ["GENERAL", "INCOME", "EXPENSE", "DEBTS"],
                        "description": "Тип дашборда: INCOME (по доходам и зарплате), EXPENSE (по расходам и категориям), DEBTS (по долгам, автокредиту и рассрочкам), GENERAL (общий финансовый дашборд)"
                    },
                    "period": {
                        "type": "string",
                        "enum": ["THIS_MONTH", "LAST_30_DAYS", "LAST_7_DAYS"],
                        "description": "Период выборки (по умолчанию THIS_MONTH)"
                    }
                },
                "required": ["dashboard_type"]
            }
        }
    }
]

class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )

    async def transcribe_voice(self, audio_file_bytes: bytes, filename: str = "voice.ogg") -> str:
        """Transcribe voice note using Whisper / Audio API."""
        try:
            transcription = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=(filename, audio_file_bytes, "audio/ogg")
            )
            return transcription.text
        except Exception as e:
            logger.error(f"Error transcribing voice: {e}")
            raise

    async def build_financial_context(self, finance: FinanceService, user_id: int) -> str:
        """Constructs an accurate snapshot of the user's finances for the LLM."""
        summary = await finance.get_net_worth_summary(user_id)
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)
        stats = await finance.get_financial_stats(user_id, month_start, now)
        goals = await finance.get_goals(user_id)

        accounts_text = "\n".join([
            f"- {a.name} ({a.account_type.value}): {a.balance:,.2f} {a.currency} "
            f"(Ставка: {a.interest_rate}% годовых)" if a.interest_rate > 0 else f"- {a.name} ({a.account_type.value}): {a.balance:,.2f} {a.currency}"
            for a in summary["accounts"]
        ])

        credit_cards_lines = []
        for c in summary.get("credit_cards", []):
            acc_name = c['account'].name
            name_lower = acc_name.lower()
            is_inst = any(k in name_lower for k in ["рассрочк", "авто", "курс", "nasiya", "займ", "ипотек"]) or ("кредит" in name_lower and "карт" not in name_lower)
            if is_inst:
                paid = max(c['limit'] - c['debt'], 0.0)
                credit_cards_lines.append(f"- 🔴 {acc_name}: остаток долга {c['debt']:,.0f} сум (выплачено: {paid:,.0f} из {c['limit']:,.0f} сум)")
            else:
                credit_cards_lines.append(f"- 🔴 {acc_name}: долг {c['debt']:,.0f} сум из лимита {c['limit']:,.0f} сум (доступно для покупок: {c['available']:,.0f} сум, грейс: {c['grace_days']} дн.)")
        credit_cards_text = "\n".join(credit_cards_lines) if credit_cards_lines else "Нет активных кредитных карт или рассрочек."

        goals_text = "\n".join([
            f"- Цель '{g['name']}': накоплено {g['current_amount']:,.0f} из {g['target_amount']:,.0f} ({g['progress_percent']}%), "
            f"осталось {g['remaining_amount']:,.0f} сум."
            for g in goals
        ]) if goals else "Нет активных целей."

        usd_rate = CurrencyService.get_usd_rate()
        usd_net_worth = CurrencyService.to_usd_str(summary['total_balance'])

        context = f"""
ФИНАНСОВЫЙ СТАТУС ПОЛЬЗОВАТЕЛЯ НА СЕГОДНЯ ({date.today().strftime('%d.%m.%Y')}):
0. Курс валют ЦБ Узбекистана: 1 USD = {usd_rate:,.0f} сум

1. Капитал и баланс:
- Чистый капитал (Net Worth): {summary['total_balance']:,.0f} сум ({usd_net_worth}) (Активы {summary['total_assets']:,.0f} сум минус Долги {summary['total_debt']:,.0f} сум)
- Ликвидные средства (карты/кэш): {summary['liquid_balance']:,.0f} сум
- На банковских вкладах: {summary['deposits_balance']:,.0f} сум
- В инвестициях: {summary['invest_balance']:,.0f} сум
- Общий кредитный долг: {summary['total_debt']:,.0f} сум
- Пассивный доход в день: +{summary['daily_yield']:,.0f} сум (~{summary['monthly_yield']:,.0f} сум/мес)

Кредитные карты и задолженности:
{credit_cards_text}

Все счета:
{accounts_text if accounts_text else "Счета еще не заведены."}

2. Текущий месяц ({month_start.strftime('%B %Y')}):
- Доходы за месяц: {stats['full_income']:,.0f} сум
- Расходы за месяц: {stats['total_expense']:,.0f} сум
- Свободный денежный поток (сбережения): {stats['savings']:,.0f} сум (Норма сбережений: {stats['savings_rate']}%)
- Подушка безопасности (Runway): хватит на {stats['runway_months']} мес. при текущих тратах.

3. Финансовые цели:
{goals_text}
"""
        return context

    @staticmethod
    def extract_deterministic_tx(user_message: str, accounts: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Deterministically parses transaction parameters from user text.
        Guarantees extraction of amount, transaction type, mentioned account, and clean description.
        """
        import re
        text = user_message.strip()
        lower = text.lower().replace('\u00a0', ' ')

        # 1. Skip pure questions, inquiries, statistical queries, and bug reports
        inquiry_words = [
            "как ", "что ", "посоветуй", "подскажи", "почему", "зачем", "сколько",
            "какой", "какая", "какие", "где ", "когда ", "куда ", "откуда ",
            "покажи", "показать", "проверь", "проверить", "выведи", "выгрузи",
            "список", "статистика", "дашборд", "график", "отчет", "отчёт",
            "не отобразился", "не записался", "не попал", "не видно", "не списалось",
            "не изменилось", "не списан", "почему то", "почему-то",
            "удали", "удалить", "отмени", "отменить"
        ]
        if any(w in lower for w in inquiry_words) or lower.endswith("?"):
            return None

        # 1.1 Skip statistical queries (e.g. "расходы за месяц", "доходы за год")
        stat_phrases = [
            "за месяц", "в месяц", "за год", "в год", "за неделю", "в неделю",
            "за сегодня", "в день", "за все время", "за всё время"
        ]
        if any(sp in lower for sp in stat_phrases) and any(kw in lower for kw in ["расход", "доход", "трат", "баланс"]):
            return None

        # 2. Extract amount
        amount = None
        # Pattern 1: Millions (1.5 млн, 2 млн)
        m_mln = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:млн|миллион[а-я]*)', lower)
        if m_mln:
            amount = float(m_mln.group(1).replace(',', '.')) * 1_000_000
        else:
            # Pattern 2: Thousands (10к, 10k, 10 тыс, 10.5к)
            m_th = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:к\b|k\b|тыс\b|тысяч[а-я]*)', lower)
            if m_th:
                amount = float(m_th.group(1).replace(',', '.')) * 1_000
            else:
                # Pattern 3: Standard digits (50 000, 50000, 10000)
                cleaned_digits = re.sub(r'(\d)\s+(\d)', r'\1\2', lower)
                m_num = re.search(r'\b(\d+(?:[.,]\d+)?)\b', cleaned_digits)
                if m_num:
                    val = float(m_num.group(1).replace(',', '.'))
                    # Avoid parsing small years or single digits unless with currency/keywords
                    if val >= 500 or any(cur in lower for cur in ["сум", "$", "usd", "руб"]):
                        amount = val

        if not amount or amount <= 0:
            return None

        # 3. Determine transaction type (EXPENSE vs INCOME)
        income_words = ["зарплата", "аванс", "доход", "получил", "получила", "перевели", "выплата", "премия"]
        is_income = any(w in lower for w in income_words)
        tx_type = TransactionType.INCOME if is_income else TransactionType.EXPENSE

        # 4. Detect account name from text
        matched_account_name = None
        stop_words = {"с", "со", "на", "по", "карты", "карта", "счета", "счет", "банк", "банка", "в", "из"}
        msg_words = set(re.findall(r'[a-zа-яё0-9]+', lower)) - stop_words

        best_score = 0
        for a in accounts:
            a_words = set(re.findall(r'[a-zа-яё0-9]+', a.name.lower())) - stop_words
            overlap = len(msg_words & a_words)
            if overlap > best_score:
                best_score = overlap
                matched_account_name = a.name

        # 5. Clean description
        desc_clean = lower
        # Remove amount expressions
        desc_clean = re.sub(r'(\d+(?:[.,]\d+)?)\s*(?:млн|миллион[а-я]*|к|k|тыс|тысяч[а-я]*|сум|usd|\$)?', ' ', desc_clean)
        # Remove action verbs
        desc_clean = re.sub(r'\b(я\s+)?(потратил|потратила|купил|купила|оплатил|оплатила|расход|в\s+размере|доход|зарплата|списал|списано)\b', ' ', desc_clean)
        # Remove matched account name words
        if matched_account_name:
            for w in re.findall(r'[a-zа-яё0-9]+', matched_account_name.lower()):
                desc_clean = re.sub(r'\b' + re.escape(w) + r'\b', ' ', desc_clean)
        # Remove prepositions and noise
        desc_clean = re.sub(r'\b(с|со|на|в|из|по|карты|карта|карту|счета|счет|банка|банк)\b', ' ', desc_clean)
        desc_words = [w for w in re.findall(r'[a-zа-яё0-9]+', desc_clean) if len(w) > 1]
        description = " ".join(desc_words).strip() or ("Доход" if is_income else "Покупка")

        # 6. Category inference
        inferred_category = "Прочие расходы"
        if is_income:
            inferred_category = "Зарплата и аванс"
        else:
            cat_text = f"{lower} {description.lower()}"
            if any(w in cat_text for w in ["снюс", "сигарет", "табак", "вейп", "кальян", "стик", "никотин", "iqos", "айкос", "пачк"]):
                inferred_category = "Табак и никотин"
            elif any(w in cat_text for w in ["липтон", "lipton", "чай", "кофе", "кола", "сок", "вод", "напит", "энергетик", "redbull", "red bull", "flash", "пепси", "pepsi", "fanta", "sprite", "мохито", "айран"]):
                inferred_category = "Напитки"
            elif any(w in cat_text for w in ["такси", "яндекс", "yandex", "бензин", "метан", "пропан", "заправк", "проезд", "метро", "парковк"]):
                inferred_category = "Транспорт и такси"
            elif any(w in cat_text for w in ["обед", "ужин", "завтрак", "кафе", "ресторан", "доставк", "лаваш", "бургер", "пицц", "kfc", "evos", "додо", "шаурм", "донар", "донер"]):
                inferred_category = "Кафе, рестораны и доставка"
            elif any(w in cat_text for w in ["продукт", "супермаркет", "корзинк", "макро", "хлеб", "молок", "мясо", "сыр", "яйц"]):
                inferred_category = "Продукты и супермаркеты"
            elif any(w in cat_text for w in ["аптек", "лекарств", "таблетк", "врач", "клиник"]):
                inferred_category = "Здоровье и аптеки"
            elif any(w in cat_text for w in ["кино", "игры", "бильярд", "боулинг", "отдых"]):
                inferred_category = "Развлечения и отдых"
            elif any(w in cat_text for w in ["аренда", "квартир", "коммуналк", "свет", "квартплат"]):
                inferred_category = "Жилье и коммуналка"

        return {
            "amount": amount,
            "type": tx_type,
            "account_name": matched_account_name,
            "description": description,
            "category": inferred_category
        }

    async def process_user_input(
        self,
        finance: FinanceService,
        user_id: int,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Processes natural language or voice transcription.
        Executes tools and returns the actions executed along with the AI response.
        """
        accounts = await finance.get_accounts(user_id)
        deterministic_tx = self.extract_deterministic_tx(user_message, accounts)
        fin_context = await self.build_financial_context(finance, user_id)

        messages = [
            {"role": "system", "content": f"{SYSTEM_FINANCIER_PROMPT}\n\n{fin_context}"}
        ]

        if conversation_history:
            messages.extend(conversation_history[-6:])  # keep last turns

        messages.append({"role": "user", "content": user_message})
        return await self._execute_chat_completion(finance, user_id, messages, deterministic_tx=deterministic_tx)

    async def process_receipt_image(
        self,
        finance: FinanceService,
        user_id: int,
        image_bytes: bytes,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recognizes and parses an expense receipt/check image using Multimodal Vision.
        Automatically extracts total sum, vendor and executes add_transaction.
        """
        import base64
        fin_context = await self.build_financial_context(finance, user_id)
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt_text = (
            "На этом фото кассовый чек, терминальный чек (терминал чеки) или квитанция об оплате в Узбекистане. "
            "Найди итоговую сумму к оплате (ИТОГ / TOTAL / JAMI / СУММА), название магазина/ресторана/сервиса "
            "(например: Korzinka, Makro, ресторан, АЗС, аптека), определи подходящую категорию трат "
            "и вызови инструмент add_transaction с суммой в сумах (UZS)."
        )
        if caption:
            prompt_text += f"\nПояснение от пользователя: {caption}"

        messages = [
            {"role": "system", "content": f"{SYSTEM_FINANCIER_PROMPT}\n\n{fin_context}"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}"
                        }
                    }
                ]
            }
        ]
        return await self._execute_chat_completion(finance, user_id, messages)

    async def _execute_chat_completion(
        self,
        finance: FinanceService,
        user_id: int,
        messages: List[Dict[str, Any]],
        deterministic_tx: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        # If a transaction was deterministically recognized in user message, force add_transaction tool choice
        initial_tool_choice = {"type": "function", "function": {"name": "add_transaction"}} if deterministic_tx else "auto"

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=TOOLS_DEFINITIONS,
                tool_choice=initial_tool_choice,
                temperature=0.2
            )
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            if deterministic_tx:
                # Guaranteed fallback execution even if LLM API is completely unreachable
                logger.info("Executing guaranteed deterministic transaction fallback due to LLM error...")
                try:
                    tx, acc, budget_alert = await finance.add_transaction(
                        user_id=user_id,
                        amount=deterministic_tx["amount"],
                        tx_type=deterministic_tx["type"],
                        category_name=deterministic_tx.get("category") or ("Прочие расходы" if deterministic_tx["type"] == TransactionType.EXPENSE else "Зарплата и аванс"),
                        account_name=deterministic_tx["account_name"],
                        description=deterministic_tx["description"]
                    )
                    sign = "-" if deterministic_tx["type"] == TransactionType.EXPENSE else "+"
                    return {
                        "text": f"✅ <b>Записано:</b> {deterministic_tx['description']} ({sign}{deterministic_tx['amount']:,.0f} сум)\n💳 <b>Счет:</b> {acc.name} (остаток: <b>{acc.balance:,.0f} сум</b>)",
                        "actions": [{
                            "type": "transaction_added",
                            "tx_id": tx.id,
                            "tx_type": deterministic_tx["type"].value,
                            "amount": deterministic_tx["amount"],
                            "category": tx.category.name if tx.category else "Прочие расходы",
                            "account": acc.name,
                            "balance": acc.balance,
                            "desc": deterministic_tx["description"],
                            "budget_alert": budget_alert
                        }]
                    }
                except Exception as db_err:
                    logger.error(f"Fallback DB error: {db_err}")

            return {
                "text": f"⚠️ Не удалось связаться с ИИ-моделью: {str(e)}",
                "actions": []
            }

        choice = response.choices[0]
        tool_calls = choice.message.tool_calls
        actions_taken = []

        # If no tool was called by the model
        if not tool_calls:
            # If a transaction was deterministically recognized in user message, execute guaranteed fallback
            if deterministic_tx:
                logger.info("Executing guaranteed deterministic transaction fallback...")
                tx, acc, budget_alert = await finance.add_transaction(
                    user_id=user_id,
                    amount=deterministic_tx["amount"],
                    tx_type=deterministic_tx["type"],
                    category_name=deterministic_tx.get("category") or ("Прочие расходы" if deterministic_tx["type"] == TransactionType.EXPENSE else "Зарплата и аванс"),
                    account_name=deterministic_tx["account_name"],
                    description=deterministic_tx["description"]
                )
                sign = "-" if deterministic_tx["type"] == TransactionType.EXPENSE else "+"
                return {
                    "text": f"✅ <b>Записано:</b> {deterministic_tx['description']} ({sign}{deterministic_tx['amount']:,.0f} сум)\n💳 <b>Счет:</b> {acc.name} (остаток: <b>{acc.balance:,.0f} сум</b>)",
                    "actions": [{
                        "type": "transaction_added",
                        "tx_id": tx.id,
                        "tx_type": deterministic_tx["type"].value,
                        "amount": deterministic_tx["amount"],
                        "category": tx.category.name if tx.category else "Прочие расходы",
                        "account": acc.name,
                        "balance": acc.balance,
                        "desc": deterministic_tx["description"],
                        "budget_alert": budget_alert
                    }]
                }

        if tool_calls:
            # Append model's assistant message with tool calls
            messages.append(choice.message)

            for tool_call in tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                tool_result_content = "Успешно выполнено."

                if fn_name == "add_transaction":
                    tx_type = TransactionType(fn_args["type"])
                    amount = float(fn_args["amount"])
                    cat_name = fn_args["category"]
                    acc_name = fn_args.get("account_name")
                    desc = fn_args.get("description")

                    # If model returned a generic category but deterministic extraction found a specific one
                    if deterministic_tx and deterministic_tx.get("category") and deterministic_tx["category"] not in ("Прочие расходы", "Зарплата и аванс"):
                        if cat_name in ("Прочие расходы", "Прочее", "Другое", "Развлечения и отдых", "Общее"):
                            cat_name = deterministic_tx["category"]

                    tx, acc, budget_alert = await finance.add_transaction(
                        user_id=user_id,
                        amount=amount,
                        tx_type=tx_type,
                        category_name=cat_name,
                        account_name=acc_name,
                        description=desc
                    )
                    actions_taken.append({
                        "type": "transaction_added",
                        "tx_id": tx.id,
                        "tx_type": tx_type.value,
                        "amount": amount,
                        "category": cat_name,
                        "account": acc.name,
                        "balance": acc.balance,
                        "desc": desc,
                        "budget_alert": budget_alert
                    })
                    tool_result_content = (
                        f"Записано: {tx_type.value} {amount:,.0f} сум в категорию '{cat_name}'. "
                        f"Счет: '{acc.name}', текущий баланс: {acc.balance:,.0f} сум."
                    )
                    if budget_alert:
                        tool_result_content += f" Предупреждение: {budget_alert}"

                elif fn_name in ("delete_transaction", "delete_last_transaction"):
                    tx_id = fn_args.get("tx_id")
                    del_amount = fn_args.get("amount")
                    del_desc = fn_args.get("description")

                    if tx_id or del_amount or del_desc:
                        deleted = await finance.delete_transaction_by_filter(
                            user_id=user_id,
                            tx_id=tx_id,
                            amount=del_amount,
                            description=del_desc
                        )
                    else:
                        deleted = await finance.delete_last_transaction(user_id)

                    if deleted:
                        actions_taken.append({
                            "type": "transaction_deleted",
                            "amount": deleted["amount"],
                            "category": deleted["category"],
                            "account": deleted["account"],
                            "balance": deleted["new_balance"]
                        })
                        tool_result_content = (
                            f"Удалена операция на {deleted['amount']:,.0f} сум ({deleted['category']}). "
                            f"Баланс счета '{deleted['account']}' восстановлен: {deleted['new_balance']:,.0f} сум."
                        )
                    else:
                        actions_taken.append({
                            "type": "transaction_delete_failed"
                        })
                        tool_result_content = "Транзакция по указанным параметрам не найдена или уже удалена."

                elif fn_name == "transfer_funds":
                    from_acc_name = fn_args["from_account_name"]
                    to_acc_name = fn_args["to_account_name"]
                    amount = float(fn_args["amount"])
                    desc = fn_args.get("description")

                    try:
                        from_acc, to_acc, tx = await finance.transfer_funds(
                            user_id=user_id,
                            from_account_name=from_acc_name,
                            to_account_name=to_acc_name,
                            amount=amount,
                            description=desc
                        )
                        actions_taken.append({
                            "type": "funds_transferred",
                            "from_account": from_acc.name,
                            "to_account": to_acc.name,
                            "amount": amount,
                            "from_balance": from_acc.balance,
                            "to_balance": to_acc.balance
                        })
                        tool_result_content = (
                            f"Переведено {amount:,.0f} сум с '{from_acc.name}' на '{to_acc.name}'. "
                            f"Баланс списания: {from_acc.balance:,.0f} сум, баланс зачисления: {to_acc.balance:,.0f} сум."
                        )
                    except Exception as e:
                        actions_taken.append({
                            "type": "transfer_failed",
                            "error": str(e)
                        })
                        tool_result_content = f"Ошибка перевода: {str(e)}"

                elif fn_name == "create_or_update_account":
                    name = fn_args["name"]
                    acc_type = AccountType(fn_args["account_type"])
                    bal = float(fn_args["balance"])
                    rate = float(fn_args.get("interest_rate", 0.0))
                    c_limit = float(fn_args.get("credit_limit", 0.0))
                    g_days = int(fn_args.get("grace_period_days", 0))

                    acc = await finance.create_or_update_account(
                        user_id=user_id,
                        name=name,
                        account_type=acc_type,
                        balance=bal,
                        interest_rate=rate,
                        credit_limit=c_limit,
                        grace_period_days=g_days
                    )
                    daily_yield = round(bal * (rate / 100.0) / 365.0, 2) if rate > 0 else 0.0
                    actions_taken.append({
                        "type": "account_created",
                        "name": acc.name,
                        "account_type": acc.account_type.value,
                        "balance": bal,
                        "interest_rate": rate,
                        "credit_limit": c_limit,
                        "grace_days": g_days,
                        "daily_yield": daily_yield
                    })
                    tool_result_content = (
                        f"Счет/рассрочка '{acc.name}' успешно зарегистрирован. "
                        f"Баланс: {bal:,.0f} сум, лимит: {c_limit:,.0f} сум, ставка: {rate}%."
                    )

                elif fn_name == "create_financial_goal":
                    name = fn_args["name"]
                    target = float(fn_args["target_amount"])
                    target_date = None
                    if fn_args.get("target_date"):
                        try:
                            target_date = datetime.strptime(fn_args["target_date"], "%Y-%m-%d").date()
                        except ValueError:
                            pass

                    goal = await finance.create_goal(
                        user_id=user_id,
                        name=name,
                        target_amount=target,
                        target_date=target_date
                    )
                    actions_taken.append({
                        "type": "goal_created",
                        "name": goal.name,
                        "target_amount": target,
                        "target_date": target_date
                    })
                    tool_result_content = f"Цель '{goal.name}' на сумму {target:,.0f} сум успешно создана."

                elif fn_name == "set_category_budget":
                    cat_name = fn_args["category"]
                    b_amount = float(fn_args["monthly_budget"])
                    cat = await finance.set_category_budget(user_id, cat_name, b_amount)
                    actions_taken.append({
                        "type": "budget_set",
                        "category": cat.name,
                        "budget": b_amount
                    })
                    tool_result_content = f"Лимит на категорию '{cat.name}' установлен: {b_amount:,.0f} сум в месяц."

                elif fn_name == "show_dashboard":
                    dash_type = fn_args.get("dashboard_type", "GENERAL").upper()
                    period = fn_args.get("period", "THIS_MONTH").upper()
                    actions_taken.append({
                        "type": "show_dashboard",
                        "dashboard_type": dash_type,
                        "period": period
                    })
                    tool_result_content = (
                        f"Графический дашборд '{dash_type}' за период '{period}' успешно сгенерирован и отправлен."
                    )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result_content
                })

            # Call LLM for expert conversational synthesis
            reply_text = ""
            try:
                synthesis_messages = list(messages)
                synthesis_messages.append({
                    "role": "system",
                    "content": "Подтверди операцию пользователю кратко, профессионально и по делу (категория, сумма, карта/счет, текущий остаток). Не используй лишних вежливых клише вроде 'Если у вас есть другие вопросы, дайте знать!'."
                })
                second_response = await self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=synthesis_messages,
                    temperature=0.2
                )
                reply_text = second_response.choices[0].message.content or ""
            except Exception as e:
                logger.warning(f"Error calling LLM for tool result synthesis: {e}")

            if not reply_text:
                # Generate clean fallback summary of recorded actions
                lines = []
                for a in actions_taken:
                    if a["type"] == "transaction_added":
                        sign = "-" if a["tx_type"] == "EXPENSE" else "+"
                        tx_line = (
                            f"✅ <b>Записано:</b> {a['category']} {sign}{a['amount']:,.0f} сум "
                            f"(Счет: {a['account']}, ост: {a['balance']:,.0f} сум)"
                        )
                        if a.get("budget_alert"):
                            tx_line += f"\n{a['budget_alert']}"
                        lines.append(tx_line)
                    elif a["type"] == "budget_set":
                        lines.append(f"📊 <b>Лимит установлен:</b> на категорию '{a['category']}' — {a['budget']:,.0f} сум в месяц.")
                    elif a["type"] == "funds_transferred":
                        lines.append(
                            f"🔄 <b>Перевод выполнен:</b> {a['amount']:,.0f} сум "
                            f"с '{a['from_account']}' на '{a['to_account']}'\n"
                            f"• {a['from_account']}: {a['from_balance']:,.0f} сум\n"
                            f"• {a['to_account']}: {a['to_balance']:,.0f} сум"
                        )
                    elif a["type"] == "transfer_failed":
                        lines.append(f"⚠️ Ошибка перевода: {a.get('error', 'не удалось выполнить')}")
                    elif a["type"] == "account_created":
                        if a["account_type"] == "CREDIT_CARD":
                            debt_val = abs(a['balance']) if a['balance'] < 0 else 0.0
                            name_lower = a['name'].lower()
                            is_inst = any(k in name_lower for k in ["рассрочк", "авто", "курс", "nasiya", "займ", "ипотек"]) or ("кредит" in name_lower and "карт" not in name_lower)
                            if is_inst:
                                paid = max(a['credit_limit'] - debt_val, 0.0)
                                icon = "🚗" if "авто" in name_lower else ("🎓" if "курс" in name_lower else "📦")
                                msg = (
                                    f"{icon} <b>Рассрочка / кредит взят на учет:</b> {a['name']}\n"
                                    f"• Общая стоимость: {a['credit_limit']:,.0f} сум\n"
                                    f"• Уже выплачено: {paid:,.0f} сум\n"
                                    f"• Остаток долга к выплате: <b>{debt_val:,.0f} сум</b>"
                                )
                            else:
                                debt_str = f"Долг: {debt_val:,.0f} сум" if a['balance'] < 0 else "Долга нет (0 сум)"
                                avail = max(a['credit_limit'] + a['balance'], 0.0)
                                msg = (
                                    f"💳 <b>Кредитная карта зарегистрирована:</b> {a['name']}\n"
                                    f"• Лимит: {a['credit_limit']:,.0f} сум | {debt_str}\n"
                                    f"• Доступно для покупок: {avail:,.0f} сум"
                                )
                                if a.get("grace_days", 0) > 0:
                                    msg += f" | Льготный период: {a['grace_days']} дней"
                        else:
                            msg = f"🏦 <b>Счет зарегистрирован:</b> {a['name']} — {a['balance']:,.0f} сум"
                            if a['interest_rate'] > 0:
                                msg += f" (Ставка {a['interest_rate']}%, пассивный доход: +{a['daily_yield']:,.0f} сум/день)"
                        lines.append(msg)
                    elif a["type"] == "goal_created":
                        d_str = f" до {a['target_date'].strftime('%d.%m.%Y')}" if a['target_date'] else ""
                        lines.append(f"🎯 <b>Цель поставлена:</b> {a['name']} на {a['target_amount']:,.0f} сум{d_str}")
                    elif a["type"] == "transaction_deleted":
                        lines.append(
                            f"🗑 <b>Операция отменена:</b> {a['category']} на {a['amount']:,.0f} сум. "
                            f"Баланс счета '{a['account']}' восстановлен: {a['balance']:,.0f} сум"
                        )
                    elif a["type"] == "transaction_delete_failed":
                        lines.append("⚠️ Не удалось найти транзакцию для отмены.")
                reply_text = "\n".join(lines)

            return {
                "text": reply_text,
                "actions": actions_taken
            }

        # If no tool calls, it was a conversational question / financial advisory question
        return {
            "text": choice.message.content or "Готово!",
            "actions": []
        }

