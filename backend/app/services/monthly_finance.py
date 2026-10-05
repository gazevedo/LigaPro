"""Game-month fixed income and summaries; salary settlement stays in contracts."""

from datetime import timedelta

from bson import ObjectId

from app.config.economy import EconomyConfig, payroll_health
from app.config.game import GameConfig
from app.models.game import utcnow


class MonthlyFinanceService:
    @staticmethod
    def initialize(repo, club_id, now=None):
        config = EconomyConfig.from_rules(repo.rules())
        now = now or utcnow()
        period = timedelta(days=GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS) / 12
        repo.update(
            "club_finances",
            {"_id": club_id},
            {
                "$set": {
                    "club_id": club_id,
                    "cash_balance": repo.find("club_finances", {"_id": club_id})["balance"],
                    "monthly_fixed_revenue": config.fixed_revenue,
                    "monthly_income": 0,
                    "monthly_expenses": 0,
                    "monthly_result": 0,
                    "finance_started_at": now,
                    "next_month_at": now + period,
                    "month_seconds": period.total_seconds(),
                    "updated_at": now,
                }
            },
        )
        repo.money(club_id, config.STARTING_CASH, "other_income", "initial_funding")

    @classmethod
    def process_due(cls, repo, now=None):
        now = now or utcnow()
        for finance in repo.many("club_finances", {"next_month_at": {"$lte": now}}, limit=None):
            while True:

                def operation(tx):
                    current = tx.find("club_finances", {"_id": finance["_id"]})
                    if not current or current.get("next_month_at", now + timedelta(days=1)) > now:
                        return False
                    end = current["next_month_at"]
                    period = timedelta(seconds=current["month_seconds"])
                    start = end - period
                    config = EconomyConfig.from_rules(tx.rules())
                    from app.services.player_contracts import ContractService

                    for contract in tx.many(
                        "player_contracts",
                        {"club_id": current["_id"], "status": {"$in": ["active", "expiring"]}},
                        limit=None,
                    ):
                        ContractService.settle_salary(tx, contract, end)
                    # Touch the financial document before writing the unique period marker.
                    tx.update(
                        "club_finances",
                        {"_id": current["_id"]},
                        {"$set": {"next_month_at": end + period}},
                    )
                    tx.money(
                        current["_id"],
                        config.MONTHLY_SPONSORSHIP,
                        "sponsorship",
                        end,
                        effective_at=end - timedelta(microseconds=1),
                    )
                    tx.money(
                        current["_id"],
                        config.MONTHLY_TV_REVENUE,
                        "tv_rights",
                        end,
                        effective_at=end - timedelta(microseconds=1),
                    )
                    tx.insert(
                        "club_finance_months",
                        {
                            "_id": ObjectId(),
                            "club_id": current["_id"],
                            "start": start,
                            "end": end,
                            "fixed_revenue": config.fixed_revenue,
                        },
                    )
                    cls.summary(tx, current["_id"])
                    return True

                if not repo.transaction(operation):
                    break

    @staticmethod
    def summary(repo, club_id):
        from app.services.player_contracts import ContractService

        config = EconomyConfig.from_rules(repo.rules())
        finance = repo.find("club_finances", {"_id": club_id})
        period = finance.get("month_seconds", 216000)
        closed = repo.many("club_finance_months", {"club_id": club_id}, limit=1, sort=[("end", -1)])
        end = closed[0]["end"] if closed else finance.get("next_month_at", utcnow())
        rows = list(
            repo.database.financial_transactions.aggregate(
                [
                    {
                        "$match": {
                            "club_id": club_id,
                            "created_at": {"$gte": end - timedelta(seconds=period), "$lt": end},
                        }
                    },
                    {
                        "$group": {
                            "_id": "$category",
                            "amount": {"$sum": "$amount"},
                            "income": {"$sum": {"$cond": [{"$gt": ["$amount", 0]}, "$amount", 0]}},
                            "expenses": {
                                "$sum": {
                                    "$cond": [
                                        {"$lt": ["$amount", 0]},
                                        {"$multiply": ["$amount", -1]},
                                        0,
                                    ]
                                }
                            },
                        }
                    },
                ],
                session=repo.session,
            )
        )
        amounts = {r["_id"]: r["amount"] for r in rows}
        income = sum(row["income"] for row in rows)
        initial = repo.find(
            "financial_transactions",
            {
                "club_id": club_id,
                "reference_id": "initial_funding",
                "created_at": {"$gte": end - timedelta(seconds=period), "$lt": end},
            },
        )
        if initial:
            income -= initial["amount"]
        expenses = sum(row["expenses"] for row in rows)
        prizes = list(
            repo.database.financial_transactions.aggregate(
                [
                    {"$match": {"club_id": club_id, "category": "prize"}},
                    {"$group": {"_id": None, "amount": {"$sum": "$amount"}}},
                ],
                session=repo.session,
            )
        )
        payroll = ContractService.payroll(repo, club_id)
        values = {
            "cash_balance": finance["balance"],
            "monthly_fixed_revenue": config.fixed_revenue,
            "monthly_payroll": payroll,
            "monthly_income": income,
            "monthly_period_end": end,
            "monthly_expenses": expenses,
            "monthly_result": income - expenses,
            "sponsorship": amounts.get("sponsorship", 0),
            "tv_rights": amounts.get("tv_rights", 0),
            "ticketing": amounts.get("ticketing", 0),
            "other_expenses": expenses
            - abs(amounts.get("salary", 0) + amounts.get("player_salary", 0)),
            "accumulated_prizes": prizes[0]["amount"] if prizes else 0,
            "payroll_health": payroll_health(payroll, config.fixed_revenue),
            "updated_at": utcnow(),
        }
        repo.update(
            "club_finances",
            {"_id": club_id},
            {"$set": {key: value for key, value in values.items() if key != "cash_balance"}},
        )
        return values


def bootstrap_economy(repo):
    from app.services.fan_base import FanBaseService

    for club in repo.many("clubs", {}, limit=None):

        def operation(tx, identity=club["_id"]):
            FanBaseService.initialize(tx, identity)
            finance = tx.find("club_finances", {"_id": identity})
            if finance and "next_month_at" not in finance:
                # Preserve existing balances/contracts; begin monthly receipts now.
                config = EconomyConfig.from_rules(tx.rules())
                now = utcnow()
                period = timedelta(days=GameConfig.from_rules(tx.rules()).SEASON_DURATION_DAYS) / 12
                tx.update(
                    "club_finances",
                    {"_id": identity},
                    {
                        "$set": {
                            "club_id": identity,
                            "cash_balance": finance["balance"],
                            "monthly_fixed_revenue": config.fixed_revenue,
                            "finance_started_at": now,
                            "next_month_at": now + period,
                            "month_seconds": period.total_seconds(),
                            "updated_at": now,
                        }
                    },
                )

        repo.transaction(operation)
