"""Resolve individual duels, marking-related discipline and penalty kicks."""


class DuelResolver:
    @staticmethod
    def resolve(attacker, defender, attacking_strength, defending_strength, rng):
        probability = attacking_strength / max(1, attacking_strength + defending_strength)
        return {
            "attacker_id": attacker.id,
            "defender_id": defender.id,
            "winner_id": attacker.id if rng.random() < probability else defender.id,
        }


class FoulResolver:
    def __init__(self, config):
        self.config = config

    def resolve(self, duel, attacker, marking, rng):
        lost_duel = duel["winner_id"] == attacker.id
        probability = (
            self.config.foul_probability[marking]
            * self.config.foul_marking_modifiers[marking]
            * (1.15 if lost_duel else 0.85)
        )
        if rng.random() >= min(1, probability):
            return None
        severity = 1 - rng.random()
        if severity > 1 - self.config.direct_red_probability[marking]:
            card = "direct_red"
        elif severity > 1 - self.config.yellow_probability[marking]:
            card = "yellow"
        else:
            card = None
        area = {"ATT": 2, "MID": 1}.get(attacker.assigned_position, 0)
        return {
            "severity": severity,
            "card": card,
            "penalty_area": rng.random() < self.config.penalty_area_probability[area],
        }


class PenaltyService:
    def __init__(self, calculator, goalkeeper, finishing):
        self.calculator = calculator
        self.goalkeeper = goalkeeper
        self.finishing = finishing

    def resolve(self, shooter, keeper, rng):
        return self.finishing.resolve(
            self.calculator.calculate(shooter, "finishing"),
            self.goalkeeper.strength(keeper),
            1.0,
            rng,
        )
