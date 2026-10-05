"""Controlled player DTO: potential stays internal, including nested results."""

from app.models.game import public


def player_public(player):
    strength = player.get("strength", player.get("overall", 50))
    return public(
        {
            **{key: value for key, value in player.items() if key != "potential"},
            "can_train": strength < player.get("potential", 100)
            and player.get("status") != "retired",
            "potential_hint": "Em avaliação",
        }
    )


def market_value(strength, potential, age):
    age_factor = max(0.75, min(1.35, 1 + (30 - age) * 0.02))
    return max(
        1000, round(100_000 * strength / 50 * (1 + max(0, potential - strength) / 100) * age_factor)
    )
