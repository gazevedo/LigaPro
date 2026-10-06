"""Bounded credit with positive total interest and monthly, idempotent installments."""

from datetime import timedelta

from bson import ObjectId
from fastapi import HTTPException

from app.config.game import GameConfig
from app.models.game import public, utcnow

PRODUCTS = {
    "short_term": {"installments": 3, "interest_rate": 0.09},
    "medium_term": {"installments": 6, "interest_rate": 0.18},
    "long_term": {"installments": 12, "interest_rate": 0.36},
}


class BankLoanService:
    @staticmethod
    def credit(repo, club_id):
        club = repo.find("clubs", {"_id": club_id}) or {}
        finance = repo.find("club_finances", {"_id": club_id}) or {}
        loans = repo.many(
            "club_loans", {"club_id": club_id, "status": {"$in": ["active", "overdue"]}}, limit=None
        )
        legacy = repo.many(
            "bank_contracts",
            {"club_id": club_id, "type": "bank_loan", "status": "active"},
            limit=None,
        )
        debt = sum(loan["remaining_balance"] for loan in loans) + sum(
            loan["amount"] + loan["interest"] for loan in legacy
        )
        revenue = max(
            0, finance.get("monthly_fixed_revenue", 1500000), finance.get("monthly_income", 0)
        )
        ceiling = min(
            repo.rules()["max_bank_loan"],
            round(
                revenue * 2
                + max(0, finance.get("balance", 0)) * 0.1
                + min(1000, club.get("reputation", 0)) * 100
            ),
        )
        blocked = any(loan["status"] == "overdue" for loan in loans) or any(
            loan.get("overdue") for loan in legacy
        )
        return {
            "credit_limit": max(0, ceiling - debt) if not blocked else 0,
            "debt": debt,
            "financial_risk": "high" if blocked else "moderate" if debt else "low",
            "credit_blocked": blocked,
        }

    @classmethod
    def contract(cls, repo, club_id, product, amount, now=None):
        if product not in PRODUCTS or amount <= 0:
            raise HTTPException(422, "Produto ou valor inválido.")
        now = now or utcnow()
        repo.update("club_finances", {"_id": club_id}, {"$inc": {"credit_revision": 1}})
        if amount > cls.credit(repo, club_id)["credit_limit"]:
            raise HTTPException(409, "Limite de crédito excedido ou parcelas em atraso.")
        if repo.find(
            "bank_contracts", {"club_id": club_id, "type": "investment", "status": "active"}
        ):
            raise HTTPException(409, "Encerre os investimentos antes de solicitar crédito.")
        terms = PRODUCTS[product]
        total = amount + max(1, round(amount * terms["interest_rate"]))
        period = timedelta(days=GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS / 12)
        finance = repo.find("club_finances", {"_id": club_id})
        next_at = finance.get("next_month_at", now + period)
        while next_at <= now:
            next_at += period
        loan = repo.insert(
            "club_loans",
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "product": product,
                "principal": amount,
                **terms,
                "installment_value": (total + terms["installments"] - 1) // terms["installments"],
                "remaining_balance": total,
                "paid_installments": 0,
                "status": "active",
                "created_at": now,
                "next_installment_at": next_at,
            },
        )
        repo.money(club_id, amount, "bank_loan", loan["_id"], effective_at=now)
        return public(loan)

    @classmethod
    def monthly(cls, repo, club_id, end, period):
        for loan in repo.many(
            "club_loans",
            {
                "club_id": club_id,
                "status": {"$in": ["active", "overdue"]},
                "next_installment_at": {"$lte": end},
            },
            limit=None,
        ):
            amount = min(loan["installment_value"], loan["remaining_balance"])
            balance = repo.find("club_finances", {"_id": club_id})["balance"]
            if balance < amount:
                repo.update(
                    "club_loans",
                    {"_id": loan["_id"]},
                    {"$set": {"status": "overdue", "missed_at": end}},
                )
                repo.update(
                    "club_finances",
                    {"_id": club_id},
                    {"$set": {"financial_risk": "high", "credit_blocked": True}},
                )
                continue
            repo.money(
                club_id,
                -amount,
                "loan_installment",
                f"{loan['_id']}:{loan['paid_installments']}",
                effective_at=end - timedelta(microseconds=1),
            )
            remaining = loan["remaining_balance"] - amount
            repo.update(
                "club_loans",
                {"_id": loan["_id"]},
                {
                    "$inc": {"paid_installments": 1},
                    "$set": {
                        "remaining_balance": remaining,
                        "status": "active" if remaining else "settled",
                        "next_installment_at": end + period,
                    },
                },
            )
        repo.update("club_finances", {"_id": club_id}, {"$set": cls.credit(repo, club_id)})

    @classmethod
    def settle(cls, repo, club_id, identity):
        loan = repo.document("club_loans", identity)
        if loan["club_id"] != club_id:
            raise HTTPException(403, "Empréstimo de outro clube.")
        if loan["status"] not in {"active", "overdue"}:
            raise HTTPException(409, "Empréstimo já quitado.")
        repo.money(club_id, -loan["remaining_balance"], "loan_settlement", loan["_id"])
        repo.update(
            "club_loans",
            {"_id": loan["_id"]},
            {"$set": {"remaining_balance": 0, "status": "settled", "settled_at": utcnow()}},
        )
        repo.update("club_finances", {"_id": club_id}, {"$set": cls.credit(repo, club_id)})
        return public(repo.find("club_loans", {"_id": loan["_id"]}))
