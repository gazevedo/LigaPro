"""Minimum forced changes; never invent a strategy for an absent human."""


class AutoMatchFallbackService:
    @staticmethod
    def replacement(team, injured):
        matching = [
            p
            for p in team.reserves
            if p.position == injured.position
            or {p.position, injured.assigned_position} <= {"FB", "CB"}
        ]
        if not matching and injured.assigned_position != "GK":
            matching = [p for p in team.reserves if p.position != "GK"]
        return max(matching, key=lambda p: p.strength * p.energy, default=None)

    @staticmethod
    def restore_keeper(team, dismissed):
        available = [p for p in team.lineup if p.id not in dismissed]
        if not available or any(p.assigned_position == "GK" for p in available):
            return None
        # With ten players, improvise the strongest available keeper. No tactic changes.
        keeper = max(
            available, key=lambda p: (p.position == "GK", p.skills.get("goalkeeping", p.strength))
        )
        displaced = next((p for p in team.lineup if p.assigned_position == "GK"), None)
        old_role = keeper.assigned_position
        keeper.assigned_position = "GK"
        if displaced:
            displaced.assigned_position = old_role
        return keeper
