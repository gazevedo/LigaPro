"""Professional attributes and legacy adapters; junior potential is separate."""

from app.models.game import public

SKILLS = {"goalkeeping", "speed", "technique", "passing", "tackling", "playmaking", "finishing"}
FORBIDDEN = {
    "potential",
    "estimated_potential_capacity",
    "experience",
    "integration",
    "chemistry",
    "training_level",
    "acceleration",
    "vision",
    "decisions",
    "composure",
    "leadership",
    "aggression",
    "work_rate",
    "skills",
    "traits",
}
TRAITS = {
    "positioning",
    "rushing_out",
    "reflexes",
    "penalty_saving",
    "playmaking",
    "heading",
    "crossing",
    "tackling",
    "dribbling",
    "finishing",
    "marking",
    "passing",
    "stamina",
    "speed",
}


# Traditional numbers are disjoint across positions for the initial 25-player squad.
SHIRT_NUMBERS = {
    "GK": (1, 12, 23),
    "FB": (2, 3, 13, 14),
    "CB": (4, 5, 15, 16),
    "MID": (6, 8, 10, 17, 18, 20, 21, 22),
    "ATT": (7, 9, 11, 19, 24, 25),
}


def choose_shirt_number(position, used=()):
    position = {"GOL": "GK", "DEF": "CB", "MED": "MID", "ATA": "ATT"}.get(position, position)
    candidates = (*SHIRT_NUMBERS.get(position, ()), *range(26, 100), *range(1, 26))
    number = next((number for number in candidates if number not in used), None)
    if number is None:
        raise ValueError("Não há números de camisa disponíveis de 1 a 99.")
    return number


def normalize_player(player):
    position = {"GOL": "GK", "DEF": "CB", "MED": "MID", "ATA": "ATT"}.get(
        player["position"], player["position"]
    )
    strength = max(1, min(100, player.get("strength", player.get("overall", 50))))
    skills = player.get("individual_skills", player.get("skills", {}))
    status = {"active": "available", "free_agent": "available"}.get(
        player.get("status", "available"), player.get("status", "available")
    )
    return {
        "position": position,
        "strength": strength,
        "overall": strength,
        "nationality": player.get("nationality", player.get("country_id", "BR")),
        "preferred_side": player.get("preferred_side", "both"),
        "energy": player.get("energy", 100),
        "morale": player.get("morale", 50),
        "stars": max(0, min(5, player.get("stars", 0))),
        "individual_skills": {key: max(0, min(100, skills.get(key, strength))) for key in SKILLS},
        "innate_characteristics": [
            trait
            for trait in player.get("innate_characteristics", player.get("traits", []))
            if trait in TRAITS
        ],
        "status": status,
        "physical_condition": player.get("physical_condition", 100),
        "retired": status == "retired",
        "player_transfer_status": player.get(
            "player_transfer_status", "not_for_sale" if player.get("owner_club_id") else "available"
        ),
    }


def player_public(player, youth=False):
    return public(
        {
            **{
                key: value
                for key, value in player.items()
                if key not in FORBIDDEN
                and key not in {"shirt_number_revision", "shirt_number_custom"}
            },
            **normalize_player(player),
            **(
                {
                    "estimated_potential_capacity": player.get(
                        "estimated_potential_capacity",
                        player.get("potential", player.get("strength", 50)),
                    )
                }
                if youth
                else {}
            ),
            "is_free_agent": player.get("owner_club_id") is None,
            "transfer_fee": 0
            if player.get("owner_club_id") is None
            else player.get("market_value", player.get("value", 0)),
            "can_train": player.get("status")
            not in {"retired", "injured", "suspended", "candidate", "discarded"}
            and any(
                value < 100 for value in normalize_player(player)["individual_skills"].values()
            ),
        }
    )


def market_value(strength, potential, age):
    from app.services.market_value import MarketValueService

    return MarketValueService().calculate({"strength": strength, "age": age, "position": "CB"})
