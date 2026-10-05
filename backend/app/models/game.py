from datetime import datetime, timezone

from bson import ObjectId

FORMATIONS = {
    "4-4-2": {"DEF": 4, "MED": 4, "ATA": 2},
    "4-3-3": {"DEF": 4, "MED": 3, "ATA": 3},
    "4-2-3-1": {"DEF": 4, "MED": 5, "ATA": 1},
    "3-5-2": {"DEF": 3, "MED": 5, "ATA": 2},
    "5-3-2": {"DEF": 5, "MED": 3, "ATA": 2},
    "4-5-1": {"DEF": 4, "MED": 5, "ATA": 1},
    "3-4-3": {"DEF": 3, "MED": 4, "ATA": 3},
}
FACILITIES = {
    "stands": "Arquibancadas",
    "pitch": "Gramado",
    "lights": "Iluminação",
    "lockers": "Vestiários",
    "medical": "Centro Médico",
    "training": "Centro de Treinamento",
    "parking": "Estacionamento",
    "shops": "Lojas",
    "boxes": "Camarotes",
}
DEFAULT_RULES = {
    "formations": FORMATIONS,
    "initial_balance": 10_000_000,
    "upgrade_base_cost": 100_000,
    "initial_capacity": 10000,
    "ticket_price": 2000,
    "max_bank_loan": 5_000_000,
    "investment_days": 30,
    "investment_interest_bps": 100,
    "bank_loan_days": 30,
    "bank_loan_interest_bps": 500,
    "sponsor_days": 90,
    "sponsor_value": 500_000,
}


def utcnow():
    return datetime.now(timezone.utc)


def public(document):
    if isinstance(document, ObjectId):
        return str(document)
    if isinstance(document, datetime):
        return document.isoformat().replace("+00:00", "Z")
    if isinstance(document, list):
        return [public(item) for item in document]
    if isinstance(document, dict):
        return {"id" if key == "_id" else key: public(value) for key, value in document.items()}
    return document
