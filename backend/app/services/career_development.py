"""Seasonal career changes share the same bounded rules with calibration."""

from app.models.player import normalize_player


class CareerDevelopmentService:
    @staticmethod
    def evolve(player, rng, minutes=0, training=0, injured_days=0, ceiling=100):
        age = player["age"] + 1
        strength = player.get("strength", player.get("overall", 50))
        base = 0.75 if age <= 20 else 0.5 if age <= 25 else 0.15 if age <= 29 else 0.02
        readiness = min(1, training / 50)
        use = min(0.08, minutes / 35000)
        morale = (player.get("morale", 50) - 50) / 1000
        traits = 0.02 if player.get("innate_characteristics") else 0
        injury = min(0.5, injured_days / 100)
        # Training/usage gate progression; higher strength slows growth.
        chance = max(
            0, base * readiness * (1 - max(0, strength - 65) / 45) + use + morale + traits - injury
        )
        delta = 1 if age < 35 and strength < ceiling and rng.random() < chance else 0
        decline = max(0, min(0.85, 0.04 + (age - 30) * 0.04)) if age >= 30 else 0
        if rng.random() < decline:
            delta = -1
        skills = normalize_player(player)["individual_skills"]
        if delta:
            skills = {key: max(0, min(ceiling, value + delta)) for key, value in skills.items()}
        updated = max(1, min(ceiling, strength + delta))
        retirement = 0 if age < 35 else min(0.85, 0.01 * 1.5 ** (age - 35))
        retirement *= (
            1
            + 0.3 * (delta < 0)
            + max(0, 60 - player.get("physical_condition", 100)) / 100
            + 0.25 * (player.get("contract_status") == "expired")
        )
        retired = age >= 35 and rng.random() < min(0.95, retirement)
        return {
            "age": age,
            "strength": updated,
            "overall": updated,
            "individual_skills": skills,
            "retired": retired,
        }, (
            "retirement"
            if retired
            else "regression"
            if delta < 0
            else "development"
            if delta > 0
            else "stability"
        )
