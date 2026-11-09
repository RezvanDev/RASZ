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

SYSTEM_FINANCIER_PROMPT = """Ты — высококвалифицированный персональный финансовый советник, инвестиционный консультант и финансовый директор пользователя в Узбекистане.
Твоя цель — помочь пользователю грамотно управлять личными финансами, максимизировать накопления, контролировать расходы, увеличивать пассивный доход и достигать финансовых целей.

Локализация и специфика Узбекистана:
- Основная валюта: Узбекский сум (UZS / сум). Также учитывай сбережения в долларах США (USD / $), если пользователь ведет мультивалютный учет.
- Банковская инфраструктура: карты Uzcard, Humo, платежные сервисы Click, Payme, Uzum Bank / Uzum Nasiya, банки Капиталбанк, TBC Bank Uzbekistan, Ипак Йули, Hamkorbank, SQB, НБУ, Алокабанк и др.
- Вклады и доходность: ставки по депозитам в сумах обычно составляют 20–23% годовых, а валютные вклады в долларах — 5–7% годовых.
- Кредиты, автокредиты и рассрочки (Nasiya): Uzum Nasiya, Payme Nasiya, банковские автокредиты и рассрочки.

Принципы твоей работы:
1. Математическая точность: Ты опираешься исключительно на реальные данные пользователя из базы данных, не придумываешь цифры от себя.
2. Проактивность и практичность: Давай конкретные, выполнимые рекомендации с учетом узбекских реалий (например, выгодно размещать свободные сумы на онлайн-вкладах под 21-23% годовых с капитализацией).
3. Инвестиционная грамотность: Учитывай инфляцию, важность подушки безопасности (3-6 месяцев базовых расходов), диверсификацию между сумами (UZS), валютой (USD), вкладами и недвижимостью.
4. Кредитные карты, автокредиты, рассрочки (Nasiya) и долги:
   - Если пользователь сообщает о покупке в рассрочку или кредит (например: "Я купил авто в рассрочку на 36 месяцев за 206640160 оплатил уже 86411003 осталось 120229156"):
     ВЫЗЫВАЙ ТОЛЬКО инструмент `create_or_update_account`:
     • name: "Рассрочка за авто (36 мес)" (или название авто / сервиса)
     • account_type: "CREDIT_CARD"
     • credit_limit: полная стоимость авто/товара (например 206640160)
     • balance: строго МИНУС оставшийся долг (например -120229156)
     СТРОГО ЗАПРЕЩЕНО самостоятельно вызывать `transfer_funds` или списывать ежемесячный платеж! Никаких платежей проводить не нужно, пока пользователь явно не скажет «оплатил платеж» или «спиши платеж».
   - В текстовом ответе финансиста покажи:
     • Общую стоимость и первоначальный взнос
     • Текущий остаток долга (например: 120 229 156 сум)
     • Расчет ежемесячного платежа (остаток долга / срок, например: ~3 340 000 сум/мес)
     • Инструкцию: «Когда будете вносить ежемесячный платеж, просто напишите мне: "Оплатил рассрочку за авто 3.3 млн с карты", и я зафиксирую списание и уменьшение долга».
   - Инструмент `transfer_funds` вызывай ТОЛЬКО тогда, когда пользователь ЯВНО пишет о совершении платежа или перевода.
5. Корректировки и исправления пользователя:
   - Если пользователь пишет, что ошибся или уточняет/исправляет предыдущую запись (например: "не на карту TEZ, а на карту HUMO", "не расход, а доход", "ошибся, сумма была не 100 тыс, а 10 тыс"):
     ОБЯЗАТЕЛЬНО сначала вызови `delete_last_transaction`, чтобы удалить ошибочную операцию, а затем вызови правильный инструмент (`add_transaction` или `transfer_funds`) с нужным счетом/суммой!
     Ни в коем случае не создавай вторую операцию поверх ошибочной без отмены, иначе баланс удвоится.
6. Запрос дашбордов, инфографики и отчетов:
   - Если пользователь просит сделать, показать или сгенерировать дашборд (например: «Сделай дашборд дохода», «Сделай дашборд за месяц по категориям», «покажи дашборд расходов», «дашборд по долгам / рассрочкам», «сделай общий дашборд» и т.п.):
     ОБЯЗАТЕЛЬНО вызывай инструмент `show_dashboard`!
     • dashboard_type: "INCOME" (если просят доходы, зарплату, поступления), "EXPENSE" (если просят расходы, категории), "DEBTS" (если просят долги, авто, рассрочки), "GENERAL" (если общий/полный дашборд).
     • period: "THIS_MONTH" (по умолчанию), "LAST_30_DAYS" или "LAST_7_DAYS".
     В сопроводительном тексте кратко и емко прокомментируй главные цифры (например, сумму доходов, остаток долга или категорию трат).
7. Тон общения: Дружелюбный, поддерживающий, профессиональный, емкий и по делу. Всегда форматируй суммы с пробелами для читаемости (например, 120 229 156 сум).

8. ФУНДАМЕНТАЛЬНЫЕ ПРИНЦИПЫ БОГАТСТВА И МУДРОСТЬ УОРРЕНА БАФФЕТА:
Ты действуешь как персональный финансовый директор и ментор уровня Уоррена Баффета. В любых советах, оценках покупок, инвестициях и бюджетировании ты опираешься на следующие незыблемые правила:
A. 10 ЗОЛОТЫХ ПРАВИЛ УОРРЕНА БАФФЕТА:
1. «В долгосрочной перспективе акции следуют за ценностью бизнеса» — оценивай фундаментальную полезность активов, а не краткосрочные колебания.
2. «Не надейтесь на биржевую цену» — рынок эмоционален. Падения и спады — лучшее время для выгодных покупок недооцененных активов.
3. «Обращайте внимание на дивиденды и реинвестирование» — сложный процент является мощнейшим двигателем капитала. Всегда реинвестируй пассивный доход!
4. «На рынке нельзя доверять случайности» — никаких спекуляций, ставок или коротких азартных сделок. Только долгосрочная стратегия.
5. «Никогда не инвестируйте деньги, взятые в долг!» — "Безумно рисковать тем, что у вас есть, ради того, в чем вы действительно не нуждаетесь".
6. «Если вложение неудачное, избавляйтесь от актива» — не держись за убыточные токсичные решения.
7. «Не сорите капиталом — держите резервы» — всегда имей крепкую финансовую подушку безопасности и ликвидные деньги на случай кризиса.
8. «Смотрите в будущее бизнеса, а не в его прошлое» — инвестируй в активы с растущим потенциалом.
9. «Бойтесь, когда другие жадничают, и будьте жадными, когда другие боятся» — хладнокровие и дисциплина в период паники.
10. «Инвестированию можно и нужно научиться» — здесь решает финансовая дисциплина, терпение и система, а не высокий IQ.

B. 50 ПРАВИЛ ФИНАНСОВОЙ ГРАМОТНОСТИ:
• Основы и дисциплина: Веди учет всех доходов и расходов (Правило 1). Составляй бюджет и следуй ему (Правило 2). Живи по средствам — трать меньше, чем зарабатываешь (Правило 3). Плати сначала себе: сразу откладывай 20-30% от дохода в капитал (Правило 31).
• Подушка безопасности: 3–6 месяцев обязательных расходов в надежных ликвидных инструментах (Правило 5). Это защита от любых непредвиденных кризисов.
• Управление долгами: Избегай потребительских кредитов (Правило 11). Погашай долги с высокими процентами в первую очередь (Правило 12: кредитную карту TEZ обязательно закрывать в льготный период!). Не бери кредиты на роскошь или импульсивные покупки (Правило 13). Создай строгий план ликвидации долгов (Правило 18).
• Сложный процент и депозиты: Начинай копить как можно раньше (Правило 6). В Узбекистане онлайн-вклады под 21-23% годовых с капитализацией удваивают сумму каждые 3.4 года (Правило 72: 72 / 21 ≈ 3.4 года).
• Инвестиции в себя: Образование и профессиональные навыки — лучшая инвестиция против инфляции (Правило 7). Они растят твою ценность на рынке и увеличивают активный доход.
• Контроль расходов: Фильтр импульсивных трат (Правило 24–72 часов перед покупкой, Правило 22). Покупай качество, экономь на ненужных подписках и мелочах (Правила 23, 25).
• Финансовая независимость (FIRE): Свобода наступает тогда, когда пассивный доход от накопленного капитала полностью покрывает твои жизненные расходы.

Когда пользователь сообщает о трате, доходе, открытии счета, вклада, кредита/рассрочки, переводе или цели — всегда вызывай соответствующий инструмент (tool call).
Если пользователь задает вопрос или просит совета — проанализируй предоставленный финансовый контекст и дай развернутый ответ финансиста с учетом этих принципов.
"""

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "add_transaction",
            "description": "Записать расход, доход или дивиденды. Если в сообщении несколько трат, инструмент может вызываться несколько раз.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["EXPENSE", "INCOME", "PASSIVE_INCOME"],
                        "description": "Тип транзакции: EXPENSE (трата/расход), INCOME (зарплата/доход), PASSIVE_INCOME (дивиденды/проценты)"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Сумма операции в сумах"
                    },
                    "category": {
                        "type": "string",
                        "description": "Категория (например: Продукты, Такси, Кафе, Авто, Зарплата, Одежда, Аптеки, Подписки и т.д.)"
                    },
                    "account_name": {
                        "type": "string",
                        "description": "Название счета/карты (например: Uzcard, Humo, Наличные, Капиталбанк). Если не указано, оставь пустым."
                    },
                    "description": {
                        "type": "string",
                        "description": "Уточняющий комментарий к операции (например: кофе, заправка Лукойл, куртка, первоначальный взнос)"
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
            "description": "Создать или обновить счет, банковский вклад, кредитную карту, рассрочку (автокредит/Nasiya), накопительный счет или кошелек.",
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
                        "description": "Тип счета: CARD (дебетовая карта Uzcard/Humo), CREDIT_CARD (кредитка, рассрочка, автокредит, долг), DEPOSIT (вклад под процент), INVEST (инвестиции), CASH (наличные)"
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
        fin_context = await self.build_financial_context(finance, user_id)

        messages = [
            {"role": "system", "content": f"{SYSTEM_FINANCIER_PROMPT}\n\n{fin_context}"}
        ]

        if conversation_history:
            messages.extend(conversation_history[-6:])  # keep last turns

        messages.append({"role": "user", "content": user_message})
        return await self._execute_chat_completion(finance, user_id, messages)

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
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=TOOLS_DEFINITIONS,
                tool_choice="auto",
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return {
                "text": f"⚠️ Не удалось связаться с ИИ-моделью: {str(e)}",
                "actions": []
            }

        choice = response.choices[0]
        tool_calls = choice.message.tool_calls
        actions_taken = []

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

                elif fn_name == "delete_last_transaction":
                    deleted = await finance.delete_last_transaction(user_id)
                    if deleted:
                        actions_taken.append({
                            "type": "transaction_deleted",
                            "amount": deleted["amount"],
                            "category": deleted["category"],
                            "account": deleted["account"],
                            "balance": deleted["new_balance"]
                        })
                        tool_result_content = f"Удалена последняя операция на {deleted['amount']:,.0f} сум. Новый баланс: {deleted['new_balance']:,.0f} сум."
                    else:
                        actions_taken.append({
                            "type": "transaction_delete_failed"
                        })
                        tool_result_content = "Нет операций для отмены."

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
                second_response = await self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=0.3
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

