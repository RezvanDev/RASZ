from bot.services.chart_service import ChartService

def test_html():
    stats = {
        'total_expense': 0.0,
        'total_income': 12000000.0,
        'total_passive': 0.0,
        'full_income': 12000000.0,
        'savings': 12000000.0,
        'savings_rate': 100.0,
        'daily_avg_expense': 0.0,
        'runway_months': 0.0,
        'categories': [],
        'period_days': 8
    }
    class Acc:
        def __init__(self, name, acc_type, bal, limit=0, grace=0, rate=0):
            self.name = name
            self.account_type = type('T', (), {'value': acc_type})
            self.balance = bal
            self.credit_limit = limit
            self.grace_period_days = grace
            self.interest_rate = rate
            self.currency = "UZS"

    summary = {
        'total_balance': -124283373.0,
        'total_assets': 12000000.0,
        'total_debt': 136283373.0,
        'liquid_balance': 12000000.0,
        'deposits_balance': 0.0,
        'invest_balance': 0.0,
        'annual_yield': 0.0,
        'monthly_yield': 0.0,
        'daily_yield': 0.0,
        'accounts': [
            Acc('Humo / Uzcard (Зарплатная)', 'CARD', 12000000.0),
            Acc('Рассрочка за авто (36 мес)', 'CREDIT_CARD', -120229156.0, 206640160.0),
            Acc('Курс на Skillbox Архитектор ПО (10 мес)', 'CREDIT_CARD', -5000000.0, 6000000.0),
            Acc('Кредитная карта TEZ', 'CREDIT_CARD', -11054217.0, 22000000.0, 62)
        ],
        'credit_cards': [
            {'debt': 120229156.0, 'limit': 206640160.0, 'available': 86411004.0, 'account': Acc('Рассрочка за авто (36 мес)', 'CREDIT_CARD', -120229156.0, 206640160.0)},
            {'debt': 5000000.0, 'limit': 6000000.0, 'available': 1000000.0, 'account': Acc('Курс на Skillbox Архитектор ПО (10 мес)', 'CREDIT_CARD', -5000000.0, 6000000.0)},
            {'debt': 11054217.0, 'limit': 22000000.0, 'available': 10945783.0, 'account': Acc('Кредитная карта TEZ', 'CREDIT_CARD', -11054217.0, 22000000.0, 62)}
        ]
    }
    html = ChartService.generate_interactive_html(stats, summary, "текущий месяц")
    with open("data/test_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML generated, size:", len(html))

if __name__ == "__main__":
    test_html()

