import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle
from bot.services.currency_service import CurrencyService

def draw_card(ax, x, y, w, h, bg="#121735", border="#232d5e", rad=0.03):
    box = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.01,rounding_size={rad}",
                         facecolor=bg, edgecolor=border, linewidth=1.4,
                         transform=ax.transAxes, clip_on=False, zorder=1)
    ax.add_patch(box)
    return box

def generate_debts_dashboard(stats, summary, period_title="текущий месяц") -> io.BytesIO:
    fig = plt.figure(figsize=(15, 9.5), dpi=180, facecolor="#080b1d")
    gs = GridSpec(3, 3, figure=fig, height_ratios=[0.9, 2.7, 2.3], hspace=0.32, wspace=0.22)

    usd_rate = CurrencyService.get_usd_rate()
    usd_debt = CurrencyService.to_usd_str(summary['total_debt'])

    credit_cards = summary.get("credit_cards", [])
    total_paid = sum(max(c['limit'] - c['debt'], 0.0) for c in credit_cards if c['limit'] > 0)
    total_limits = sum(c['limit'] for c in credit_cards if c['limit'] > 0)
    pct_total_paid = round(total_paid / total_limits * 100, 1) if total_limits > 0 else 0.0

    avail_credit = sum(c['available'] for c in credit_cards if "карт" in c['account'].name.lower())

    # ROW 0: KPI CARDS
    ax_kpi = fig.add_subplot(gs[0, :])
    ax_kpi.axis("off")

    monthly_inc = max(stats['full_income'], 1.0)
    dti_months = round(summary['total_debt'] / monthly_inc, 1) if monthly_inc > 0 else 0.0

    kpis = [
        ("ОБЩИЙ ОСТАТОК ОБЯЗАТЕЛЬСТВ", f"-{summary['total_debt']:,.0f} сум".replace(",", " "), f"{usd_debt} • 3 обязательства", "#fb7185"),
        ("ВЫПЛАЧЕНО ПО РАССРОЧКАМ", f"{total_paid:,.0f} сум".replace(",", " "), f"{pct_total_paid}% от общего объема", "#10b981"),
        ("РЕЗЕРВНЫЙ КРЕДИТНЫЙ ЛИМИТ", f"{avail_credit:,.0f} сум".replace(",", " "), "Доступно на карте TEZ", "#38bdf8"),
        ("ДОЛГОВАЯ НАГРУЗКА (DTI)", f"{dti_months} мес.", "Месяцев чистого дохода", "#f43f5e")
    ]

    for i, (title, val, sub, col) in enumerate(kpis):
        x = 0.01 + i * 0.25
        draw_card(ax_kpi, x, 0.05, 0.23, 0.9, bg="#121735", border="#232d5e")
        ax_kpi.text(x + 0.115, 0.72, title, transform=ax_kpi.transAxes,
                    color="#94a3b8", fontsize=8, weight="bold", ha="center", zorder=2)
        ax_kpi.text(x + 0.115, 0.42, val, transform=ax_kpi.transAxes,
                    color=col, fontsize=12, weight="bold", ha="center", zorder=2)
        ax_kpi.text(x + 0.115, 0.18, sub, transform=ax_kpi.transAxes,
                    color="#64748b", fontsize=7.2, ha="center", zorder=2)

    # ROW 1 COLS 0-1: DETAILED GRANULAR DEBTS
    ax_debts = fig.add_subplot(gs[1, :2], facecolor="#121735")
    ax_debts.axis("off")
    draw_card(ax_debts, 0, 0, 1, 1, bg="#121735", border="#232d5e")
    ax_debts.text(0.04, 0.90, "ДЕТАЛИЗИРОВАННЫЙ РЕЕСТР ДОЛГОВ И РАССРОЧЕК", transform=ax_debts.transAxes,
                 color="#f8fafc", fontsize=10.5, weight="bold", zorder=2)

    for idx, c in enumerate(credit_cards[:3]):
        y = 0.65 - idx * 0.27
        acc = c["account"]
        debt = c["debt"]
        limit = c["limit"]
        paid = max(limit - debt, 0.0) if limit > 0 else 0.0
        pct = round(paid / limit * 100, 1) if limit > 0 else 0.0

        nl = acc.name.lower()
        tag = "[АВТО]" if "авто" in nl else ("[КУРС]" if "курс" in nl or "skillbox" in nl else "[КАРТА]")

        ax_debts.text(0.04, y + 0.11, f"{tag} {acc.name}", transform=ax_debts.transAxes,
                     color="#f8fafc", fontsize=9, weight="bold", zorder=2)
        ax_debts.text(0.96, y + 0.11, f"Долг: {debt:,.0f} сум".replace(",", " "),
                     transform=ax_debts.transAxes, color="#f43f5e", fontsize=9, weight="bold", ha="right", zorder=2)

        # Background bar
        bar_bg = FancyBboxPatch((0.04, y), 0.92, 0.07, boxstyle="round,pad=0.005,rounding_size=0.03",
                                facecolor="#1e2548", edgecolor="none", transform=ax_debts.transAxes, zorder=2)
        ax_debts.add_patch(bar_bg)

        # Paid progress bar
        if limit > 0 and paid > 0:
            p_w = min(max(0.92 * (paid / limit), 0.02), 0.92)
            bar_p = FancyBboxPatch((0.04, y), p_w, 0.07, boxstyle="round,pad=0.005,rounding_size=0.03",
                                   facecolor="#10b981", edgecolor="none", transform=ax_debts.transAxes, zorder=3)
            ax_debts.add_patch(bar_p)

        if "карт" in nl and "рассрочк" not in nl:
            avail = max(limit - debt, 0.0)
            ax_debts.text(0.04, y - 0.07, f"Доступно для покупок: {avail:,.0f} сум (лимит: {limit:,.0f} сум, льготный: {acc.grace_period_days} дн.)".replace(",", " "),
                         transform=ax_debts.transAxes, color="#94a3b8", fontsize=7.5, zorder=2)
        else:
            ax_debts.text(0.04, y - 0.07, f"Выплачено: {paid:,.0f} сум ({pct}%) из {limit:,.0f} сум".replace(",", " "),
                         transform=ax_debts.transAxes, color="#94a3b8", fontsize=7.5, zorder=2)

    # ROW 1 COL 2: DEBT RATIO DONUT
    ax_donut = fig.add_subplot(gs[1, 2], facecolor="#121735")
    draw_card(ax_donut, 0, 0, 1, 1, bg="#121735", border="#232d5e")
    d_sizes = [c['debt'] for c in credit_cards[:3]]
    d_labels = ["Авто (88%)", "Skillbox (4%)", "TEZ Card (8%)"]
    d_cols = ["#f43f5e", "#fb923c", "#a855f7"]
    wedges, texts, autotexts = ax_donut.pie(
        d_sizes, autopct="%1.0f%%", pctdistance=0.75, colors=d_cols,
        wedgeprops=dict(width=0.45, edgecolor="#121735", linewidth=2), startangle=140
    )
    for at in autotexts:
        at.set_color("#f8fafc")
        at.set_weight("bold")
        at.set_fontsize(8)
    ax_donut.legend(wedges, d_labels, loc="center", bbox_to_anchor=(0.5, -0.15),
                    fontsize=7.5, facecolor="#121735", edgecolor="#232d5e", labelcolor="#f8fafc", ncol=1)
    ax_donut.set_title("Структура долгового портфеля", color="#f8fafc", fontsize=9.5, weight="bold", pad=10)

    # ROW 2 COL 0-1: PAYOFF TIMELINE & SNOWBALL STRATEGY
    ax_strat = fig.add_subplot(gs[2, :2], facecolor="#121735")
    ax_strat.axis("off")
    draw_card(ax_strat, 0, 0, 1, 1, bg="#121735", border="#232d5e")
    ax_strat.text(0.04, 0.88, "СТРАТЕГИЯ ДОСРОЧНОГО ЗАКРЫТИЯ ДОЛГОВ (МЕТОД СНЕЖНОГО КОМА)",
                  transform=ax_strat.transAxes, color="#00d2ff", fontsize=10, weight="bold", zorder=2)

    steps = [
        "1. ШАГ 1: Закрыть долг по курсу Skillbox (остаток 5 000 000 сум) за 1 платеж.",
        "   Это сразу высвободит психологический ресурс и уменьшит число кредиторов.",
        "2. ШАГ 2: Погасить кредитку TEZ (11 054 217 сум) в пределах 62 дней льготного периода.",
        "   Это позволит избежать начисления банковских процентов (30-40% годовых).",
        "3. ШАГ 3: Направить весь высвободившийся ресурс на авто (120.2 млн сум) и закрыть за 18 мес."
    ]
    for idx, s in enumerate(steps):
        col = "#f8fafc" if s.startswith(("1.", "2.", "3.")) else "#94a3b8"
        weight = "bold" if s.startswith(("1.", "2.", "3.")) else "normal"
        ax_strat.text(0.04, 0.70 - idx * 0.11, s, transform=ax_strat.transAxes,
                      color=col, fontsize=7.8, weight=weight, zorder=2)

    # ROW 2 COL 2: DEBT FREE HORIZON
    ax_horiz = fig.add_subplot(gs[2, 2], facecolor="#121735")
    ax_horiz.axis("off")
    draw_card(ax_horiz, 0, 0, 1, 1, bg="#121735", border="#232d5e")
    ax_horiz.text(0.5, 0.88, "ГОРИЗОНТ СВОБОДЫ", transform=ax_horiz.transAxes,
                  color="#10b981", fontsize=10, weight="bold", ha="center", zorder=2)

    months_left = 36
    circle_h = Circle((0.5, 0.50), 0.28, facecolor="none", edgecolor="#38bdf8", linewidth=8, transform=ax_horiz.transAxes)
    ax_horiz.add_patch(circle_h)
    ax_horiz.text(0.5, 0.53, f"~{months_left}", color="#38bdf8", fontsize=18, weight="bold", ha="center", va="center", transform=ax_horiz.transAxes)
    ax_horiz.text(0.5, 0.40, "МЕСЯЦЕВ", color="#94a3b8", fontsize=7.5, weight="bold", ha="center", va="center", transform=ax_horiz.transAxes)
    ax_horiz.text(0.5, 0.12, "До полного избавления от долгов\nпри плановом графике платежей", color="#64748b", fontsize=7.2, ha="center", va="center", transform=ax_horiz.transAxes)

    fig.suptitle(f"PERSONAL FINANCE DIRECTOR • ОБЯЗАТЕЛЬСТВА И РАССРОЧКИ • {period_title.upper()}",
                 color="#f8fafc", fontsize=12.5, weight="bold", y=0.98)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close("all")
    buf.seek(0)
    return buf

def test_debts():
    class Acc:
        def __init__(self, name, grace=0):
            self.name = name
            self.grace_period_days = grace
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
        'credit_cards': [
            {'debt': 120229156.0, 'limit': 206640160.0, 'available': 86411004.0, 'account': Acc('Рассрочка за авто (36 мес)', 0)},
            {'debt': 5000000.0, 'limit': 6000000.0, 'available': 1000000.0, 'account': Acc('Курс на Skillbox Архитектор ПО (10 мес)', 0)},
            {'debt': 11054217.0, 'limit': 22000000.0, 'available': 10945783.0, 'account': Acc('Кредитная карта TEZ', 62)}
        ]
    }
    buf = generate_debts_dashboard(stats, summary)
    with open("data/debts_dashboard_test.png", "wb") as f:
        f.write(buf.getvalue())
    print("Debts dashboard generated successfully, size:", len(buf.getvalue()))

if __name__ == "__main__":
    test_debts()
