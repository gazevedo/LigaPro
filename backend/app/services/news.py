"""News are projections of committed domain events, never independent random state."""

from app.models.game import public, utcnow

NEWS_TYPES = {
    "transfer",
    "injury",
    "suspension",
    "title",
    "promotion",
    "relegation",
    "top_scorer",
    "record",
    "financial",
    "sponsor",
    "stadium",
    "youth",
    "retirement",
}


class NewsService:
    @staticmethod
    def publish(
        repo,
        kind,
        title,
        club_id=None,
        reference=None,
        *,
        player_id=None,
        competition_id=None,
        body=None,
        now=None,
    ):
        if kind not in NEWS_TYPES:
            return
        if kind == "transfer" and player_id is None and reference is not None:
            offer = repo.find("transfer_offers", {"_id": reference})
            listing = (
                repo.find("transfer_listings", {"_id": offer["listing_id"]}) if offer else None
            )
            if listing:
                player_id = listing["player_id"]
        if kind == "financial":
            title = {
                "salary": "Pagamento de salários",
                "player_salary": "Pagamento de salários",
                "sponsorship": "Receita de patrocínio",
                "tv_rights": "Receita de direitos de TV",
                "ticketing": "Receita de bilheteria",
                "prize": "Premiação recebida",
                "player_purchase": "Compra de jogador",
                "player_sale": "Venda de jogador",
                "bank_loan": "Crédito contratado",
                "loan_installment": "Parcela de empréstimo paga",
                "loan_settlement": "Empréstimo quitado",
                "other_income": "Receita registrada",
                "other_expense": "Despesa registrada",
                "stadium": "Investimento no estádio",
            }.get(title, title)
        now = now or utcnow()
        source = reference if reference is not None else now.isoformat(timespec="milliseconds")
        identity = f"{kind}:{club_id}:{source}:{title}"
        repo.database.news_items.update_one(
            {"_id": identity},
            {
                "$setOnInsert": {
                    "type": kind,
                    "title": title,
                    "body": body or title,
                    "club_id": club_id,
                    "player_id": player_id,
                    "competition_id": competition_id,
                    "reference_id": reference,
                    "created_at": now,
                }
            },
            upsert=True,
            session=repo.session,
        )

    @staticmethod
    def feed(repo, club_id=None):
        query = {"club_id": {"$in": [club_id, None]}} if club_id else {}
        return public(repo.many("news_items", query, sort=[("created_at", -1)], limit=30))
