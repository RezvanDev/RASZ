from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import (
    User, Account, Category, Transaction, Goal, DailyAccrualLog,
    AccountType, TransactionType
)

class FinanceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(self, telegram_id: int, username: Optional[str] = None, full_name: Optional[str] = None) -> User:
        stmt = select(User).where(User.telegram_id == telegram_id).options(
            selectinload(User.accounts)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=telegram_id,
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                currency="UZS"
            )
            self.session.add(user)
            await self.session.flush()

            # Create default card account
            default_account = Account(
                user_id=user.id,
                name="Uzcard / Humo",
                account_type=AccountType.CARD,
                balance=0.0,
                interest_rate=0.0,
                currency="UZS"
            )
            self.session.add(default_account)
            await self.session.commit()
            await self.session.refresh(user)

        return user

    async def get_accounts(self, user_id: int) -> List[Account]:
        stmt = select(Account).where(Account.user_id == user_id, Account.is_active.is_(True)).order_by(Account.account_type)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    def find_matching_account(
        self,
        accounts: List[Account],
        name: str,
        account_type: Optional[AccountType] = None
    ) -> Optional[Account]:
        """Intelligently matches an account by name, aliases, or key brand words."""
        if not accounts or not name:
            return None

        import re
        raw_name = name.strip()
        # Clean prefix noise like 'остаток задолженности по', 'долг по'
        clean_target = re.sub(
            r'^(остаток\s+(задолженности|долга)?\s*(по)?|задолженность\s*(по)?|долг\s*(по)?)\s*',
            '',
            raw_name,
            flags=re.IGNORECASE
        ).strip().lower()

        raw_lower = raw_name.lower()

        # 1. Exact match on raw name or cleaned name
        for a in accounts:
            a_lower = a.name.lower()
            if a_lower == raw_lower or a_lower == clean_target:
                return a

        # 2. Substring match (either clean_target in a_lower or a_lower in clean_target)
        for a in accounts:
            if account_type and a.account_type != account_type:
                continue
            a_lower = a.name.lower()
            if clean_target in a_lower or a_lower in clean_target:
                return a

        # 3. Significant keywords overlap (brands like 'tez', 'skillbox', 'авто', 'uzum')
        stop_words = {"кредитная", "карта", "счет", "вклад", "рассрочка", "банк", "по", "за", "на", "uzs", "сум"}
        target_words = set(re.findall(r'[a-zа-яё0-9]+', clean_target)) - stop_words

        if target_words:
            for a in accounts:
                if account_type and a.account_type != account_type:
                    continue
                a_words = set(re.findall(r'[a-zа-яё0-9]+', a.name.lower())) - stop_words
                if target_words & a_words:
                    return a

        return None

    async def get_account_by_name_or_default(self, user_id: int, name: Optional[str] = None) -> Optional[Account]:
        accounts = await self.get_accounts(user_id)
        if not accounts:
            return None

        # Helper to find default debit card
        def default_debit():
            for a in accounts:
                if a.account_type == AccountType.CARD:
                    return a
            for a in accounts:
                if a.account_type == AccountType.CASH:
                    return a
            return accounts[0]

        if not name or not name.strip():
            return default_debit()

        matched = self.find_matching_account(accounts, name)
        return matched if matched else default_debit()

    async def create_or_update_account(
        self,
        user_id: int,
        name: str,
        account_type: AccountType,
        balance: float,
        interest_rate: float = 0.0,
        credit_limit: float = 0.0,
        grace_period_days: int = 0,
        currency: str = "UZS"
    ) -> Account:
        accounts = await self.get_accounts(user_id)
        # Use smart matching so variations like 'Остаток по карте TEZ' match 'Кредитная карта TEZ'
        acc = self.find_matching_account(accounts, name, account_type=account_type)

        if acc:
            acc.balance = balance
            if interest_rate > 0 or acc.interest_rate == 0:
                acc.interest_rate = interest_rate
            if credit_limit > 0 or acc.credit_limit == 0:
                acc.credit_limit = credit_limit
            if grace_period_days > 0 or acc.grace_period_days == 0:
                acc.grace_period_days = grace_period_days
            acc.account_type = account_type
            acc.currency = currency
            acc.is_active = True
        else:
            acc = Account(
                user_id=user_id,
                name=name,
                account_type=account_type,
                balance=balance,
                interest_rate=interest_rate,
                credit_limit=credit_limit,
                grace_period_days=grace_period_days,
                currency=currency
            )
            self.session.add(acc)

        await self.session.commit()
        await self.session.refresh(acc)
        return acc

    async def transfer_funds(
        self,
        user_id: int,
        from_account_name: str,
        to_account_name: str,
        amount: float,
        description: Optional[str] = None
    ) -> Tuple[Account, Account, Transaction]:
        from_acc = await self.get_account_by_name_or_default(user_id, from_account_name)
        to_acc = await self.get_account_by_name_or_default(user_id, to_account_name)
        if not from_acc or not to_acc or from_acc.id == to_acc.id:
            raise ValueError("Некорректные счета для перевода")

        from_acc.balance -= amount
        to_acc.balance += amount

        tx = Transaction(
            user_id=user_id,
            account_id=from_acc.id,
            to_account_id=to_acc.id,
            type=TransactionType.TRANSFER,
            amount=amount,
            date=datetime.utcnow(),
            description=description or f"Перевод с '{from_acc.name}' на '{to_acc.name}'"
        )
        self.session.add(tx)
        await self.session.commit()
        await self.session.refresh(from_acc)
        await self.session.refresh(to_acc)
        await self.session.refresh(tx)
        return from_acc, to_acc, tx

    async def get_or_create_category(self, user_id: int, category_name: str, tx_type: TransactionType) -> Category:
        clean_name = category_name.strip()
        stmt = select(Category).where(
            or_(Category.user_id == user_id, Category.user_id.is_(None)),
            Category.type == tx_type
        )
        res = await self.session.execute(stmt)
        categories = list(res.scalars().all())

        clean_lower = clean_name.lower()
        for c in categories:
            if c.name.lower() == clean_lower:
                return c

        cat = Category(
            user_id=user_id,
            name=clean_name.capitalize(),
            type=tx_type,
            icon="💡"
        )
        self.session.add(cat)
        await self.session.flush()
        return cat

    async def set_category_budget(self, user_id: int, category_name: str, monthly_budget: float) -> Category:
        """Sets a monthly spending limit for an expense category."""
        cat = await self.get_or_create_category(user_id, category_name, TransactionType.EXPENSE)
        cat.monthly_budget = monthly_budget
        await self.session.commit()
        await self.session.refresh(cat)
        return cat

    async def get_category_month_spent(self, user_id: int, category_id: int) -> float:
        now = datetime.utcnow()
        start_m = datetime(now.year, now.month, 1)
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.date >= start_m
        )
        res = await self.session.execute(stmt)
        return float(res.scalar() or 0.0)

    async def add_transaction(
        self,
        user_id: int,
        amount: float,
        tx_type: TransactionType,
        category_name: str,
        account_name: Optional[str] = None,
        description: Optional[str] = None,
        tx_date: Optional[datetime] = None
    ) -> Tuple[Transaction, Account, Optional[str]]:
        account = await self.get_account_by_name_or_default(user_id, account_name)
        if not account:
            account = await self.create_or_update_account(
                user_id=user_id,
                name="Uzcard / Humo",
                account_type=AccountType.CARD,
                balance=0.0
            )

        cat = await self.get_or_create_category(user_id, category_name, tx_type)
        dt = tx_date or datetime.utcnow()

        # Update balance
        if tx_type == TransactionType.EXPENSE:
            account.balance -= amount
        elif tx_type in (TransactionType.INCOME, TransactionType.PASSIVE_INCOME):
            account.balance += amount

        tx = Transaction(
            user_id=user_id,
            account_id=account.id,
            category_id=cat.id,
            type=tx_type,
            amount=amount,
            date=dt,
            description=description
        )
        self.session.add(tx)
        await self.session.commit()
        await self.session.refresh(tx)
        await self.session.refresh(account)

        # Check monthly budget alert
        budget_alert = None
        if tx_type == TransactionType.EXPENSE and cat.monthly_budget and cat.monthly_budget > 0:
            month_spent = await self.get_category_month_spent(user_id, cat.id)
            pct = round((month_spent / cat.monthly_budget) * 100)
            if month_spent > cat.monthly_budget:
                budget_alert = f"⚠️ <b>Превышен лимит!</b> По категории '{cat.name}' израсходовано {month_spent:,.0f} из {cat.monthly_budget:,.0f} сум ({pct}%)."
            elif pct >= 80:
                budget_alert = f"⚠️ <b>Внимание:</b> по категории '{cat.name}' израсходовано {pct}% лимита ({month_spent:,.0f} из {cat.monthly_budget:,.0f} сум)."

        return tx, account, budget_alert

    async def get_net_worth_summary(self, user_id: int) -> Dict[str, Any]:
        """Calculates total net worth, breakdown by asset class, liabilities (credit debt) and passive income rate."""
        accounts = await self.get_accounts(user_id)

        # Asset classes
        liquid_types = (AccountType.CASH, AccountType.CARD)
        liquid_balance = sum(a.balance for a in accounts if a.account_type in liquid_types and a.balance > 0)
        deposits_balance = sum(a.balance for a in accounts if a.account_type == AccountType.DEPOSIT and a.balance > 0)
        invest_balance = sum(a.balance for a in accounts if a.account_type in (AccountType.INVEST, AccountType.CRYPTO) and a.balance > 0)

        # Total Assets (Все реальные активы)
        total_assets = liquid_balance + deposits_balance + invest_balance

        # Liabilities / Credit Debt (Долги по кредиткам и овердрафтам)
        total_debt = 0.0
        credit_cards = []
        for a in accounts:
            if a.account_type == AccountType.CREDIT_CARD:
                debt = abs(a.balance) if a.balance < 0 else 0.0
                available = max(a.credit_limit + a.balance, 0.0)
                total_debt += debt
                credit_cards.append({
                    "account": a,
                    "debt": round(debt, 2),
                    "limit": a.credit_limit,
                    "available": round(available, 2),
                    "grace_days": a.grace_period_days
                })
            elif a.balance < 0:
                total_debt += abs(a.balance)

        # Net Worth = Assets - Liabilities
        net_worth = round(total_assets - total_debt, 2)

        # Calculate annual, monthly, and daily passive yields from active deposits/investments
        annual_yield = sum(a.balance * (a.interest_rate / 100.0) for a in accounts if a.interest_rate > 0 and a.balance > 0)
        daily_yield = round(annual_yield / 365.0, 2)
        monthly_yield = round(annual_yield / 12.0, 2)

        return {
            "total_balance": net_worth,
            "total_assets": round(total_assets, 2),
            "total_debt": round(total_debt, 2),
            "liquid_balance": round(liquid_balance, 2),
            "deposits_balance": round(deposits_balance, 2),
            "invest_balance": round(invest_balance, 2),
            "annual_yield": round(annual_yield, 2),
            "monthly_yield": monthly_yield,
            "daily_yield": daily_yield,
            "accounts": accounts,
            "credit_cards": credit_cards
        }

    async def get_financial_stats(self, user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculates income, expenses, category breakdown, savings rate and runway."""
        # 1. Total expenses & incomes
        stmt_totals = select(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0.0)
        ).where(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).group_by(Transaction.type)

        totals_res = await self.session.execute(stmt_totals)
        totals = dict(totals_res.all())

        total_expense = totals.get(TransactionType.EXPENSE, 0.0)
        total_income = totals.get(TransactionType.INCOME, 0.0)
        total_passive = totals.get(TransactionType.PASSIVE_INCOME, 0.0)
        full_income = total_income + total_passive

        # Savings rate
        savings = full_income - total_expense
        savings_rate = round((savings / full_income * 100), 1) if full_income > 0 else 0.0

        # 2. Categories breakdown for expenses
        stmt_cats = select(
            Category.name,
            Category.icon,
            func.sum(Transaction.amount).label("cat_total")
        ).join(Transaction.category).where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).group_by(Category.id).order_by(func.sum(Transaction.amount).desc())

        cats_res = await self.session.execute(stmt_cats)
        cat_rows = cats_res.all()

        categories_breakdown = []
        for name, icon, amt in cat_rows:
            pct = round((amt / total_expense * 100), 1) if total_expense > 0 else 0.0
            categories_breakdown.append({
                "name": name,
                "icon": icon,
                "amount": round(amt, 2),
                "percent": pct
            })

        # 3. Daily average expense
        days = max((end_date - start_date).days, 1)
        daily_avg_expense = round(total_expense / days, 2)

        # 4. Runway (months of financial safety cushion)
        summary = await self.get_net_worth_summary(user_id)
        runway_months = round(summary["liquid_balance"] / (daily_avg_expense * 30), 1) if daily_avg_expense > 0 else 0.0

        return {
            "total_expense": round(total_expense, 2),
            "total_income": round(total_income, 2),
            "total_passive": round(total_passive, 2),
            "full_income": round(full_income, 2),
            "savings": round(savings, 2),
            "savings_rate": savings_rate,
            "daily_avg_expense": daily_avg_expense,
            "runway_months": runway_months,
            "categories": categories_breakdown,
            "period_days": days
        }

    async def process_daily_deposit_yields(self, target_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Accrues daily interest for active deposits and investment accounts."""
        today = target_date or date.today()
        # Find accounts with interest_rate > 0 and balance > 0
        stmt = select(Account).where(
            Account.interest_rate > 0,
            Account.balance > 0,
            Account.is_active.is_(True),
            or_(Account.last_interest_date.is_(None), Account.last_interest_date < today)
        )
        res = await self.session.execute(stmt)
        accounts = list(res.scalars().all())

        accruals = []
        for acc in accounts:
            daily_amount = round(acc.balance * (acc.interest_rate / 100.0) / 365.0, 2)
            if daily_amount <= 0:
                continue

            acc.balance += daily_amount
            acc.last_interest_date = today

            # Log accrual
            log = DailyAccrualLog(
                account_id=acc.id,
                date=today,
                amount=daily_amount
            )
            self.session.add(log)

            # Record passive income transaction
            tx = Transaction(
                user_id=acc.user_id,
                account_id=acc.id,
                type=TransactionType.PASSIVE_INCOME,
                amount=daily_amount,
                date=datetime.utcnow(),
                description=f"Начисление % по вкладу ({acc.name}, {acc.interest_rate}% годовых)"
            )
            self.session.add(tx)

            accruals.append({
                "user_id": acc.user_id,
                "account_name": acc.name,
                "amount": daily_amount,
                "new_balance": round(acc.balance, 2)
            })

        if accruals:
            await self.session.commit()

        return accruals

    async def create_goal(
        self,
        user_id: int,
        name: str,
        target_amount: float,
        target_date: Optional[date] = None
    ) -> Goal:
        goal = Goal(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            target_date=target_date,
            current_amount=0.0
        )
        self.session.add(goal)
        await self.session.commit()
        await self.session.refresh(goal)
        return goal

    async def get_goals(self, user_id: int) -> List[Dict[str, Any]]:
        stmt = select(Goal).where(Goal.user_id == user_id, Goal.is_completed.is_(False)).order_by(Goal.target_date)
        res = await self.session.execute(stmt)
        goals = list(res.scalars().all())

        result = []
        today = date.today()
        for g in goals:
            pct = round((g.current_amount / g.target_amount * 100), 1) if g.target_amount > 0 else 0.0
            remaining_amount = max(g.target_amount - g.current_amount, 0.0)

            monthly_needed = 0.0
            days_left = None
            if g.target_date:
                days_left = (g.target_date - today).days
                if days_left > 0:
                    months_left = max(days_left / 30.0, 1.0)
                    monthly_needed = round(remaining_amount / months_left, 2)

            result.append({
                "id": g.id,
                "name": g.name,
                "target_amount": g.target_amount,
                "current_amount": g.current_amount,
                "remaining_amount": round(remaining_amount, 2),
                "progress_percent": min(pct, 100.0),
                "target_date": g.target_date,
                "days_left": days_left,
                "monthly_needed": monthly_needed
            })
        return result

    async def get_last_transaction(self, user_id: int) -> Optional[Transaction]:
        stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.id.desc()).limit(1).options(
            selectinload(Transaction.account),
            selectinload(Transaction.category)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def delete_transaction(self, tx_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Deletes a transaction and safely rolls back the account balance."""
        stmt = select(Transaction).where(
            Transaction.id == tx_id,
            Transaction.user_id == user_id
        ).options(
            selectinload(Transaction.account),
            selectinload(Transaction.category)
        )
        res = await self.session.execute(stmt)
        tx = res.scalar_one_or_none()

        if not tx:
            return None

        account = tx.account
        cat_name = tx.category.name if tx.category else "Без категории"
        amount = tx.amount
        tx_type = tx.type

        # Revert balance
        if account:
            if tx_type == TransactionType.EXPENSE:
                account.balance += amount
            elif tx_type in (TransactionType.INCOME, TransactionType.PASSIVE_INCOME):
                account.balance -= amount

        await self.session.delete(tx)
        await self.session.commit()
        if account:
            await self.session.refresh(account)

        return {
            "id": tx_id,
            "amount": amount,
            "category": cat_name,
            "account": account.name if account else "Удаленный счет",
            "new_balance": account.balance if account else 0.0
        }

    async def delete_last_transaction(self, user_id: int) -> Optional[Dict[str, Any]]:
        last_tx = await self.get_last_transaction(user_id)
        if not last_tx:
            return None
        return await self.delete_transaction(last_tx.id, user_id)

    async def export_transactions_csv(self, user_id: int) -> str:
        """Exports all user transactions in CSV format."""
        import csv
        import io

        stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date.desc()).options(
            selectinload(Transaction.account),
            selectinload(Transaction.category)
        )
        res = await self.session.execute(stmt)
        txs = list(res.scalars().all())

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["ID", "Дата и время", "Тип", "Категория", "Сумма (сум)", "Счет", "Комментарий"])

        for t in txs:
            writer.writerow([
                t.id,
                t.date.strftime("%Y-%m-%d %H:%M:%S") if t.date else "",
                t.type.value,
                t.category.name if t.category else "Общее",
                f"{t.amount:.2f}",
                t.account.name if t.account else "",
                t.description or ""
            ])

        return output.getvalue()


