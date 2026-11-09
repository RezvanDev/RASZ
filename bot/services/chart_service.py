import io
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
from typing import List, Dict, Any, Optional, Tuple
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless server execution
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle

from bot.services.currency_service import CurrencyService

class ChartService:
    @staticmethod
    def _draw_card(ax, x, y, w, h, bg="#121735", border="#232d5e", rad=0.03):
        box = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.01,rounding_size={rad}",
                             facecolor=bg, edgecolor=border, linewidth=1.4,
                             transform=ax.transAxes, clip_on=False, zorder=1)
        ax.add_patch(box)
        return box

    @staticmethod
    def generate_expense_pie_chart(categories: List[Dict[str, Any]], title: str = "Структура расходов") -> Optional[io.BytesIO]:
        """
        Generates a modern donut chart of expenses by category.
        """
        if not categories:
            return None

        top_cats = categories[:6]
        other_cats = categories[6:]

        labels = []
        sizes = []
        for cat in top_cats:
            labels.append(f"{cat['name']} ({cat['percent']}%)")
            sizes.append(cat['amount'])

        if other_cats:
            other_amount = sum(c['amount'] for c in other_cats)
            other_pct = round(sum(c['percent'] for c in other_cats), 1)
            labels.append(f"Другое ({other_pct}%)")
            sizes.append(other_amount)

        colors = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1"]
        slice_colors = colors[:len(labels)]

        plt.figure(figsize=(8, 6), dpi=150)
        fig, ax = plt.subplots(figsize=(8, 6), subplot_kw=dict(aspect="equal"))

        wedges, texts, autotexts = ax.pie(
            sizes,
            autopct=lambda pct: f"{pct:.1f}%" if pct > 4 else "",
            pctdistance=0.75,
            colors=slice_colors,
            wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
            startangle=140
        )

        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_weight("bold")
            autotext.set_fontsize(10)

        ax.legend(
            wedges,
            labels,
            title="Категории",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=9
        )

        plt.title(title, fontsize=14, weight="bold", pad=20)
        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight")
        plt.close("all")
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_full_dashboard(stats: Dict[str, Any], summary: Dict[str, Any], period_title: str) -> io.BytesIO:
        """
        Generates an Executive Financial Infographic Dashboard (Dark Luxury Fintech Theme).
        - 4 Glowing KPI Metric Tiles (Net Worth, Income, Expenses, Total Debt)
        - Virtual Bank Card (Humo / Uzcard) with Gold Chip & Real Balance
        - Donut Category Breakdown & Savings Ratio
        - Cashflow Bar Comparison with Clean Values
        - Granular Debts & Installments Breakdown (Car, Course, Credit Card with % Paid vs % Left)
        - Wealth Pulse & Advisory Indicators
        """
        fig = plt.figure(figsize=(16, 11), dpi=190, facecolor="#080b1d")
        gs = GridSpec(3, 3, figure=fig, height_ratios=[0.9, 2.5, 2.8], hspace=0.32, wspace=0.22)

        usd_rate = CurrencyService.get_usd_rate()
        usd_net_worth = CurrencyService.to_usd_str(summary['total_balance'])

        # ---------------- ROW 0: TOP 4 KPI CARDS ----------------
        ax_kpi = fig.add_subplot(gs[0, :])
        ax_kpi.axis("off")

        nw_val = summary['total_balance']
        nw_col = "#38bdf8" if nw_val >= 0 else "#f43f5e"
        nw_sign = "+" if nw_val > 0 else ""

        debt_cards = summary.get("credit_cards", [])
        debt_count_str = f"{len(debt_cards)} активных обязательства" if debt_cards else "Обязательств нет"

        kpis = [
            ("ЧИСТЫЙ КАПИТАЛ", f"{nw_sign}{nw_val:,.0f} сум".replace(",", " "), f"{usd_net_worth} • Активы - Долги", nw_col),
            ("ДОХОДЫ ЗА МЕСЯЦ", f"+{stats['full_income']:,.0f} сум".replace(",", " "), f"Пассивный доход: +{stats['total_passive']:,.0f} сум".replace(",", " "), "#10b981"),
            ("РАСХОДЫ ЗА МЕСЯЦ", f"-{stats['total_expense']:,.0f} сум".replace(",", " "), f"В день: {stats['daily_avg_expense']:,.0f} сум".replace(",", " "), "#cbd5e1" if stats['total_expense'] == 0 else "#f43f5e"),
            ("ОБЩИЙ ДОЛГ / ОБЯЗАТЕЛЬСТВА", f"-{summary['total_debt']:,.0f} сум".replace(",", " "), debt_count_str, "#fb7185")
        ]

        for i, (title, val, sub, col) in enumerate(kpis):
            x = 0.01 + i * 0.25
            ChartService._draw_card(ax_kpi, x, 0.05, 0.23, 0.9, bg="#121735", border="#232d5e")
            ax_kpi.text(x + 0.115, 0.72, title, transform=ax_kpi.transAxes,
                        color="#94a3b8", fontsize=8.5, weight="bold", ha="center", zorder=2)
            ax_kpi.text(x + 0.115, 0.42, val, transform=ax_kpi.transAxes,
                        color=col, fontsize=12, weight="bold", ha="center", zorder=2)
            ax_kpi.text(x + 0.115, 0.18, sub, transform=ax_kpi.transAxes,
                        color="#64748b", fontsize=7.5, ha="center", zorder=2)

        # ---------------- ROW 1 COL 0: CATEGORIES DONUT / BUDGET GAUGE ----------------
        ax_donut = fig.add_subplot(gs[1, 0], facecolor="#121735")
        ChartService._draw_card(ax_donut, 0, 0, 1, 1, bg="#121735", border="#232d5e")

        categories = stats.get("categories", [])
        if categories:
            top_cats = categories[:5]
            other_cats = categories[5:]
            labels = [f"{c['name']} ({c['percent']}%)" for c in top_cats]
            sizes = [c['amount'] for c in top_cats]
            if other_cats:
                labels.append(f"Другое ({round(sum(c['percent'] for c in other_cats), 1)}%)")
                sizes.append(sum(c['amount'] for c in other_cats))

            palette = ["#38bdf8", "#fbbf24", "#f43f5e", "#10b981", "#a855f7", "#f472b6"]
            wedges, texts, autotexts = ax_donut.pie(
                sizes,
                autopct=lambda p: f"{p:.0f}%" if p > 5 else "",
                pctdistance=0.75,
                colors=palette[:len(sizes)],
                wedgeprops=dict(width=0.42, edgecolor="#121735", linewidth=2.5),
                startangle=140
            )
            for autotext in autotexts:
                autotext.set_color("#080b1d")
                autotext.set_weight("bold")
                autotext.set_fontsize(8.5)

            ax_donut.legend(wedges, labels, loc="center", bbox_to_anchor=(0.5, -0.18),
                            fontsize=7.5, facecolor="#121735", edgecolor="#232d5e", labelcolor="#f8fafc", ncol=2)
            ax_donut.set_title(f"Структура расходов ({period_title})", color="#f8fafc", fontsize=9.5, weight="bold", pad=10)
        else:
            circle = Circle((0.5, 0.52), 0.32, facecolor="none", edgecolor="#10b981", linewidth=7, transform=ax_donut.transAxes)
            ax_donut.add_patch(circle)
            ax_donut.text(0.5, 0.56, f"{stats['savings_rate']:.0f}%", color="#10b981", fontsize=16, weight="bold", ha="center", va="center", transform=ax_donut.transAxes)
            ax_donut.text(0.5, 0.44, "СБЕРЕЖЕНИЯ", color="#94a3b8", fontsize=7.5, weight="bold", ha="center", va="center", transform=ax_donut.transAxes)
            ax_donut.text(0.5, 0.14, "Расходов за период нет\nВсе средства направлены в накопления", color="#64748b", fontsize=7.5, ha="center", va="center", transform=ax_donut.transAxes)
            ax_donut.set_title(f"Контроль бюджета ({period_title})", color="#f8fafc", fontsize=9.5, weight="bold", pad=10)
            ax_donut.axis("off")

        # ---------------- ROW 1 COL 1: CASHFLOW BARS ----------------
        ax_cf = fig.add_subplot(gs[1, 1], facecolor="#121735")
        for spine in ax_cf.spines.values():
            spine.set_color("#232d5e")
        cf_labels = ["Доходы", "Расходы", "Сбережения"]
        cf_vals = [stats['full_income'], stats['total_expense'], max(stats['savings'], 0.0)]
        cf_cols = ["#10b981", "#f43f5e", "#00d2ff"]

        bars = ax_cf.bar(cf_labels, cf_vals, color=cf_cols, width=0.45, zorder=3, edgecolor="#080b1d", linewidth=1.2)
        ax_cf.grid(axis="y", linestyle="--", alpha=0.15, color="#f8fafc", zorder=0)
        ax_cf.tick_params(colors="#94a3b8", labelsize=8.5)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax_cf.annotate(
                    f"{int(h):,} сум".replace(",", " "),
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points",
                    ha="center", va="bottom",
                    fontweight="bold", fontsize=7.8, color="#f8fafc"
                )
        ax_cf.set_title("Денежный поток (Cashflow)", color="#f8fafc", fontsize=9.5, weight="bold", pad=12)

        # ---------------- ROW 1 COL 2: VIRTUAL CARD WIDGET ----------------
        ax_card = fig.add_subplot(gs[1, 2])
        ax_card.axis("off")
        ChartService._draw_card(ax_card, 0.02, 0.02, 0.96, 0.96, bg="#121735", border="#232d5e")

        primary_card_name = "HUMO / UZCARD"
        primary_balance = summary['liquid_balance']
        for a in summary.get("accounts", []):
            if a.account_type.value in ("CARD", "CASH") and a.balance > 0:
                primary_card_name = a.name.upper()
                primary_balance = a.balance
                break

        c_bg = FancyBboxPatch((0.08, 0.12), 0.84, 0.76, boxstyle="round,pad=0.01,rounding_size=0.06",
                              facecolor="#1c1642", edgecolor="#4c1d95", linewidth=1.5,
                              transform=ax_card.transAxes, clip_on=False, zorder=2)
        ax_card.add_patch(c_bg)

        chip = Rectangle((0.14, 0.58), 0.14, 0.14, facecolor="#eab308", edgecolor="#ca8a04",
                         transform=ax_card.transAxes, zorder=3)
        ax_card.add_patch(chip)

        ax_card.text(0.86, 0.72, "HUMO", transform=ax_card.transAxes, color="#f8fafc",
                    fontsize=10.5, weight="bold", ha="right", zorder=3)
        ax_card.text(0.14, 0.43, "•••• •••• •••• 4821", transform=ax_card.transAxes,
                    color="#94a3b8", fontsize=9, fontfamily="monospace", zorder=3)
        ax_card.text(0.14, 0.28, f"{primary_balance:,.0f} сум".replace(",", " "), transform=ax_card.transAxes,
                    color="#34d399", fontsize=11.5, weight="bold", zorder=3)
        ax_card.text(0.14, 0.18, f"{primary_card_name[:20]} • ЛИКВИДНЫЙ АКТИВ", transform=ax_card.transAxes,
                    color="#cbd5e1", fontsize=6.5, weight="bold", zorder=3)
        ax_card.text(0.5, 0.94, "Основная карта и активы", transform=ax_card.transAxes,
                    color="#f8fafc", fontsize=9.5, weight="bold", ha="center")

        # ---------------- ROW 2 COLS 0-1: DETAILED DEBTS BREAKDOWN ----------------
        ax_debts = fig.add_subplot(gs[2, :2], facecolor="#121735")
        ax_debts.axis("off")
        ChartService._draw_card(ax_debts, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_debts.text(0.04, 0.90, "ДЕТАЛИЗАЦИЯ ОБЯЗАТЕЛЬСТВ И РАССРОЧЕК", transform=ax_debts.transAxes,
                     color="#f8fafc", fontsize=10.5, weight="bold", zorder=2)

        if debt_cards:
            debts_to_show = debt_cards[:3]
            for idx, c in enumerate(debts_to_show):
                y = 0.65 - idx * 0.27
                acc = c["account"]
                debt = c["debt"]
                limit = c["limit"]
                paid = max(limit - debt, 0.0) if limit > 0 else 0.0
                pct = round(paid / limit * 100, 1) if limit > 0 else 0.0

                clean_name = acc.name
                if len(clean_name) > 36:
                    clean_name = clean_name[:34] + "…"

                nl = clean_name.lower()
                tag = "[АВТО]" if "авто" in nl else ("[КУРС]" if "курс" in nl or "skillbox" in nl else "[КАРТА]")

                ax_debts.text(0.04, y + 0.11, f"{tag} {clean_name}", transform=ax_debts.transAxes,
                             color="#f8fafc", fontsize=8.5, weight="bold", zorder=2)
                ax_debts.text(0.96, y + 0.11, f"Остаток: {debt:,.0f} сум".replace(",", " "),
                             transform=ax_debts.transAxes, color="#f43f5e", fontsize=8.5, weight="bold", ha="right", zorder=2)

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

                # Subtext
                if "карт" in nl and "рассрочк" not in nl:
                    avail = max(limit - debt, 0.0)
                    ax_debts.text(0.05, y - 0.06, f"Доступно для покупок: {avail:,.0f} сум (лимит: {limit:,.0f} сум)".replace(",", " "),
                                 transform=ax_debts.transAxes, color="#94a3b8", fontsize=7.2, zorder=2)
                else:
                    ax_debts.text(0.05, y - 0.06, f"Выплачено: {paid:,.0f} сум ({pct}%) из {limit:,.0f} сум".replace(",", " "),
                                 transform=ax_debts.transAxes, color="#94a3b8", fontsize=7.2, zorder=2)
        else:
            ax_debts.text(0.5, 0.5, "Активных кредитов и рассрочек нет. Отличная финансовая свобода!",
                         color="#34d399", fontsize=9, ha="center", va="center", transform=ax_debts.transAxes)

        # ---------------- ROW 2 COL 2: WEALTH HEALTH PULSE ----------------
        ax_pulse = fig.add_subplot(gs[2, 2], facecolor="#121735")
        ax_pulse.axis("off")
        ChartService._draw_card(ax_pulse, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_pulse.text(0.08, 0.88, "ФИНАНСОВЫЙ ПУЛЬС", transform=ax_pulse.transAxes,
                     color="#00d2ff", fontsize=10, weight="bold", zorder=2)

        monthly_inc = max(stats['full_income'], 1.0)
        dti_months = round(summary['total_debt'] / monthly_inc, 1) if monthly_inc > 0 else 0.0
        runway_str = f"{stats['runway_months']} мес." if stats['runway_months'] > 0 else "Бессрочно (нет трат)"

        pulse_items = [
            ("Подушка безопасности (Runway):", runway_str, "#10b981"),
            ("Норма сбережений (Savings Rate):", f"{stats['savings_rate']:.0f}% от доходов", "#00d2ff"),
            ("Долговая нагрузка (DTI):", f"{dti_months} мес. чистого дохода", "#f43f5e"),
            ("Пассивный доход в день:", f"+{summary['daily_yield']:,.0f} сум/день".replace(",", " "), "#fbbf24"),
            ("Курс ЦБ Узбекистана:", f"1 USD = {usd_rate:,.0f} сум", "#94a3b8")
        ]
        for idx, (label, val, col) in enumerate(pulse_items):
            y = 0.72 - idx * 0.14
            ax_pulse.text(0.08, y + 0.04, label, transform=ax_pulse.transAxes,
                         color="#94a3b8", fontsize=7.5, zorder=2)
            ax_pulse.text(0.08, y - 0.03, val, transform=ax_pulse.transAxes,
                         color=col, fontsize=8.2, weight="bold", zorder=2)

        fig.suptitle(f"PERSONAL FINANCE DIRECTOR • EXECUTIVE DASHBOARD • {period_title.upper()}",
                     color="#f8fafc", fontsize=12.5, weight="bold", y=0.98)

        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close("all")
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_income_dashboard(stats: Dict[str, Any], summary: Dict[str, Any], period_title: str = "текущий месяц") -> io.BytesIO:
        """
        Generates a specialized Income Analytics Dashboard (Infographic).
        """
        fig = plt.figure(figsize=(15, 9.5), dpi=180, facecolor="#080b1d")
        gs = GridSpec(3, 3, figure=fig, height_ratios=[0.9, 2.5, 2.5], hspace=0.32, wspace=0.22)

        usd_rate = CurrencyService.get_usd_rate()
        usd_income = CurrencyService.to_usd_str(stats['full_income'])

        # ROW 0: KPI CARDS
        ax_kpi = fig.add_subplot(gs[0, :])
        ax_kpi.axis("off")

        daily_pace = stats['full_income'] / max(stats.get('period_days', 8), 1)
        kpis = [
            ("ОБЩИЙ ДОХОД ЗА ПЕРИОД", f"+{stats['full_income']:,.0f} сум".replace(",", " "), f"{usd_income} • Поступления", "#10b981"),
            ("АКТИВНЫЙ ДОХОД (ЗАРПЛАТА)", f"+{stats['total_income']:,.0f} сум".replace(",", " "), "100% от всех доходов", "#38bdf8"),
            ("ПАССИВНЫЙ ДОХОД (ВКЛАДЫ)", f"+{stats['total_passive']:,.0f} сум".replace(",", " "), f"+{summary['daily_yield']:,.0f} сум/день начислений".replace(",", " "), "#fbbf24"),
            ("СРЕДНИЙ ТЕМП ПОСТУПЛЕНИЙ", f"+{daily_pace:,.0f} сум/день".replace(",", " "), f"За {stats.get('period_days', 8)} дн. периода", "#a855f7")
        ]

        for i, (title, val, sub, col) in enumerate(kpis):
            x = 0.01 + i * 0.25
            ChartService._draw_card(ax_kpi, x, 0.05, 0.23, 0.9, bg="#121735", border="#232d5e")
            ax_kpi.text(x + 0.115, 0.72, title, transform=ax_kpi.transAxes,
                        color="#94a3b8", fontsize=8, weight="bold", ha="center", zorder=2)
            ax_kpi.text(x + 0.115, 0.42, val, transform=ax_kpi.transAxes,
                        color=col, fontsize=12, weight="bold", ha="center", zorder=2)
            ax_kpi.text(x + 0.115, 0.18, sub, transform=ax_kpi.transAxes,
                        color="#64748b", fontsize=7.2, ha="center", zorder=2)

        # ROW 1 COL 0-1: INCOME STRUCTURE & SOURCES
        ax_sources = fig.add_subplot(gs[1, :2], facecolor="#121735")
        ax_sources.axis("off")
        ChartService._draw_card(ax_sources, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_sources.text(0.04, 0.88, "ИСТОЧНИКИ ПОСТУПЛЕНИЙ И КАНАЛЫ ДОХОДА", transform=ax_sources.transAxes,
                        color="#f8fafc", fontsize=10.5, weight="bold", zorder=2)

        sources = [
            ("[КАРТА] Основная заработная плата (Humo / Uzcard)", stats['total_income'], "#10b981", 100.0),
            ("[ВКЛАД] Проценты по вкладам и депозитам", stats['total_passive'], "#fbbf24", 0.0),
            ("[БОНУС] Премии, фриланс и сторонний доход", 0.0, "#38bdf8", 0.0)
        ]
        for idx, (name, amount, color, pct) in enumerate(sources):
            y = 0.62 - idx * 0.24
            ax_sources.text(0.04, y + 0.09, name, transform=ax_sources.transAxes,
                            color="#f8fafc", fontsize=9, weight="bold", zorder=2)
            ax_sources.text(0.96, y + 0.09, f"+{amount:,.0f} сум ({pct:.0f}%)".replace(",", " "),
                            transform=ax_sources.transAxes, color=color, fontsize=9, weight="bold", ha="right", zorder=2)

            b_bg = FancyBboxPatch((0.04, y), 0.92, 0.055, boxstyle="round,pad=0.005,rounding_size=0.02",
                                  facecolor="#1e2548", edgecolor="none", transform=ax_sources.transAxes, zorder=2)
            ax_sources.add_patch(b_bg)

            if pct > 0:
                fill_w = max(0.92 * (pct / 100.0), 0.03)
                b_fill = FancyBboxPatch((0.04, y), fill_w, 0.055, boxstyle="round,pad=0.005,rounding_size=0.02",
                                        facecolor=color, edgecolor="none", transform=ax_sources.transAxes, zorder=3)
                ax_sources.add_patch(b_fill)

        # ROW 1 COL 2: VIRTUAL CARD RECEIVING ASSET
        ax_card = fig.add_subplot(gs[1, 2])
        ax_card.axis("off")
        ChartService._draw_card(ax_card, 0.02, 0.02, 0.96, 0.96, bg="#121735", border="#232d5e")

        c_bg = FancyBboxPatch((0.08, 0.12), 0.84, 0.76, boxstyle="round,pad=0.01,rounding_size=0.06",
                              facecolor="#064e3b", edgecolor="#059669", linewidth=1.5,
                              transform=ax_card.transAxes, clip_on=False, zorder=2)
        ax_card.add_patch(c_bg)

        chip = Rectangle((0.14, 0.58), 0.14, 0.14, facecolor="#eab308", edgecolor="#ca8a04",
                         transform=ax_card.transAxes, zorder=3)
        ax_card.add_patch(chip)

        ax_card.text(0.86, 0.72, "HUMO", transform=ax_card.transAxes, color="#f8fafc",
                     fontsize=10.5, weight="bold", ha="right", zorder=3)
        ax_card.text(0.14, 0.43, "•••• •••• •••• 4821", transform=ax_card.transAxes,
                     color="#cbd5e1", fontsize=9, fontfamily="monospace", zorder=3)
        ax_card.text(0.14, 0.28, f"+{stats['full_income']:,.0f} сум".replace(",", " "), transform=ax_card.transAxes,
                     color="#34d399", fontsize=11.5, weight="bold", zorder=3)
        ax_card.text(0.14, 0.18, "ЗАРПЛАТНЫЙ ДОХОД ЗАЧИСЛЕН", transform=ax_card.transAxes,
                     color="#a7f3d0", fontsize=6.5, weight="bold", zorder=3)
        ax_card.text(0.5, 0.94, "Основной счет зачисления", transform=ax_card.transAxes,
                     color="#f8fafc", fontsize=9.5, weight="bold", ha="center")

        # ROW 2 COL 0: SAVINGS CAPACITY GAUGE
        ax_cap = fig.add_subplot(gs[2, 0], facecolor="#121735")
        ax_cap.axis("off")
        ChartService._draw_card(ax_cap, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_cap.text(0.5, 0.88, "НОРМА СБЕРЕЖЕНИЙ", transform=ax_cap.transAxes,
                    color="#00d2ff", fontsize=10, weight="bold", ha="center", zorder=2)

        circle = Circle((0.5, 0.50), 0.28, facecolor="none", edgecolor="#10b981", linewidth=8, transform=ax_cap.transAxes)
        ax_cap.add_patch(circle)
        ax_cap.text(0.5, 0.53, f"{stats['savings_rate']:.0f}%", color="#10b981", fontsize=17, weight="bold", ha="center", va="center", transform=ax_cap.transAxes)
        ax_cap.text(0.5, 0.42, "СОХРАНЕНО", color="#94a3b8", fontsize=7.5, weight="bold", ha="center", va="center", transform=ax_cap.transAxes)
        ax_cap.text(0.5, 0.12, "Все доходы свободны от расходов\nОтличный потенциал инвестирования", color="#64748b", fontsize=7.2, ha="center", va="center", transform=ax_cap.transAxes)

        # ROW 2 COL 1: 12-MONTH WEALTH PROJECTION
        ax_proj = fig.add_subplot(gs[2, 1], facecolor="#121735")
        for spine in ax_proj.spines.values():
            spine.set_color("#232d5e")
        months_labels = ["3 мес", "6 мес", "9 мес", "12 мес"]
        base_m = stats['full_income']
        proj_vals = [base_m * 3, base_m * 6, base_m * 9, base_m * 12]
        bars = ax_proj.bar(months_labels, proj_vals, color="#38bdf8", width=0.45, zorder=3, edgecolor="#080b1d", linewidth=1.2)
        ax_proj.grid(axis="y", linestyle="--", alpha=0.15, color="#f8fafc", zorder=0)
        ax_proj.tick_params(colors="#94a3b8", labelsize=8)
        for bar in bars:
            h = bar.get_height()
            ax_proj.annotate(f"{int(h/1e6)} млн",
                             xy=(bar.get_x() + bar.get_width() / 2, h),
                             xytext=(0, 3), textcoords="offset points",
                             ha="center", va="bottom",
                             fontweight="bold", fontsize=7.5, color="#f8fafc")
        ax_proj.set_title("Прогноз накоплений (без учета %)", color="#f8fafc", fontsize=9.5, weight="bold", pad=10)

        # ROW 2 COL 2: FINANCIAL DIRECTOR ADVICE
        ax_adv = fig.add_subplot(gs[2, 2], facecolor="#121735")
        ax_adv.axis("off")
        ChartService._draw_card(ax_adv, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_adv.text(0.08, 0.88, "СОВЕТ ФИНАНСИСТА", transform=ax_adv.transAxes,
                    color="#fbbf24", fontsize=10, weight="bold", zorder=2)

        tips = [
            "1. Создание пассивного дохода:",
            "   Открыв вклад на 20% зарплаты",
            "   под 22% годовых в банках РУз,",
            "   вы получите +528 000 сум/год",
            "2. Ускорение выплат по долгам:",
            "   Направив часть зарплаты на авто,",
            "   вы быстрее закроете 120.2 млн сум."
        ]
        for idx, tip in enumerate(tips):
            col = "#f8fafc" if tip.startswith(("1.", "2.")) else "#94a3b8"
            weight = "bold" if tip.startswith(("1.", "2.")) else "normal"
            ax_adv.text(0.08, 0.72 - idx * 0.085, tip, transform=ax_adv.transAxes,
                        color=col, fontsize=7.5, weight=weight, zorder=2)

        fig.suptitle(f"PERSONAL FINANCE DIRECTOR • АНАЛИТИКА ДОХОДОВ • {period_title.upper()}",
                     color="#f8fafc", fontsize=12.5, weight="bold", y=0.98)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close("all")
        buf.seek(0)
        return buf

    @staticmethod
    def generate_expense_dashboard(stats: Dict[str, Any], summary: Dict[str, Any], period_title: str = "текущий месяц") -> io.BytesIO:
        """
        Generates a specialized Expense & Categories Analytics Dashboard (Infographic).
        """
        fig = plt.figure(figsize=(15, 9.5), dpi=180, facecolor="#080b1d")
        gs = GridSpec(3, 3, figure=fig, height_ratios=[0.9, 2.5, 2.5], hspace=0.32, wspace=0.22)

        usd_rate = CurrencyService.get_usd_rate()
        usd_exp = CurrencyService.to_usd_str(stats['total_expense'])

        # ROW 0: KPI CARDS
        ax_kpi = fig.add_subplot(gs[0, :])
        ax_kpi.axis("off")

        categories = stats.get("categories", [])
        cat_count_str = f"{len(categories)} категорий трат" if categories else "Расходов нет (0)"

        kpis = [
            ("ОБЩИЕ РАСХОДЫ ЗА ПЕРИОД", f"-{stats['total_expense']:,.0f} сум".replace(",", " "), f"{usd_exp} • Списания", "#f43f5e" if stats['total_expense'] > 0 else "#94a3b8"),
            ("СРЕДНИЙ РАСХОД В ДЕНЬ", f"{stats['daily_avg_expense']:,.0f} сум/день".replace(",", " "), f"За {stats.get('period_days', 8)} дн.", "#38bdf8"),
            ("СТРУКТУРА ТРАТ", cat_count_str, "Детализация ниже", "#a855f7"),
            ("НОРМА СБЕРЕЖЕНИЙ", f"{stats['savings_rate']:.0f}%", "Доля сохраненного дохода", "#10b981")
        ]

        for i, (title, val, sub, col) in enumerate(kpis):
            x = 0.01 + i * 0.25
            ChartService._draw_card(ax_kpi, x, 0.05, 0.23, 0.9, bg="#121735", border="#232d5e")
            ax_kpi.text(x + 0.115, 0.72, title, transform=ax_kpi.transAxes,
                        color="#94a3b8", fontsize=8, weight="bold", ha="center", zorder=2)
            ax_kpi.text(x + 0.115, 0.42, val, transform=ax_kpi.transAxes,
                        color=col, fontsize=12, weight="bold", ha="center", zorder=2)
            ax_kpi.text(x + 0.115, 0.18, sub, transform=ax_kpi.transAxes,
                        color="#64748b", fontsize=7.2, ha="center", zorder=2)

        # ROW 1 COL 0-1: CATEGORIES VISUALIZATION
        ax_cats = fig.add_subplot(gs[1, :2], facecolor="#121735")
        ChartService._draw_card(ax_cats, 0, 0, 1, 1, bg="#121735", border="#232d5e")

        if categories:
            for spine in ax_cats.spines.values():
                spine.set_color("#232d5e")
            c_names = [c['name'] for c in categories[:6]]
            c_amounts = [c['amount'] for c in categories[:6]]
            c_colors = ["#f43f5e", "#fbbf24", "#38bdf8", "#10b981", "#a855f7", "#ec4899"][:len(c_names)]
            bars = ax_cats.barh(c_names, c_amounts, color=c_colors, height=0.5, zorder=3)
            ax_cats.grid(axis="x", linestyle="--", alpha=0.15, color="#f8fafc", zorder=0)
            ax_cats.tick_params(colors="#94a3b8", labelsize=8.5)
            for bar in bars:
                w = bar.get_width()
                ax_cats.annotate(f"{int(w):,} сум".replace(",", " "),
                                 xy=(w, bar.get_y() + bar.get_height() / 2),
                                 xytext=(6, 0), textcoords="offset points",
                                 ha="left", va="center",
                                 fontweight="bold", fontsize=7.8, color="#f8fafc")
            ax_cats.set_title("Рейтинг категорий по сумме расходов", color="#f8fafc", fontsize=9.5, weight="bold", pad=10)
        else:
            ax_cats.axis("off")
            circle_c = Circle((0.5, 0.52), 0.30, facecolor="none", edgecolor="#10b981", linewidth=7, transform=ax_cats.transAxes)
            ax_cats.add_patch(circle_c)
            ax_cats.text(0.5, 0.55, "0 РАСХОДОВ", color="#10b981", fontsize=15, weight="bold", ha="center", va="center", transform=ax_cats.transAxes)
            ax_cats.text(0.5, 0.43, "БЮДЖЕТ ЦЕЛ", color="#94a3b8", fontsize=8, weight="bold", ha="center", va="center", transform=ax_cats.transAxes)
            ax_cats.text(0.5, 0.15, "За текущий месяц не зафиксировано ни одного расхода!\nВсе доходы остаются в капитале.", color="#64748b", fontsize=7.5, ha="center", va="center", transform=ax_cats.transAxes)
            ax_cats.text(0.5, 0.88, "СТАТУС ИСПОЛНЕНИЯ БЮДЖЕТА", color="#f8fafc", fontsize=10, weight="bold", ha="center", transform=ax_cats.transAxes)

        # ROW 1 COL 2: BUDGET SAFETY RATIO
        ax_ratio = fig.add_subplot(gs[1, 2], facecolor="#121735")
        ax_ratio.axis("off")
        ChartService._draw_card(ax_ratio, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_ratio.text(0.5, 0.88, "ЗАЩИТА БЮДЖЕТА (50/30/20)", transform=ax_ratio.transAxes,
                      color="#00d2ff", fontsize=9.5, weight="bold", ha="center", zorder=2)

        items_50 = [
            ("Базовые нужды (до 50%):", "0 сум (0%)", "#10b981"),
            ("Личные желания (до 30%):", "0 сум (0%)", "#38bdf8"),
            ("Сбережения и долги (от 20%):", f"{stats['savings']:,.0f} сум (100%)".replace(",", " "), "#fbbf24")
        ]
        for idx, (label, val, col) in enumerate(items_50):
            y = 0.68 - idx * 0.22
            ax_ratio.text(0.08, y + 0.06, label, transform=ax_ratio.transAxes,
                          color="#94a3b8", fontsize=7.5, zorder=2)
            ax_ratio.text(0.08, y - 0.02, val, transform=ax_ratio.transAxes,
                          color=col, fontsize=8.5, weight="bold", zorder=2)

        # ROW 2 COL 0-1: EXPENSE SPEED & BURN RATE
        ax_burn = fig.add_subplot(gs[2, :2], facecolor="#121735")
        ax_burn.axis("off")
        ChartService._draw_card(ax_burn, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_burn.text(0.04, 0.88, "АНАЛИЗ ТЕМПА ТРАТ И СБЕРЕЖЕНИЙ", transform=ax_burn.transAxes,
                     color="#f8fafc", fontsize=10, weight="bold", zorder=2)

        burn_lines = [
            "• Дневной лимит расходов: для сохранения 50% нормы сбережений рекомендуемый расход — до 200 000 сум/день.",
            "• Текущая скорость трат (Burn Rate): 0 сум/день. Подушка безопасности не расходуется.",
            "• Рекомендация: при совершении покупок фиксируйте их текстом или чеком — бот моментально учтет категорию."
        ]
        for idx, line in enumerate(burn_lines):
            ax_burn.text(0.04, 0.66 - idx * 0.22, line, transform=ax_burn.transAxes,
                         color="#cbd5e1", fontsize=7.8, zorder=2)

        # ROW 2 COL 2: RUNWAY
        ax_runway = fig.add_subplot(gs[2, 2], facecolor="#121735")
        ax_runway.axis("off")
        ChartService._draw_card(ax_runway, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_runway.text(0.5, 0.88, "ЗАПАС ПРОЧНОСТИ (RUNWAY)", transform=ax_runway.transAxes,
                       color="#10b981", fontsize=9.5, weight="bold", ha="center", zorder=2)

        circle_r = Circle((0.5, 0.50), 0.28, facecolor="none", edgecolor="#10b981", linewidth=8, transform=ax_runway.transAxes)
        ax_runway.add_patch(circle_r)
        ax_runway.text(0.5, 0.53, "MAX", color="#10b981", fontsize=17, weight="bold", ha="center", va="center", transform=ax_runway.transAxes)
        ax_runway.text(0.5, 0.40, "БЕССРОЧНО", color="#94a3b8", fontsize=7.5, weight="bold", ha="center", va="center", transform=ax_runway.transAxes)
        ax_runway.text(0.5, 0.12, "При текущих расходах 0 сум\nактивы остаются нетронутыми", color="#64748b", fontsize=7.2, ha="center", va="center", transform=ax_runway.transAxes)

        fig.suptitle(f"PERSONAL FINANCE DIRECTOR • АНАЛИТИКА РАСХОДОВ • {period_title.upper()}",
                     color="#f8fafc", fontsize=12.5, weight="bold", y=0.98)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close("all")
        buf.seek(0)
        return buf

    @staticmethod
    def generate_debts_dashboard(stats: Dict[str, Any], summary: Dict[str, Any], period_title: str = "текущий месяц") -> io.BytesIO:
        """
        Generates a specialized Debts & Installments Analytics Dashboard (Infographic).
        """
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
            ("ОБЩИЙ ОСТАТОК ОБЯЗАТЕЛЬСТВ", f"-{summary['total_debt']:,.0f} сум".replace(",", " "), f"{usd_debt} • {len(credit_cards)} обязательства", "#fb7185"),
            ("ВЫПЛАЧЕНО ПО РАССРОЧКАМ", f"{total_paid:,.0f} сум".replace(",", " "), f"{pct_total_paid}% от общего объема", "#10b981"),
            ("РЕЗЕРВНЫЙ КРЕДИТНЫЙ ЛИМИТ", f"{avail_credit:,.0f} сум".replace(",", " "), "Доступно на карте TEZ", "#38bdf8"),
            ("ДОЛГОВАЯ НАГРУЗКА (DTI)", f"{dti_months} мес.", "Месяцев чистого дохода", "#f43f5e")
        ]

        for i, (title, val, sub, col) in enumerate(kpis):
            x = 0.01 + i * 0.25
            ChartService._draw_card(ax_kpi, x, 0.05, 0.23, 0.9, bg="#121735", border="#232d5e")
            ax_kpi.text(x + 0.115, 0.72, title, transform=ax_kpi.transAxes,
                        color="#94a3b8", fontsize=8, weight="bold", ha="center", zorder=2)
            ax_kpi.text(x + 0.115, 0.42, val, transform=ax_kpi.transAxes,
                        color=col, fontsize=12, weight="bold", ha="center", zorder=2)
            ax_kpi.text(x + 0.115, 0.18, sub, transform=ax_kpi.transAxes,
                        color="#64748b", fontsize=7.2, ha="center", zorder=2)

        # ROW 1 COLS 0-1: DETAILED GRANULAR DEBTS
        ax_debts = fig.add_subplot(gs[1, :2], facecolor="#121735")
        ax_debts.axis("off")
        ChartService._draw_card(ax_debts, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_debts.text(0.04, 0.90, "ДЕТАЛИЗИРОВАННЫЙ РЕЕСТР ДОЛГОВ И РАССРОЧЕК", transform=ax_debts.transAxes,
                     color="#f8fafc", fontsize=10.5, weight="bold", zorder=2)

        for idx, c in enumerate(credit_cards[:3]):
            y = 0.65 - idx * 0.27
            acc = c["account"]
            debt = c["debt"]
            limit = c["limit"]
            paid = max(limit - debt, 0.0) if limit > 0 else 0.0
            pct = round(paid / limit * 100, 1) if limit > 0 else 0.0

            clean_name = acc.name
            if len(clean_name) > 36:
                clean_name = clean_name[:34] + "…"

            nl = clean_name.lower()
            tag = "[АВТО]" if "авто" in nl else ("[КУРС]" if "курс" in nl or "skillbox" in nl else "[КАРТА]")

            ax_debts.text(0.04, y + 0.11, f"{tag} {clean_name}", transform=ax_debts.transAxes,
                         color="#f8fafc", fontsize=9, weight="bold", zorder=2)
            ax_debts.text(0.96, y + 0.11, f"Долг: {debt:,.0f} сум".replace(",", " "),
                         transform=ax_debts.transAxes, color="#f43f5e", fontsize=9, weight="bold", ha="right", zorder=2)

            bar_bg = FancyBboxPatch((0.04, y), 0.92, 0.07, boxstyle="round,pad=0.005,rounding_size=0.03",
                                    facecolor="#1e2548", edgecolor="none", transform=ax_debts.transAxes, zorder=2)
            ax_debts.add_patch(bar_bg)

            if limit > 0 and paid > 0:
                p_w = min(max(0.92 * (paid / limit), 0.02), 0.92)
                bar_p = FancyBboxPatch((0.04, y), p_w, 0.07, boxstyle="round,pad=0.005,rounding_size=0.03",
                                       facecolor="#10b981", edgecolor="none", transform=ax_debts.transAxes, zorder=3)
                ax_debts.add_patch(bar_p)

            if "карт" in nl and "рассрочк" not in nl:
                avail = max(limit - debt, 0.0)
                grace_str = f", льготный: {acc.grace_period_days} дн." if getattr(acc, "grace_period_days", 0) > 0 else ""
                ax_debts.text(0.04, y - 0.07, f"Доступно для покупок: {avail:,.0f} сум (лимит: {limit:,.0f} сум{grace_str})".replace(",", " "),
                             transform=ax_debts.transAxes, color="#94a3b8", fontsize=7.5, zorder=2)
            else:
                ax_debts.text(0.04, y - 0.07, f"Выплачено: {paid:,.0f} сум ({pct}%) из {limit:,.0f} сум".replace(",", " "),
                             transform=ax_debts.transAxes, color="#94a3b8", fontsize=7.5, zorder=2)

        # ROW 1 COL 2: DEBT RATIO DONUT
        ax_donut = fig.add_subplot(gs[1, 2], facecolor="#121735")
        ChartService._draw_card(ax_donut, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        if credit_cards:
            d_sizes = [c['debt'] for c in credit_cards[:3]]
            d_labels = [f"{c['account'].name[:12]} ({round(c['debt']/max(summary['total_debt'],1.0)*100):.0f}%)" for c in credit_cards[:3]]
            d_cols = ["#f43f5e", "#fb923c", "#a855f7"][:len(d_sizes)]
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

        # ROW 2 COL 0-1: PAYOFF STRATEGY
        ax_strat = fig.add_subplot(gs[2, :2], facecolor="#121735")
        ax_strat.axis("off")
        ChartService._draw_card(ax_strat, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_strat.text(0.04, 0.88, "СТРАТЕГИЯ ДОСРОЧНОГО ЗАКРЫТИЯ ДОЛГОВ (МЕТОД СНЕЖНОГО КОМА)",
                      transform=ax_strat.transAxes, color="#00d2ff", fontsize=10, weight="bold", zorder=2)

        steps = [
            "1. ШАГ 1: Закрыть долг по курсу Skillbox (остаток 5 000 000 сум) за 1 платеж.",
            "   Это сразу высвободит психологический ресурс и уменьшит число кредиторов.",
            "2. ШАГ 2: Погасить кредитку TEZ (11 054 217 сум) в пределах 62 дней льготного периода.",
            "   Это позволит избежать начисления высоких банковских процентов.",
            "3. ШАГ 3: Направить весь высвободившийся ресурс на авто (120.2 млн сум) и закрыть за 18-24 мес."
        ]
        for idx, s in enumerate(steps):
            col = "#f8fafc" if s.startswith(("1.", "2.", "3.")) else "#94a3b8"
            weight = "bold" if s.startswith(("1.", "2.", "3.")) else "normal"
            ax_strat.text(0.04, 0.70 - idx * 0.11, s, transform=ax_strat.transAxes,
                          color=col, fontsize=7.8, weight=weight, zorder=2)

        # ROW 2 COL 2: DEBT FREE HORIZON
        ax_horiz = fig.add_subplot(gs[2, 2], facecolor="#121735")
        ax_horiz.axis("off")
        ChartService._draw_card(ax_horiz, 0, 0, 1, 1, bg="#121735", border="#232d5e")
        ax_horiz.text(0.5, 0.88, "ГОРИЗОНТ СВОБОДЫ", transform=ax_horiz.transAxes,
                      color="#10b981", fontsize=10, weight="bold", ha="center", zorder=2)

        circle_h = Circle((0.5, 0.50), 0.28, facecolor="none", edgecolor="#38bdf8", linewidth=8, transform=ax_horiz.transAxes)
        ax_horiz.add_patch(circle_h)
        ax_horiz.text(0.5, 0.53, "~24-36", color="#38bdf8", fontsize=16, weight="bold", ha="center", va="center", transform=ax_horiz.transAxes)
        ax_horiz.text(0.5, 0.40, "МЕСЯЦЕВ", color="#94a3b8", fontsize=7.5, weight="bold", ha="center", va="center", transform=ax_horiz.transAxes)
        ax_horiz.text(0.5, 0.12, "До полного избавления от долгов\nпри плановом графике выплат", color="#64748b", fontsize=7.2, ha="center", va="center", transform=ax_horiz.transAxes)

        fig.suptitle(f"PERSONAL FINANCE DIRECTOR • ОБЯЗАТЕЛЬСТВА И РАССРОЧКИ • {period_title.upper()}",
                     color="#f8fafc", fontsize=12.5, weight="bold", y=0.98)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close("all")
        buf.seek(0)
        return buf

    @staticmethod
    def generate_specialized_dashboard(dashboard_type: str, stats: Dict[str, Any], summary: Dict[str, Any], period_title: str = "текущий месяц") -> Tuple[io.BytesIO, str]:
        """
        Dispatches to the requested dashboard generator and returns (buffer, title).
        """
        t = dashboard_type.upper()
        if t == "INCOME":
            return ChartService.generate_income_dashboard(stats, summary, period_title), "🟢 ДАШБОРД ДОХОДОВ"
        elif t == "EXPENSE":
            return ChartService.generate_expense_dashboard(stats, summary, period_title), "🔴 ДАШБОРД РАСХОДОВ ПО КАТЕГОРИЯМ"
        elif t == "DEBTS":
            return ChartService.generate_debts_dashboard(stats, summary, period_title), "🚗 ДАШБОРД ОБЯЗАТЕЛЬСТВ И РАССРОЧЕК"
        else:
            return ChartService.generate_full_dashboard(stats, summary, period_title), "📊 ЕДИНЫЙ ФИНАНСОВЫЙ ДАШБОРД"

    @staticmethod
    def generate_interactive_html(stats: Dict[str, Any], summary: Dict[str, Any], period_title: str) -> str:
        """
        Generates a standalone, fully interactive HTML5 Web Dashboard with:
        - Clickable sidebar tabs (Dashboard, Income, Expenses, Debts, Budgeting, Goals, Investments)
        - Dynamic month filter selector
        - Live currency toggle between UZS and USD via CBU rate
        - Interactive Chart.js charts with tooltips and animations
        - Sleek Dark Luxury Fintech UI/UX
        """
        usd_rate = CurrencyService.get_usd_rate()
        usd_net_worth = CurrencyService.to_usd_str(summary['total_balance'])

        credit_cards = summary.get("credit_cards", [])
        debts_cards_html = ""
        total_paid_debts = 0.0
        total_limits_debts = 0.0

        if credit_cards:
            for c in credit_cards:
                acc = c["account"]
                debt = c["debt"]
                limit = c["limit"]
                paid = max(limit - debt, 0.0) if limit > 0 else 0.0
                pct = round((paid / limit) * 100, 1) if limit > 0 else 0.0
                total_paid_debts += paid
                total_limits_debts += limit

                nl = acc.name.lower()
                icon = "🚗" if "авто" in nl else ("🎓" if ("курс" in nl or "skillbox" in nl) else "💳")

                debts_cards_html += f"""
                <div class="debt-item">
                    <div class="debt-header">
                        <span class="debt-name">{icon} {acc.name}</span>
                        <span class="debt-val" data-uzs="{debt}">Остаток: {debt:,.0f} сум</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: {pct}%;"></div>
                    </div>
                    <div class="debt-sub">
                        <span>Выплачено: <strong data-uzs="{paid}">{paid:,.0f} сум</strong> ({pct}%)</span>
                        <span>Всего: <strong data-uzs="{limit}">{limit:,.0f} сум</strong></span>
                    </div>
                </div>
                """
        else:
            debts_cards_html = "<p style='color: var(--green); text-align: center; padding: 20px;'>🎉 У вас нет активных задолженностей или рассрочек!</p>"

        # Find primary debit card
        primary_card_name = "HUMO / UZCARD"
        primary_balance = summary['liquid_balance']
        for a in summary.get("accounts", []):
            if a.account_type.value in ("CARD", "CASH") and a.balance > 0:
                primary_card_name = a.name
                primary_balance = a.balance
                break

        # Category lists
        cats = stats.get("categories", [])
        cat_rows_html = ""
        if cats:
            for cat in cats:
                cat_rows_html += f"""
                <div class="category-row">
                    <div class="cat-info">
                        <span class="cat-icon">{cat.get('icon', '📦')}</span>
                        <span class="cat-name">{cat['name']}</span>
                    </div>
                    <div class="cat-amount">
                        <strong data-uzs="{cat['amount']}">{cat['amount']:,.0f} сум</strong>
                        <span class="cat-pct">{cat['percent']}%</span>
                    </div>
                </div>
                """
        else:
            cat_rows_html = "<p style='color: var(--text-muted); text-align: center; padding: 20px;'>За выбранный период расходов пока нет.</p>"

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal Finance Director — Uzbekistan</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-main: #080b1d;
            --bg-card: #121735;
            --bg-card-hover: #171e44;
            --border: #232d5e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-cyan: #00d2ff;
            --accent-blue: #38bdf8;
            --green: #10b981;
            --red: #f43f5e;
            --purple: #8b5cf6;
            --amber: #fbbf24;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif; }}
        body {{ background-color: var(--bg-main); color: var(--text-main); min-height: 100vh; display: flex; }}
        
        /* SIDEBAR */
        .sidebar {{ width: 230px; background: #0c102a; border-right: 1px solid var(--border); padding: 24px 16px; display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }}
        .brand {{ font-size: 15px; font-weight: bold; color: var(--accent-cyan); display: flex; align-items: center; gap: 8px; margin-bottom: 24px; padding-left: 8px; letter-spacing: 0.5px; }}
        .nav-item {{ display: flex; align-items: center; gap: 12px; padding: 11px 14px; border-radius: 12px; color: var(--text-muted); font-size: 13px; font-weight: 600; transition: all 0.2s; cursor: pointer; user-select: none; }}
        .nav-item:hover {{ background: rgba(255,255,255,0.05); color: var(--text-main); }}
        .nav-item.active {{ background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); color: var(--accent-cyan); border: 1px solid #4338ca; box-shadow: 0 4px 14px rgba(67, 56, 202, 0.3); }}
        
        /* MAIN CONTENT */
        .main-wrapper {{ flex: 1; padding: 24px 30px; overflow-y: auto; }}
        
        /* TOP BAR */
        .top-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 16px; }}
        .months-bar {{ display: flex; gap: 6px; background: var(--bg-card); padding: 5px; border-radius: 30px; border: 1px solid var(--border); overflow-x: auto; }}
        .month-pill {{ padding: 6px 14px; border-radius: 20px; font-size: 11px; font-weight: 600; color: var(--text-muted); cursor: pointer; transition: all 0.2s; user-select: none; }}
        .month-pill:hover {{ color: var(--text-main); }}
        .month-pill.active {{ background: linear-gradient(90deg, #6366f1, #a855f7); color: #fff; box-shadow: 0 0 12px rgba(168, 85, 247, 0.4); }}
        
        .top-actions {{ display: flex; gap: 10px; align-items: center; }}
        .currency-btn {{ background: linear-gradient(135deg, #1e1b4b 0%, #2e1065 100%); border: 1px solid #6366f1; color: var(--accent-cyan); padding: 7px 16px; border-radius: 20px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s; }}
        .currency-btn:hover {{ filter: brightness(1.2); box-shadow: 0 0 10px rgba(99, 102, 241, 0.4); }}
        .cbu-badge {{ background: var(--bg-card); border: 1px solid var(--border); padding: 7px 16px; border-radius: 20px; font-size: 12px; font-weight: bold; color: var(--accent-cyan); }}
        
        /* KPI GRID */
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .kpi-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 20px; position: relative; overflow: hidden; }}
        .kpi-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: transparent; }}
        .kpi-card.nw::before {{ background: var(--accent-cyan); }}
        .kpi-card.inc::before {{ background: var(--green); }}
        .kpi-card.exp::before {{ background: var(--red); }}
        .kpi-card.debt::before {{ background: #fb7185; }}
        .kpi-title {{ font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px; }}
        .kpi-val {{ font-size: 22px; font-weight: 800; margin-bottom: 4px; }}
        .kpi-sub {{ font-size: 11px; color: var(--text-muted); }}

        /* MAIN WIDGETS GRID */
        .dashboard-grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 24px; }}
        .dashboard-grid-equal {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
        .widget-box {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 22px; }}
        .widget-title {{ font-size: 14px; font-weight: 700; margin-bottom: 18px; color: var(--text-main); display: flex; justify-content: space-between; align-items: center; }}
        
        /* VIRTUAL CARD WIDGET */
        .virtual-card {{ background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%); border: 1px solid #4c1d95; border-radius: 16px; padding: 22px; box-shadow: 0 8px 24px rgba(76, 29, 149, 0.25); position: relative; }}
        .chip {{ width: 38px; height: 28px; background: #eab308; border-radius: 5px; margin-bottom: 18px; position: relative; border: 1px solid #ca8a04; }}
        .chip::after {{ content: ''; position: absolute; inset: 4px; border: 1px dashed rgba(0,0,0,0.3); border-radius: 2px; }}
        .card-number {{ font-family: monospace; font-size: 14px; letter-spacing: 2px; color: #cbd5e1; margin-bottom: 12px; }}
        .card-bal {{ font-size: 20px; font-weight: 800; color: #34d399; margin-bottom: 4px; }}
        .card-holder {{ font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; }}
        .card-logo {{ position: absolute; top: 22px; right: 22px; font-size: 16px; font-weight: 900; color: #fff; }}

        /* DEBTS LIST */
        .debt-item {{ background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 14px; margin-bottom: 12px; }}
        .debt-header {{ display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; margin-bottom: 8px; }}
        .debt-val {{ color: var(--red); font-weight: 800; }}
        .progress-bar-bg {{ width: 100%; height: 8px; background: #1e2548; border-radius: 4px; overflow: hidden; margin-bottom: 6px; }}
        .progress-bar-fill {{ height: 100%; background: linear-gradient(90deg, #10b981, #00d2ff); border-radius: 4px; }}
        .debt-sub {{ display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); }}

        /* CATEGORIES LIST */
        .category-row {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }}
        .cat-info {{ display: flex; align-items: center; gap: 10px; font-size: 13px; font-weight: 600; }}
        .cat-amount {{ display: flex; align-items: center; gap: 10px; font-size: 13px; }}
        .cat-pct {{ color: var(--accent-cyan); font-weight: 700; font-size: 11px; background: rgba(0, 210, 255, 0.1); padding: 2px 8px; border-radius: 10px; }}

        /* PULSE LIST */
        .pulse-list {{ list-style: none; display: flex; flex-direction: column; gap: 12px; }}
        .pulse-item {{ display: flex; justify-content: space-between; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 13px; }}

        /* TAB VIEWS */
        .tab-view {{ display: none; animation: fadeIn 0.25s ease-in-out; }}
        .tab-view.active {{ display: block; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        @media (max-width: 900px) {{
            body {{ flex-direction: column; }}
            .sidebar {{ width: 100%; border-right: none; border-bottom: 1px solid var(--border); }}
            .dashboard-grid, .dashboard-grid-equal {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <!-- LEFT SIDEBAR -->
    <div class="sidebar">
        <div class="brand">💎 FINANCE AI</div>
        <div class="nav-item active" id="nav-dashboard" onclick="switchTab('dashboard')">📊 Dashboard</div>
        <div class="nav-item" id="nav-income" onclick="switchTab('income')">🟢 Доходы</div>
        <div class="nav-item" id="nav-expenses" onclick="switchTab('expenses')">🔴 Расходы</div>
        <div class="nav-item" id="nav-debts" onclick="switchTab('debts')">🚗 Обязательства</div>
        <div class="nav-item" id="nav-budget" onclick="switchTab('budget')">💰 Бюджетирование</div>
        <div class="nav-item" id="nav-goals" onclick="switchTab('goals')">🎯 Финансовые цели</div>
        <div class="nav-item" id="nav-invest" onclick="switchTab('invest')">📈 Инвестиции</div>
    </div>

    <!-- MAIN CONTENT -->
    <div class="main-wrapper">
        <!-- TOP FILTER BAR -->
        <div class="top-bar">
            <div class="months-bar">
                <span class="month-pill" onclick="switchMonth(this, 'Январь 2026')">Янв</span>
                <span class="month-pill" onclick="switchMonth(this, 'Февраль 2026')">Фев</span>
                <span class="month-pill" onclick="switchMonth(this, 'Март 2026')">Мар</span>
                <span class="month-pill" onclick="switchMonth(this, 'Апрель 2026')">Апр</span>
                <span class="month-pill" onclick="switchMonth(this, 'Май 2026')">Май</span>
                <span class="month-pill" onclick="switchMonth(this, 'Июнь 2026')">Июн</span>
                <span class="month-pill" onclick="switchMonth(this, 'Июль 2026')">Июл</span>
                <span class="month-pill" onclick="switchMonth(this, 'Август 2026')">Авг</span>
                <span class="month-pill" onclick="switchMonth(this, 'Сентябрь 2026')">Сен</span>
                <span class="month-pill" onclick="switchMonth(this, 'Октябрь 2026')">Окт</span>
                <span class="month-pill active" onclick="switchMonth(this, 'Ноябрь 2026')">Ноябрь 2026</span>
                <span class="month-pill" onclick="switchMonth(this, 'Декабрь 2026')">Дек</span>
            </div>
            <div class="top-actions">
                <button id="cur-toggle-btn" class="currency-btn" onclick="toggleCurrency()">🇺🇿 UZS (Сум)</button>
                <div class="cbu-badge">🇺🇿 ЦБ РУз: 1$ = {usd_rate:,.0f} сум</div>
            </div>
        </div>

        <!-- ================= TAB 1: DASHBOARD (OVERVIEW) ================= -->
        <div id="tab-dashboard" class="tab-view active">
            <!-- 4 TOP KPI CARDS -->
            <div class="kpi-grid">
                <div class="kpi-card nw">
                    <div class="kpi-title">💎 Чистый капитал</div>
                    <div class="kpi-val" style="color: {'#38bdf8' if summary['total_balance'] >= 0 else '#f43f5e'};" data-uzs="{summary['total_balance']}">{summary['total_balance']:,.0f} сум</div>
                    <div class="kpi-sub">{usd_net_worth} • Активы минус долги</div>
                </div>
                <div class="kpi-card inc">
                    <div class="kpi-title">🟢 Доходы за месяц</div>
                    <div class="kpi-val" style="color: var(--green);" data-uzs="{stats['full_income']}">+{stats['full_income']:,.0f} сум</div>
                    <div class="kpi-sub">Зарплата • Пассивный: +{stats['total_passive']:,.0f} сум</div>
                </div>
                <div class="kpi-card exp">
                    <div class="kpi-title">🔴 Расходы за месяц</div>
                    <div class="kpi-val" style="color: {'var(--text-muted)' if stats['total_expense'] == 0 else 'var(--red)'};" data-uzs="{stats['total_expense']}">-{stats['total_expense']:,.0f} сум</div>
                    <div class="kpi-sub">В день: {stats['daily_avg_expense']:,.0f} сум</div>
                </div>
                <div class="kpi-card debt">
                    <div class="kpi-title">⚖️ Общие обязательства</div>
                    <div class="kpi-val" style="color: #fb7185;" data-uzs="{summary['total_debt']}">-{summary['total_debt']:,.0f} сум</div>
                    <div class="kpi-sub">{len(credit_cards)} активных рассрочки/долга</div>
                </div>
            </div>

            <!-- MAIN ROW: COMBO CHART & VIRTUAL CARD -->
            <div class="dashboard-grid">
                <div class="widget-box">
                    <div class="widget-title">
                        <span>📊 Денежный поток (Cashflow)</span>
                        <span style="font-size: 11px; color: var(--accent-cyan);">Норма сбережений: {stats['savings_rate']:.0f}%</span>
                    </div>
                    <canvas id="cfComboChart" height="130"></canvas>
                </div>

                <div class="widget-box" style="display: flex; flex-direction: column; justify-content: center;">
                    <div class="virtual-card">
                        <div class="card-logo">HUMO</div>
                        <div class="chip"></div>
                        <div class="card-number">•••• •••• •••• 4821</div>
                        <div class="card-bal" data-uzs="{primary_balance}">{primary_balance:,.0f} сум</div>
                        <div class="card-holder">{primary_card_name} • ЗАРПЛАТНЫЙ АКТИВ</div>
                    </div>
                </div>
            </div>

            <!-- BOTTOM ROW: DEBTS BREAKDOWN & WEALTH HEALTH -->
            <div class="dashboard-grid">
                <div class="widget-box">
                    <div class="widget-title">
                        <span>🚗 Детализация обязательств и рассрочек</span>
                        <span style="font-size: 11px; color: var(--red);" data-uzs="{summary['total_debt']}">Всего: -{summary['total_debt']:,.0f} сум</span>
                    </div>
                    {debts_cards_html}
                </div>

                <div class="widget-box">
                    <div class="widget-title">
                        <span>⚡️ Финансовый пульс и индикаторы</span>
                    </div>
                    <ul class="pulse-list">
                        <li class="pulse-item">
                            <span style="color: var(--text-muted);">Подушка безопасности (Runway):</span>
                            <strong style="color: var(--green);">{stats['runway_months']} мес. (Бессрочно)</strong>
                        </li>
                        <li class="pulse-item">
                            <span style="color: var(--text-muted);">Норма сбережений:</span>
                            <strong style="color: var(--accent-cyan);">{stats['savings_rate']:.0f}% дохода</strong>
                        </li>
                        <li class="pulse-item">
                            <span style="color: var(--text-muted);">Долговая нагрузка (DTI):</span>
                            <strong style="color: var(--red);">{round(summary['total_debt'] / max(stats['full_income'], 1.0), 1)} мес. дохода</strong>
                        </li>
                        <li class="pulse-item">
                            <span style="color: var(--text-muted);">Пассивный доход:</span>
                            <strong style="color: var(--amber);">+{summary['daily_yield']:,.0f} сум/день</strong>
                        </li>
                        <li class="pulse-item">
                            <span style="color: var(--text-muted);">Официальный курс ЦБ РУз:</span>
                            <strong style="color: var(--text-main);">1$ = {usd_rate:,.0f} сум</strong>
                        </li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- ================= TAB 2: INCOME ================= -->
        <div id="tab-income" class="tab-view">
            <div class="kpi-grid">
                <div class="kpi-card inc">
                    <div class="kpi-title">Всего доходов</div>
                    <div class="kpi-val" style="color: var(--green);" data-uzs="{stats['full_income']}">+{stats['full_income']:,.0f} сум</div>
                    <div class="kpi-sub">За период {period_title}</div>
                </div>
                <div class="kpi-card nw">
                    <div class="kpi-title">Заработная плата</div>
                    <div class="kpi-val" style="color: var(--accent-cyan);" data-uzs="{stats['total_income']}">+{stats['total_income']:,.0f} сум</div>
                    <div class="kpi-sub">100% от общего объема</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Пассивный доход</div>
                    <div class="kpi-val" style="color: var(--amber);" data-uzs="{stats['total_passive']}">+{stats['total_passive']:,.0f} сум</div>
                    <div class="kpi-sub">Проценты по депозитам</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Средний темп</div>
                    <div class="kpi-val" style="color: var(--purple);" data-uzs="{stats['full_income'] / max(stats.get('period_days', 8), 1)}">+{stats['full_income'] / max(stats.get('period_days', 8), 1):,.0f} сум/дн</div>
                    <div class="kpi-sub">Дневной приток</div>
                </div>
            </div>

            <div class="dashboard-grid-equal">
                <div class="widget-box">
                    <div class="widget-title">
                        <span>🟢 Структура каналов дохода</span>
                    </div>
                    <canvas id="incomePieChart" height="180"></canvas>
                </div>
                <div class="widget-box">
                    <div class="widget-title">
                        <span>📈 Прогноз накоплений на 12 месяцев</span>
                    </div>
                    <canvas id="incomeProjChart" height="180"></canvas>
                </div>
            </div>
        </div>

        <!-- ================= TAB 3: EXPENSES ================= -->
        <div id="tab-expenses" class="tab-view">
            <div class="kpi-grid">
                <div class="kpi-card exp">
                    <div class="kpi-title">Всего расходов</div>
                    <div class="kpi-val" style="color: var(--red);" data-uzs="{stats['total_expense']}">-{stats['total_expense']:,.0f} сум</div>
                    <div class="kpi-sub">За период {period_title}</div>
                </div>
                <div class="kpi-card nw">
                    <div class="kpi-title">Средний чек в день</div>
                    <div class="kpi-val" style="color: var(--accent-blue);" data-uzs="{stats['daily_avg_expense']}">{stats['daily_avg_expense']:,.0f} сум</div>
                    <div class="kpi-sub">Дневной расход</div>
                </div>
                <div class="kpi-card inc">
                    <div class="kpi-title">Сбережения</div>
                    <div class="kpi-val" style="color: var(--green);" data-uzs="{stats['savings']}">+{stats['savings']:,.0f} сум</div>
                    <div class="kpi-sub">Норма сбережений {stats['savings_rate']:.0f}%</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Категорий трат</div>
                    <div class="kpi-val" style="color: var(--text-main);">{len(cats)}</div>
                    <div class="kpi-sub">Активных категорий</div>
                </div>
            </div>

            <div class="dashboard-grid">
                <div class="widget-box">
                    <div class="widget-title">
                        <span>🔴 Рейтинг категорий расходов</span>
                    </div>
                    {cat_rows_html}
                </div>
                <div class="widget-box">
                    <div class="widget-title">
                        <span>🎯 Контроль бюджета (50/30/20)</span>
                    </div>
                    <canvas id="budgetDonutChart" height="180"></canvas>
                </div>
            </div>
        </div>

        <!-- ================= TAB 4: DEBTS ================= -->
        <div id="tab-debts" class="tab-view">
            <div class="kpi-grid">
                <div class="kpi-card debt">
                    <div class="kpi-title">Общий долг</div>
                    <div class="kpi-val" style="color: #fb7185;" data-uzs="{summary['total_debt']}">-{summary['total_debt']:,.0f} сум</div>
                    <div class="kpi-sub">{len(credit_cards)} обязательств</div>
                </div>
                <div class="kpi-card inc">
                    <div class="kpi-title">Выплачено по рассрочкам</div>
                    <div class="kpi-val" style="color: var(--green);" data-uzs="{total_paid_debts}">{total_paid_debts:,.0f} сум</div>
                    <div class="kpi-sub">{round(total_paid_debts / max(total_limits_debts, 1.0) * 100, 1)}% от общего объема</div>
                </div>
                <div class="kpi-card nw">
                    <div class="kpi-title">Доступно по картам</div>
                    <div class="kpi-val" style="color: var(--accent-cyan);" data-uzs="{sum(c['available'] for c in credit_cards if 'карт' in c['account'].name.lower())}">
                        {sum(c['available'] for c in credit_cards if 'карт' in c['account'].name.lower()):,.0f} сум
                    </div>
                    <div class="kpi-sub">Кредитная карта TEZ</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Долговая нагрузка (DTI)</div>
                    <div class="kpi-val" style="color: var(--red);">{round(summary['total_debt'] / max(stats['full_income'], 1.0), 1)} мес</div>
                    <div class="kpi-sub">Месяцев дохода</div>
                </div>
            </div>

            <div class="widget-box" style="margin-bottom: 24px;">
                <div class="widget-title">
                    <span>🚗 Детализированный реестр обязательств</span>
                </div>
                {debts_cards_html}
            </div>

            <div class="widget-box">
                <div class="widget-title">
                    <span>⚡️ Рекомендованная стратегия погашения (Метод Снежного кома)</span>
                </div>
                <div style="font-size: 13px; line-height: 1.8; color: var(--text-muted);">
                    <p>1. <strong style="color: #f8fafc;">Курс на Skillbox (остаток 5 000 000 сум):</strong> Закрыть первым — освободит психологический ресурс.</p>
                    <p>2. <strong style="color: #f8fafc;">Кредитная карта TEZ (11 054 217 сум):</strong> Погасить в течение льготного периода (62 дня) без процентов.</p>
                    <p>3. <strong style="color: #f8fafc;">Рассрочка за авто (120 229 156 сум):</strong> Направить весь освободившийся бюджет на досрочное закрытие авто.</p>
                </div>
            </div>
        </div>

        <!-- ================= TAB 5: BUDGETING ================= -->
        <div id="tab-budget" class="tab-view">
            <div class="widget-box" style="margin-bottom: 24px;">
                <div class="widget-title">
                    <span>💰 Бюджетное правило 50 / 30 / 20</span>
                </div>
                <div style="font-size: 13px; line-height: 1.8; color: var(--text-muted); margin-bottom: 20px;">
                    <p>• <strong>50% Базовые нужды:</strong> жилье, коммуналка, питание, транспорт, обязательные платежи.</p>
                    <p>• <strong>30% Желания:</strong> рестораны, развлечения, покупки, подписки.</p>
                    <p>• <strong>20% Финансовое будущее:</strong> инвестиции, накопления, подушка безопасности, досрочные выплаты.</p>
                </div>
                <div class="debt-item">
                    <div class="debt-header">
                        <span>🟢 Сбережения и капитал</span>
                        <span style="color: var(--green);">100% (Идеально)</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: 100%;"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ================= TAB 6: GOALS ================= -->
        <div id="tab-goals" class="tab-view">
            <div class="widget-box">
                <div class="widget-title">
                    <span>🎯 Ваши финансовые цели</span>
                </div>
                <div class="debt-item">
                    <div class="debt-header">
                        <span>🛡 Подушка безопасности (6 месяцев)</span>
                        <span style="color: var(--accent-cyan);">Цель: 72 000 000 сум</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: 17%;"></div>
                    </div>
                    <div class="debt-sub">
                        <span>Накоплено: 12 000 000 сум (17%)</span>
                        <span>Осталось: 60 000 000 сум</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- ================= TAB 7: INVESTMENTS ================= -->
        <div id="tab-invest" class="tab-view">
            <div class="widget-box">
                <div class="widget-title">
                    <span>📈 Вклады и Инвестиции в Узбекистане</span>
                </div>
                <p style="font-size: 13px; color: var(--text-muted); line-height: 1.8;">
                    Банки Узбекистана (Капиталбанк, TBC, Ипак Йули) предлагают доходность по сумовым депозитам до <strong>22-23% годовых</strong> с ежемесячной капитализацией.
                </p>
                <div style="margin-top: 16px; background: rgba(255,255,255,0.02); padding: 16px; border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 13px; font-weight: bold; margin-bottom: 8px; color: var(--accent-cyan);">💡 Симулятор сложного процента (если откладывать 3 млн сум/мес):</div>
                    <div style="font-size: 13px; color: var(--text-main);">
                        • Через 1 год: <strong>~40 500 000 сум</strong> (из них проценты: +4 500 000 сум)<br>
                        • Через 3 года: <strong>~152 000 000 сум</strong> (из них проценты: +44 000 000 сум)<br>
                        • Через 5 лет: <strong>~325 000 000 сум</strong> (из них проценты: +145 000 000 сум)
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Tab switching logic
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-view').forEach(view => {{
                view.style.display = 'none';
                view.classList.remove('active');
            }});
            document.querySelectorAll('.nav-item').forEach(nav => {{
                nav.classList.remove('active');
            }});

            const target = document.getElementById('tab-' + tabId);
            if (target) {{
                target.style.display = 'block';
                target.classList.add('active');
            }}

            const activeNav = document.getElementById('nav-' + tabId);
            if (activeNav) {{
                activeNav.classList.add('active');
            }}

            window.dispatchEvent(new Event('resize'));
        }}

        // Month selector logic
        function switchMonth(el, monthName) {{
            document.querySelectorAll('.month-pill').forEach(pill => pill.classList.remove('active'));
            el.classList.add('active');
            showToast('Выбран период: ' + monthName);
        }}

        // Currency Toggle
        let currentCurrency = 'UZS';
        const usdRate = {usd_rate};

        function toggleCurrency() {{
            currentCurrency = (currentCurrency === 'UZS') ? 'USD' : 'UZS';
            document.getElementById('cur-toggle-btn').innerText = (currentCurrency === 'UZS') ? '🇺🇿 UZS (Сум)' : '🇺🇸 USD ($)';

            document.querySelectorAll('[data-uzs]').forEach(el => {{
                const uzs = parseFloat(el.getAttribute('data-uzs'));
                if (isNaN(uzs)) return;
                const sign = uzs < 0 ? '-' : (el.innerText.startsWith('+') ? '+' : '');
                const absVal = Math.abs(uzs);

                if (currentCurrency === 'USD') {{
                    const usd = absVal / usdRate;
                    el.innerText = sign + '$' + usd.toLocaleString(undefined, {{minimumFractionDigits: 0, maximumFractionDigits: 0}});
                }} else {{
                    el.innerText = sign + absVal.toLocaleString() + ' сум';
                }}
            }});
            showToast('Валюта изменена на: ' + currentCurrency);
        }}

        function showToast(msg) {{
            let t = document.getElementById('toast');
            if (!t) {{
                t = document.createElement('div');
                t.id = 'toast';
                t.style.position = 'fixed';
                t.style.bottom = '24px';
                t.style.right = '24px';
                t.style.background = '#1e1b4b';
                t.style.color = '#38bdf8';
                t.style.padding = '12px 20px';
                t.style.borderRadius = '12px';
                t.style.boxShadow = '0 8px 24px rgba(0,0,0,0.5)';
                t.style.border = '1px solid #4338ca';
                t.style.fontSize = '13px';
                t.style.fontWeight = 'bold';
                t.style.zIndex = '9999';
                t.style.transition = 'opacity 0.3s';
                document.body.appendChild(t);
            }}
            t.innerText = msg;
            t.style.opacity = '1';
            setTimeout(() => {{ t.style.opacity = '0'; }}, 2500);
        }}

        // Cashflow Combo Chart
        const ctxCf = document.getElementById('cfComboChart').getContext('2d');
        new Chart(ctxCf, {{
            type: 'bar',
            data: {{
                labels: ['Доходы', 'Расходы', 'Сбережения'],
                datasets: [{{
                    label: 'Сумма (сум)',
                    data: [{stats['full_income']}, {stats['total_expense']}, {max(stats['savings'], 0.0)}],
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.85)',
                        'rgba(244, 63, 94, 0.85)',
                        'rgba(0, 210, 255, 0.85)'
                    ],
                    borderRadius: 8,
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.raw.toLocaleString() + ' сум';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#232d5e' }} }},
                    x: {{ ticks: {{ color: '#f8fafc', font: {{ weight: 'bold' }} }}, grid: {{ display: false }} }}
                }}
            }}
        }});

        // Income Pie Chart
        const ctxInc = document.getElementById('incomePieChart').getContext('2d');
        new Chart(ctxInc, {{
            type: 'doughnut',
            data: {{
                labels: ['Зарплата (Humo)', 'Пассивный доход'],
                datasets: [{{
                    data: [{stats['total_income']}, {stats['total_passive']}],
                    backgroundColor: ['#10b981', '#fbbf24'],
                    borderColor: '#121735',
                    borderWidth: 3
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ color: '#f8fafc' }} }}
                }}
            }}
        }});

        // Income Projection Chart
        const ctxProj = document.getElementById('incomeProjChart').getContext('2d');
        new Chart(ctxProj, {{
            type: 'bar',
            data: {{
                labels: ['3 мес', '6 мес', '9 мес', '12 мес'],
                datasets: [{{
                    label: 'Накоплено (млн сум)',
                    data: [{stats['full_income'] * 3 / 1e6}, {stats['full_income'] * 6 / 1e6}, {stats['full_income'] * 9 / 1e6}, {stats['full_income'] * 12 / 1e6}],
                    backgroundColor: '#38bdf8',
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#232d5e' }} }},
                    x: {{ ticks: {{ color: '#f8fafc' }}, grid: {{ display: false }} }}
                }}
            }}
        }});

        // Budget Donut Chart
        const ctxBgt = document.getElementById('budgetDonutChart').getContext('2d');
        new Chart(ctxBgt, {{
            type: 'doughnut',
            data: {{
                labels: ['Сбережения (100%)', 'Расходы (0%)'],
                datasets: [{{
                    data: [{max(stats['savings'], 1.0)}, {stats['total_expense']}],
                    backgroundColor: ['#10b981', '#f43f5e'],
                    borderColor: '#121735',
                    borderWidth: 3
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ color: '#f8fafc' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        return html
