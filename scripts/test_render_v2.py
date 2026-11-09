import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle
import io

def draw_card(ax, x, y, w, h, bg="#121735", border="#232d5e", rad=0.03):
    box = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.01,rounding_size={rad}",
                         facecolor=bg, edgecolor=border, linewidth=1.4,
                         transform=ax.transAxes, clip_on=False, zorder=1)
    ax.add_patch(box)
    return box

def test():
    fig = plt.figure(figsize=(16, 11), dpi=180, facecolor="#080b1d")
    gs = GridSpec(3, 3, figure=fig, height_ratios=[0.9, 2.4, 2.7], hspace=0.32, wspace=0.22)
    
    # ---------------- ROW 0: TOP 4 KPI CARDS ----------------
    ax_kpi = fig.add_subplot(gs[0, :])
    ax_kpi.axis("off")
    
    kpis = [
        ("ЧИСТЫЙ КАПИТАЛ", "-124 283 373 сум", "-$10 368 • Активы - Долги", "#f43f5e"),
        ("ДОХОДЫ ЗА МЕСЯЦ", "+12 000 000 сум", "Зарплата • Пассивный: +0", "#10b981"),
        ("РАСХОДЫ ЗА МЕСЯЦ", "-0 сум", "В день: 0 сум • Бюджет 100% OK", "#cbd5e1"),
        ("ОБЯЗАТЕЛЬСТВА", "-136 283 373 сум", "3 активных кредита/рассрочки", "#fb7185")
    ]
    for i, (title, val, sub, col) in enumerate(kpis):
        x = 0.01 + i * 0.25
        draw_card(ax_kpi, x, 0.05, 0.23, 0.9, bg="#121735", border="#232d5e")
        ax_kpi.text(x + 0.115, 0.72, title, transform=ax_kpi.transAxes,
                    color="#94a3b8", fontsize=8.5, weight="bold", ha="center", zorder=2)
        ax_kpi.text(x + 0.115, 0.42, val, transform=ax_kpi.transAxes,
                    color=col, fontsize=12, weight="bold", ha="center", zorder=2)
        ax_kpi.text(x + 0.115, 0.18, sub, transform=ax_kpi.transAxes,
                    color="#64748b", fontsize=7.5, ha="center", zorder=2)
        
    # ---------------- ROW 1 COL 0: CATEGORIES DONUT / BUDGET GAUGE ----------------
    ax_donut = fig.add_subplot(gs[1, 0], facecolor="#121735")
    draw_card(ax_donut, 0, 0, 1, 1, bg="#121735", border="#232d5e")
    ax_donut.set_title("Структура расходов (Ноябрь 2026)", color="#f8fafc", fontsize=10, weight="bold", pad=12)
    # Empty state / 100% savings circle
    circle = Circle((0.5, 0.5), 0.35, facecolor="none", edgecolor="#10b981", linewidth=8, transform=ax_donut.transAxes)
    ax_donut.add_patch(circle)
    ax_donut.text(0.5, 0.55, "100%", color="#10b981", fontsize=18, weight="bold", ha="center", va="center", transform=ax_donut.transAxes)
    ax_donut.text(0.5, 0.42, "СБЕРЕЖЕНИЯ", color="#94a3b8", fontsize=8, weight="bold", ha="center", va="center", transform=ax_donut.transAxes)
    ax_donut.text(0.5, 0.15, "Расходов в этом месяце еще не было\nВсе доходы направлены в сбережения", color="#64748b", fontsize=7.5, ha="center", va="center", transform=ax_donut.transAxes)
    ax_donut.axis("off")
    
    # ---------------- ROW 1 COL 1: CASHFLOW BARS ----------------
    ax_cf = fig.add_subplot(gs[1, 1], facecolor="#121735")
    for spine in ax_cf.spines.values():
        spine.set_color("#232d5e")
    cf_labels = ["Доходы", "Расходы", "Сбережения"]
    cf_vals = [12000000, 0, 12000000]
    cf_cols = ["#10b981", "#f43f5e", "#00d2ff"]
    bars = ax_cf.bar(cf_labels, cf_vals, color=cf_cols, width=0.45, zorder=3)
    ax_cf.grid(axis="y", linestyle="--", alpha=0.15, color="#f8fafc", zorder=0)
    ax_cf.tick_params(colors="#94a3b8", labelsize=8.5)
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax_cf.annotate(f"{int(h/1e6)} млн сум", xy=(bar.get_x() + bar.get_width()/2, h),
                           xytext=(0, 4), textcoords="offset points", ha="center", va="bottom",
                           fontweight="bold", fontsize=8, color="#f8fafc")
    ax_cf.set_title("Денежный поток (Cashflow)", color="#f8fafc", fontsize=10, weight="bold", pad=12)
    
    # ---------------- ROW 1 COL 2: VIRTUAL CARD WIDGET ----------------
    ax_card = fig.add_subplot(gs[1, 2])
    ax_card.axis("off")
    # Draw card container
    draw_card(ax_card, 0.02, 0.02, 0.96, 0.96, bg="#121735", border="#232d5e")
    # Draw card inside
    c_bg = FancyBboxPatch((0.08, 0.12), 0.84, 0.76, boxstyle="round,pad=0.01,rounding_size=0.06",
                          facecolor="#1c1642", edgecolor="#4c1d95", linewidth=1.5,
                          transform=ax_card.transAxes, clip_on=False, zorder=2)
    ax_card.add_patch(c_bg)
    # Chip
    chip = Rectangle((0.14, 0.58), 0.14, 0.14, facecolor="#eab308", edgecolor="#ca8a04",
                     transform=ax_card.transAxes, zorder=3)
    ax_card.add_patch(chip)
    ax_card.text(0.86, 0.72, "HUMO", transform=ax_card.transAxes, color="#f8fafc",
                fontsize=11, weight="bold", ha="right", zorder=3)
    ax_card.text(0.14, 0.42, "•••• •••• •••• 4821", transform=ax_card.transAxes,
                color="#94a3b8", fontsize=9, fontfamily="monospace", zorder=3)
    ax_card.text(0.14, 0.28, "12 000 000 сум", transform=ax_card.transAxes,
                color="#34d399", fontsize=12, weight="bold", zorder=3)
    ax_card.text(0.14, 0.18, "ЗАРПЛАТНАЯ КАРТА (~$1 001)", transform=ax_card.transAxes,
                color="#cbd5e1", fontsize=6.5, weight="bold", zorder=3)
    ax_card.text(0.5, 0.94, "Основной счет / Активы", transform=ax_card.transAxes,
                color="#f8fafc", fontsize=9.5, weight="bold", ha="center")
    
    # ---------------- ROW 2 COLS 0-1: DETAILED DEBTS BREAKDOWN ----------------
    ax_debts = fig.add_subplot(gs[2, :2], facecolor="#121735")
    ax_debts.axis("off")
    draw_card(ax_debts, 0, 0, 1, 1, bg="#121735", border="#232d5e")
    ax_debts.text(0.04, 0.90, "ДЕТАЛИЗАЦИЯ ОБЯЗАТЕЛЬСТВ И РАССРОЧЕК", transform=ax_debts.transAxes,
                 color="#f8fafc", fontsize=10.5, weight="bold", zorder=2)
    
    debts = [
        ("Рассрочка за авто (36 мес)", 206640160, 86411004, 120229156, "🚗"),
        ("Курс Skillbox Архитектор ПО (10 мес)", 6000000, 1000000, 5000000, "🎓"),
        ("Кредитная карта TEZ (Лимит 22 млн)", 22000000, 10945783, 11054217, "💳")
    ]
    for idx, (name, total, paid, debt, icon) in enumerate(debts):
        y = 0.65 - idx * 0.27
        pct = round(paid / total * 100, 1)
        ax_debts.text(0.04, y + 0.11, f"{icon} {name}", transform=ax_debts.transAxes,
                     color="#f8fafc", fontsize=9, weight="bold", zorder=2)
        ax_debts.text(0.96, y + 0.11, f"Остаток: {debt:,.0f} сум".replace(",", " "),
                     transform=ax_debts.transAxes, color="#f43f5e", fontsize=8.5, weight="bold", ha="right", zorder=2)
        
        # Background bar
        bar_bg = FancyBboxPatch((0.04, y), 0.92, 0.07, boxstyle="round,pad=0.005,rounding_size=0.03",
                                facecolor="#1e2548", edgecolor="none", transform=ax_debts.transAxes, zorder=2)
        ax_debts.add_patch(bar_bg)
        # Paid progress bar
        p_w = max(0.92 * (paid / total), 0.02)
        bar_p = FancyBboxPatch((0.04, y), p_w, 0.07, boxstyle="round,pad=0.005,rounding_size=0.03",
                               facecolor="#10b981", edgecolor="none", transform=ax_debts.transAxes, zorder=3)
        ax_debts.add_patch(bar_p)
        
        ax_debts.text(0.05, y - 0.06, f"Выплачено: {paid:,.0f} сум ({pct}%) из {total:,.0f} сум".replace(",", " "),
                     transform=ax_debts.transAxes, color="#94a3b8", fontsize=7.5, zorder=2)
        
    # ---------------- ROW 2 COL 2: WEALTH HEALTH PULSE ----------------
    ax_pulse = fig.add_subplot(gs[2, 2], facecolor="#121735")
    ax_pulse.axis("off")
    draw_card(ax_pulse, 0, 0, 1, 1, bg="#121735", border="#232d5e")
    ax_pulse.text(0.08, 0.88, "ФИНАНСОВЫЙ ПУЛЬС", transform=ax_pulse.transAxes,
                 color="#00d2ff", fontsize=10, weight="bold", zorder=2)
    
    pulse_items = [
        ("Подушка безопасности", "Бессрочно (нет трат)", "#10b981"),
        ("Норма сбережений", "100% от дохода", "#00d2ff"),
        ("Долговая нагрузка", "11.3 мес. дохода", "#f43f5e"),
        ("Пассивный доход", "+0 сум/день (депозиты 22%)", "#fbbf24"),
        ("Официальный курс ЦБ", "1 USD = 11 987 сум", "#94a3b8")
    ]
    for idx, (label, val, col) in enumerate(pulse_items):
        y = 0.72 - idx * 0.14
        ax_pulse.text(0.08, y + 0.04, label, transform=ax_pulse.transAxes,
                     color="#94a3b8", fontsize=8, zorder=2)
        ax_pulse.text(0.08, y - 0.03, val, transform=ax_pulse.transAxes,
                     color=col, fontsize=8.5, weight="bold", zorder=2)
        
    fig.suptitle("PERSONAL FINANCE DIRECTOR • EXECUTIVE DASHBOARD • УЗБЕКИСТАН",
                 color="#f8fafc", fontsize=13, weight="bold", y=0.98)
    
    plt.savefig("/tmp/full_dashboard_preview.png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    print("Full Dashboard V2 Rendered Successfully!")

test()
