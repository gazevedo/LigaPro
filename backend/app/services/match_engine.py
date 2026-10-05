"""Individual, seeded match simulation with reproducible Monte Carlo calibration.

Snapshots are JSON-compatible and returned with the result for the match scheduler
to persist. This module performs no database reads or writes.
"""

from copy import copy, deepcopy
from dataclasses import asdict, dataclass, field
from math import isfinite
from random import Random

from app.services.discipline import DuelResolver, FoulResolver, PenaltyService

MAX_SUBSTITUTIONS = 5
FORMATIONS = {"4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2", "4-5-1", "3-4-3"}
BOT_PRESETS = {
    "balanced": ("balanced", "light", "normal"),
    "aggressive": ("all_out_attack", "heavy", "center"),
    "counter": ("counter_attack", "light", "wings"),
    "defensive_heavy_marking": ("balanced", "very_heavy", "normal"),
}

POSITIONS = {"GK", "FB", "CB", "MID", "ATT"}
ALIASES = {"GOL": "GK", "DEF": "CB", "MED": "MID", "ATA": "ATT"}
SKILLS = {"goalkeeping", "speed", "technique", "passing", "tackling", "playmaking", "finishing"}


def clamp(value, low, high):
    return max(low, min(high, value))


@dataclass(frozen=True)
class MatchConfig:
    block_minutes: int = 5
    compatible_fit: float = 0.90
    unsuitable_fit: float = 0.72
    wrong_side_fit: float = 0.96
    home_advantage: float = 1.04
    focus_probability: float = 0.70
    energy_loss: float = 1.5
    marking_containment: tuple = (1.0, 1.08, 1.20)
    marking_build_up: tuple = (1.0, 0.98, 0.90)
    foul_probability: tuple = (0.03, 0.07, 0.12)
    foul_marking_modifiers: tuple = (0.75, 1.0, 1.35)
    yellow_probability: tuple = (0.20, 0.32, 0.44)
    direct_red_probability: tuple = (0.025, 0.05, 0.075)
    penalty_area_probability: tuple = (0.02, 0.08, 0.16)
    phase_bases: tuple = (0.80, 0.75, 0.65)
    phase_sensitivity: float = 0.30
    goal_base: float = 0.36
    on_target_base: float = 0.45
    marking_attack_reduction: tuple = (0.0, 0.07, 0.20)
    marking_attempt_cost: tuple = (0.0, 0.04, 0.12)
    attacking_creation_bonus: float = 0.05
    attacking_exposure: float = 0.85
    counter_initiative: float = 0.86
    counter_progression_bonus: float = 0.10
    counter_creation_bonus: float = 0.06

    def __post_init__(self):
        if not isinstance(self.block_minutes, int) or not 1 <= self.block_minutes <= 90:
            raise ValueError("block_minutes must be between 1 and 90")
        if not 0 < self.unsuitable_fit <= self.compatible_fit <= self.wrong_side_fit <= 1:
            raise ValueError("Invalid position/side calibration")
        if not 1 <= self.home_advantage <= 1.05:
            raise ValueError("Home advantage must remain small")
        if not 0 <= self.focus_probability <= 1 or not 0 <= self.energy_loss <= 100:
            raise ValueError("Invalid focus/energy calibration")
        for values in (
            self.marking_containment,
            self.marking_build_up,
            self.foul_probability,
            self.foul_marking_modifiers,
            self.yellow_probability,
            self.direct_red_probability,
            self.penalty_area_probability,
            self.phase_bases,
            self.marking_attack_reduction,
            self.marking_attempt_cost,
        ):
            if len(values) != 3 or any(not isfinite(x) for x in values):
                raise ValueError("Marking requires three finite values")
        probabilities = (
            *self.phase_bases,
            self.goal_base,
            self.on_target_base,
            self.phase_sensitivity,
            *self.marking_attack_reduction,
            *self.marking_attempt_cost,
            self.attacking_creation_bonus,
            self.attacking_exposure,
            self.counter_initiative,
            self.counter_progression_bonus,
            self.counter_creation_bonus,
        )
        if any(not isfinite(x) or not 0 <= x <= 1 for x in probabilities):
            raise ValueError("Invalid phase/style probability")
        if any(x <= 0 for x in self.marking_containment):
            raise ValueError("Containment must be positive")
        if any(not 0 < x <= 1 for x in self.marking_build_up):
            raise ValueError("Build-up factors must be in (0, 1]")
        if any(x <= 0 for x in self.foul_marking_modifiers):
            raise ValueError("Foul modifiers must be positive")
        for probabilities in (
            self.yellow_probability,
            self.direct_red_probability,
            self.penalty_area_probability,
        ):
            if any(not 0 <= x <= 1 for x in probabilities):
                raise ValueError("Invalid disciplinary probability")
        if any(
            red > yellow
            for red, yellow in zip(self.direct_red_probability, self.yellow_probability)
        ):
            raise ValueError("Direct red threshold must not exceed yellow threshold")
        if any(not 0 <= x <= 1 for x in self.foul_probability):
            raise ValueError("Foul probabilities must be in [0, 1]")


@dataclass
class MatchPlayer:
    id: str
    position: str
    assigned_position: str
    strength: float = 50
    energy: float = 100
    morale: float = 50
    preferred_side: str = "both"
    side: str = "center"
    skills: dict = field(default_factory=dict)
    traits: tuple = ()

    def __post_init__(self):
        self.position = ALIASES.get(self.position, self.position)
        self.assigned_position = ALIASES.get(self.assigned_position, self.assigned_position)
        if self.position not in POSITIONS or self.assigned_position not in POSITIONS:
            raise ValueError("Unknown player position")
        if self.preferred_side not in {"left", "right", "both"}:
            raise ValueError("Unknown preferred side")
        if self.side not in {"left", "right", "center"}:
            raise ValueError("Unknown lineup side")
        values = [self.strength, self.energy, self.morale, *self.skills.values()]
        if any(not isfinite(x) or not 0 <= x <= 100 for x in values):
            raise ValueError("Player attributes must be finite and between 0 and 100")
        if set(self.skills) - SKILLS:
            raise ValueError("Unknown skill")

    @classmethod
    def from_document(cls, document, assigned_position=None, side="center"):
        """Adapt existing overall/GOL/DEF/MED/ATA documents without migration."""
        return cls(
            id=str(document.get("_id", document.get("id", ""))),
            position=document["position"],
            assigned_position=assigned_position or document["position"],
            strength=document.get("strength", document.get("overall", 50)),
            energy=document.get("energy", 100),
            morale=document.get("morale", 50),
            preferred_side=document.get("preferred_side", "both"),
            side=side,
            skills=dict(document.get("skills", {})),
            traits=tuple(document.get("traits", ())),
        )


@dataclass
class MatchTeam:
    id: str
    lineup: list[MatchPlayer]
    formation: str = "4-4-2"
    style: str = "balanced"
    marking: str = "light"
    attack_focus: str = "normal"
    reserves: list[MatchPlayer] = field(default_factory=list)
    is_bot: bool = False

    def __post_init__(self):
        if self.style not in {"balanced", "all_out_attack", "counter_attack"}:
            raise ValueError("Unknown style")
        if self.marking not in {"light", "heavy", "very_heavy"}:
            raise ValueError("Unknown marking")
        if self.attack_focus not in {"normal", "center", "wings"}:
            raise ValueError("Unknown attack focus")
        try:
            sectors = [int(n) for n in self.formation.split("-")]
        except ValueError as exc:
            raise ValueError("Invalid formation") from exc
        if len(sectors) < 3 or any(n <= 0 for n in sectors) or sum(sectors) != 10:
            raise ValueError("Formation must describe ten outfield players")
        if len(self.lineup) != 11 or len({p.id for p in self.lineup}) != 11:
            raise ValueError("Lineup requires eleven distinct players")
        ids = [p.id for p in self.lineup + self.reserves]
        if len(ids) != len(set(ids)):
            raise ValueError("Starters and reserves must be distinct")
        counts = [
            sum(p.assigned_position == "GK" for p in self.lineup),
            sum(p.assigned_position in {"CB", "FB"} for p in self.lineup),
            sum(p.assigned_position == "MID" for p in self.lineup),
            sum(p.assigned_position == "ATT" for p in self.lineup),
        ]
        if counts != [1, sectors[0], sum(sectors[1:-1]), sectors[-1]]:
            raise ValueError("Lineup sectors must match formation")


def arrange_formation(players, formation):
    """Keep actual players and their current energy; assign roles and sides."""
    if formation not in FORMATIONS:
        raise ValueError("Unknown formation")
    sectors = [int(n) for n in formation.split("-")]
    defenders = [("CB", "center")] * sectors[0]
    if sectors[0] >= 4:
        defenders = [("FB", "left"), ("FB", "right")] + [("CB", "center")] * (sectors[0] - 2)
    midfield = [("MID", "center")] * sum(sectors[1:-1])
    if len(midfield) >= 4:
        midfield[:2] = [("MID", "left"), ("MID", "right")]
    slots = [("GK", "center")] + defenders + midfield + [("ATT", "center")] * sectors[-1]
    pool, assigned = list(players), []
    for role, side in slots:

        def suitability(player):
            natural = player.position == role or {player.position, role} == {"CB", "FB"}
            return (
                natural,
                player.preferred_side in {side, "both"},
                player.assigned_position == role,
            )

        player = max(pool, key=suitability)
        pool.remove(player)
        player.assigned_position, player.side = role, side
        assigned.append(player)
    return assigned


def bot_preset(team, opponent, difference):
    strength = sum(p.strength for p in team.lineup) / 11
    rival = sum(p.strength for p in opponent.lineup) / 11
    speed = sum(p.skills.get("speed", p.strength) for p in team.lineup) / 11
    if difference < 0:
        return "aggressive"
    if difference > 0 or opponent.style == "all_out_attack" or speed > strength + 5:
        return "counter"
    if strength < rival - 8:
        return "defensive_heavy_marking"
    return "balanced"


def validate_commands(commands, team_ids):
    for command in commands:
        if not isinstance(command, dict) or set(command) != {
            "team_id",
            "minute",
            "type",
            "payload",
        }:
            raise ValueError("Invalid command fields")
        if command["team_id"] not in team_ids:
            raise ValueError("Unknown command team")
        minute = command["minute"]
        if type(minute) is not int or not 0 <= minute < 90:
            raise ValueError("Command minute must be between 0 and 89")
        payload = command["payload"]
        if not isinstance(payload, dict) or not payload:
            raise ValueError("Empty command payload")
        if command["type"] == "substitution":
            if set(payload) != {"out_player_id", "in_player_id"} or any(
                not isinstance(v, str) for v in payload.values()
            ):
                raise ValueError("Invalid substitution")
        elif command["type"] == "tactics_change":
            choices = {
                "formation": FORMATIONS,
                "play_style": {"balanced", "all_out_attack", "counter_attack"},
                "marking": {"light", "heavy", "very_heavy"},
                "attack_focus": {"normal", "center", "wings"},
            }
            if any(
                k not in choices or not isinstance(v, str) or v not in choices[k]
                for k, v in payload.items()
            ):
                raise ValueError("Invalid tactical command")
        else:
            raise ValueError("Unknown command type")


class PositionFitCalculator:
    def __init__(self, config):
        self.config = config

    def calculate(self, player):
        if player.position == player.assigned_position:
            fit = 1.0
        elif {player.position, player.assigned_position} in (
            {"FB", "CB"},
            {"FB", "MID"},
            {"MID", "ATT"},
        ):
            fit = self.config.compatible_fit
        else:
            fit = self.config.unsuitable_fit
        if player.side != "center" and player.preferred_side not in {player.side, "both"}:
            fit *= self.config.wrong_side_fit
        return fit


class PlayerEffectiveStrengthCalculator:
    def __init__(self, config, mode):
        if mode not in {"classic", "skills"}:
            raise ValueError("Unknown attribute mode")
        self.mode = mode
        self.fit = PositionFitCalculator(config)

    def calculate(self, player, *skills):
        value = (
            player.strength
            if self.mode == "classic"
            else (sum(player.skills[s] for s in skills) / len(skills))
        )
        energy = clamp(0.70 + player.energy / 333, 0.70, 1.0)
        morale = 1 + (player.morale - 50) * 0.0008
        related = sum(skill in player.traits for skill in skills) if player.traits else 0
        # Traits apply only to the requested phase, never to general team strength.
        return value * energy * morale * self.fit.calculate(player) * (1 + 0.02 * related)


class SectorContributionCalculator:
    def __init__(self, calculator):
        self.calculator = calculator

    def participants(self, team, phase, lane, rng, dismissed):
        players = [p for p in team.lineup if p.id not in dismissed and p.assigned_position != "GK"]
        if not players:
            return []
        roles = {
            "build": {"CB": 2, "FB": 2, "MID": 3, "ATT": 1},
            "progress": {"CB": 1, "FB": 2, "MID": 3, "ATT": 2},
            "create": {"CB": 1, "FB": 2, "MID": 3, "ATT": 3},
            "finish": {"CB": 1, "FB": 1, "MID": 2, "ATT": 5},
            "defend": {"CB": 4, "FB": 3, "MID": 2, "ATT": 1},
        }[phase]
        weights = [
            roles[p.assigned_position]
            * (2 if p.side == lane else 1)
            * (
                1.4
                if team.style == "all_out_attack"
                and p.assigned_position in {"MID", "FB", "ATT"}
                and phase != "defend"
                else 1
            )
            * (1.5 if lane != "center" and p.assigned_position == "FB" else 1)
            * (
                1
                + sum(
                    p.skills.get(skill, p.strength) for skill in ("speed", "passing", "finishing")
                )
                / 300
                if team.style == "counter_attack" and phase in {"progress", "create", "finish"}
                else 1
            )
            for p in players
        ]
        selected = []
        for _ in range(min(3, len(players))):
            index = rng.choices(range(len(players)), weights=weights)[0]
            selected.append(players.pop(index))
            weights.pop(index)
        return selected

    @staticmethod
    def presence(team, phase, dismissed):
        weights = {
            "build": {"CB": 2, "FB": 2, "MID": 3, "ATT": 1},
            "progress": {"CB": 1, "FB": 2, "MID": 3, "ATT": 2},
            "create": {"CB": 0.5, "FB": 1, "MID": 2, "ATT": 4},
            "defend": {"CB": 4, "FB": 3, "MID": 2, "ATT": 1},
        }[phase]
        # Reference presence is a 4-4-2 with two fullbacks. Formation effects
        # come from the actual available positions, including dismissals.
        reference = 2 * weights["CB"] + 2 * weights["FB"] + 4 * weights["MID"] + 2 * weights["ATT"]
        actual = sum(
            weights[p.assigned_position]
            for p in team.lineup
            if p.id not in dismissed and p.assigned_position != "GK"
        )
        return (actual / reference) ** 0.5

    def contribution(self, players, *skills):
        return sum(self.calculator.calculate(p, *skills) for p in players) / max(1, len(players))


class BuildUpResolver:
    def __init__(self, base=None, sensitivity=0.30):
        self.base = self.base if base is None else base
        self.sensitivity = sensitivity

    skills = ("passing", "technique", "playmaking")
    base = 0.80

    def resolve(self, attack, defense, rng, bonus=0):
        probability = clamp(
            self.base + self.sensitivity * (attack - defense) / max(1, attack + defense) + bonus,
            0.08,
            0.97,
        )
        return rng.random() < probability


class ProgressionResolver(BuildUpResolver):
    skills = ("speed", "technique", "playmaking")
    base = 0.75


class ChanceCreator(BuildUpResolver):
    skills = ("playmaking", "passing")
    base = 0.65


class GoalkeeperResolver:
    def __init__(self, calculator):
        self.calculator = calculator

    def strength(self, goalkeeper):
        return self.calculator.calculate(goalkeeper, "goalkeeping") if goalkeeper else 0


class FinishingResolver:
    def __init__(self, config=None):
        self.config = config or MatchConfig()

    def resolve(self, finishing, goalkeeper, quality, rng):
        on_target = clamp(self.config.on_target_base + quality * 0.25 + finishing / 500, 0.20, 0.85)
        if rng.random() >= on_target:
            return "shot_off_target"
        goal = clamp(
            self.config.goal_base
            + quality * 0.22
            + (finishing - goalkeeper) / max(1, finishing + goalkeeper) * 0.35,
            0.03,
            0.85,
        )
        return "goal" if rng.random() < goal else "shot_saved"


class MatchEngine:
    def __init__(self, config=None, mode="classic"):
        self.config = config or MatchConfig()
        self.mode = mode
        self.calculator = PlayerEffectiveStrengthCalculator(self.config, mode)
        self.sectors = SectorContributionCalculator(self.calculator)
        self.goalkeeper = GoalkeeperResolver(self.calculator)
        self.finishing = FinishingResolver(self.config)
        self.fouls = FoulResolver(self.config)
        self.penalties = PenaltyService(self.calculator, self.goalkeeper, self.finishing)
        self.phases = [
            (phase, resolver(base, self.config.phase_sensitivity))
            for phase, resolver, base in zip(
                ("build", "progress", "create"),
                (BuildUpResolver, ProgressionResolver, ChanceCreator),
                self.config.phase_bases,
            )
        ]

    def attack_lane(self, focus, rng):
        favored = rng.random() < self.config.focus_probability
        if focus == "normal":
            return rng.choice(["center", "left", "right"])
        wings = favored if focus == "wings" else not favored
        return rng.choice(["left", "right"]) if wings else "center"

    def simulate(self, home, away, seed, *, capture_snapshot=True, commands=None):
        # Revalidate mutable inputs and isolate fatigue/cards from caller data.
        commands = deepcopy(commands or [])
        validate_commands(commands, {home.id, away.id})
        pending = sorted(commands, key=lambda command: command["minute"])
        teams = [copy(home), copy(away)]
        for team in teams:
            team.lineup = [copy(player) for player in team.lineup]
            team.reserves = [copy(player) for player in team.reserves]
        if home.id == away.id:
            raise ValueError("Teams must be distinct")
        for team in teams:
            team.__post_init__()
            for player in team.lineup + team.reserves:
                player.__post_init__()
                if self.mode == "skills" and not SKILLS <= player.skills.keys():
                    raise ValueError("Skills mode requires all seven skills")
        snapshot = (
            {
                "home": asdict(teams[0]),
                "away": asdict(teams[1]),
                "seed": seed,
                "mode": self.mode,
                "config": asdict(self.config),
                "commands": commands,
            }
            if capture_snapshot
            else None
        )
        rng = Random(seed)
        events, scores = [], [0, 0]
        dismissed, yellows = [set(), set()], [{}, {}]
        marking_names = ["light", "heavy", "very_heavy"]
        presence_cache = {}

        def sector_presence(index, phase):
            key = (index, phase, len(dismissed[index]))
            if key not in presence_cache:
                presence_cache[key] = self.sectors.presence(teams[index], phase, dismissed[index])
            return presence_cache[key]

        substitutions = [0, 0]

        def apply_command(command, minute):
            index = next(i for i, t in enumerate(teams) if t.id == command["team_id"])
            active = teams[index]
            payload = command["payload"]
            base = {"minute": minute, "team_id": active.id, "player_id": None}
            if command["type"] == "substitution":
                outgoing = next(
                    (p for p in active.lineup if p.id == payload["out_player_id"]), None
                )
                incoming = next(
                    (p for p in active.reserves if p.id == payload["in_player_id"]), None
                )
                if (
                    substitutions[index] >= MAX_SUBSTITUTIONS
                    or outgoing is None
                    or incoming is None
                    or outgoing.id in dismissed[index]
                ):
                    events.append(
                        {
                            **base,
                            "type": "command_rejected",
                            "command": command,
                            "reason": "Substituição indisponível ou limite atingido.",
                        }
                    )
                    return
                incoming.assigned_position, incoming.side = (
                    outgoing.assigned_position,
                    outgoing.side,
                )
                active.lineup[active.lineup.index(outgoing)] = incoming
                active.reserves.remove(incoming)
                substitutions[index] += 1
                events.append(
                    {**base, "type": "substitution", **payload, "energy": incoming.energy}
                )
            else:
                for field_name, value in payload.items():
                    attribute = "style" if field_name == "play_style" else field_name
                    previous = getattr(active, attribute)
                    if previous == value:
                        continue
                    if field_name == "formation":
                        active.lineup = arrange_formation(active.lineup, value)
                    setattr(active, attribute, value)
                    events.append(
                        {
                            **base,
                            "type": field_name + "_change",
                            "previous": previous,
                            "value": value,
                        }
                    )
            presence_cache.clear()

        stats = [
            {
                "possession_minutes": 0,
                "attacks": 0,
                "chances": 0,
                "shots": 0,
                "goals": 0,
                "fouls": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "lanes": {"center": 0, "left": 0, "right": 0},
                "phases": {phase: {"attempts": 0, "successes": 0} for phase, _ in self.phases},
                "transitions": 0,
                "transition_chances": 0,
            }
            for _ in teams
        ]
        for start in range(0, 90, self.config.block_minutes):
            while pending and pending[0]["minute"] <= start:
                apply_command(pending.pop(0), start)
            for index, active in enumerate(teams):
                if not active.is_bot:
                    continue
                if start in {0, 45, 65, 80}:
                    preset = bot_preset(active, teams[1 - index], scores[index] - scores[1 - index])
                    style, marking, focus = BOT_PRESETS[preset]
                    if sum(yellows[index].values()) >= 3 or dismissed[index]:
                        marking = "light"
                    apply_command(
                        {
                            "team_id": active.id,
                            "type": "tactics_change",
                            "payload": {
                                "play_style": style,
                                "marking": marking,
                                "attack_focus": focus,
                            },
                        },
                        start,
                    )
                if start in {60, 75}:
                    for _ in range(3):
                        if substitutions[index] >= MAX_SUBSTITUTIONS:
                            break
                        options = [
                            (out, reserve)
                            for out in active.lineup
                            for reserve in active.reserves
                            if out.id not in dismissed[index]
                            and out.assigned_position == reserve.position
                            and reserve.energy > out.energy + 5
                        ]
                        if not options:
                            break
                        outgoing, incoming = min(
                            options, key=lambda pair: (pair[0].energy, -pair[1].strength)
                        )
                        apply_command(
                            {
                                "team_id": active.id,
                                "type": "substitution",
                                "payload": {
                                    "out_player_id": outgoing.id,
                                    "in_player_id": incoming.id,
                                },
                            },
                            start,
                        )
            minute = min(90, start + self.config.block_minutes)
            duration = minute - start
            for index, active_team in enumerate(teams):
                for player in active_team.lineup:
                    if player.id not in dismissed[index]:
                        player.energy = max(
                            0, player.energy - self.config.energy_loss * duration / 5
                        )
            initiative = []
            for index, team in enumerate(teams):
                players = [
                    p
                    for p in team.lineup
                    if p.id not in dismissed[index] and p.assigned_position != "GK"
                ]
                presence = sum(
                    self.calculator.calculate(p, "passing", "playmaking")
                    * (1.2 if p.assigned_position == "MID" else 1)
                    for p in players
                )
                initiative.append(
                    max(1, presence)
                    * (self.config.counter_initiative if team.style == "counter_attack" else 1)
                    * (self.config.home_advantage if index == 0 else 1)
                )
            attacker = rng.choices([0, 1], weights=initiative)[0]
            defender = 1 - attacker
            team, opponent = teams[attacker], teams[defender]
            stats[attacker]["possession_minutes"] += duration
            lane = self.attack_lane(team.attack_focus, rng)
            mark = marking_names.index(opponent.marking)
            own_mark = marking_names.index(team.marking)

            def event(kind, player=None, **extra):
                event_team = defender if extra.get("team_id") == opponent.id else attacker
                if kind in {"attack", "chance", "goal", "foul", "yellow_card", "red_card"}:
                    field = {
                        "attack": "attacks",
                        "chance": "chances",
                        "goal": "goals",
                        "foul": "fouls",
                        "yellow_card": "yellow_cards",
                        "red_card": "red_cards",
                    }[kind]
                    stats[event_team][field] += 1
                if kind in {"goal", "shot_saved", "shot_off_target"}:
                    stats[event_team]["shots"] += 1
                if kind == "attack":
                    stats[attacker]["lanes"][lane] += 1
                events.append(
                    {
                        "minute": minute,
                        "type": kind,
                        "team_id": team.id,
                        "player_id": player.id if player else None,
                        **extra,
                    }
                )

            defenders = self.sectors.participants(
                opponent, "defend", lane, rng, dismissed[defender]
            )
            build_players = self.sectors.participants(team, "build", lane, rng, dismissed[attacker])
            build_strength = self.sectors.contribution(build_players, *BuildUpResolver.skills)
            pressure = self.sectors.contribution(defenders, "tackling", "speed")
            suppression = self.config.marking_attack_reduction[mark] * clamp(
                pressure / max(1, build_strength), 0.5, 1
            )
            if team.style == "counter_attack":
                suppression *= 0.35
            if rng.random() < suppression:
                event("attack_lost", phase="pressure")
                continue
            if rng.random() < self.config.marking_attempt_cost[own_mark]:
                event("attack_lost", phase="marking_cost")
                continue
            event("attack", lane=lane)
            transition_attack = (
                team.style == "counter_attack" and opponent.style == "all_out_attack"
            )
            if transition_attack:
                stats[attacker]["transitions"] += 1
            foul = None
            if defenders and build_players:
                challenger, culprit = rng.choice(build_players), rng.choice(defenders)
                duel = DuelResolver.resolve(
                    challenger,
                    culprit,
                    self.calculator.calculate(challenger, "technique", "speed"),
                    self.calculator.calculate(culprit, "tackling", "speed"),
                    rng,
                )
                event("duel", challenger, **duel)
                foul = self.fouls.resolve(duel, challenger, mark, rng)
            if foul:
                event(
                    "foul",
                    culprit,
                    team_id=opponent.id,
                    severity=foul["severity"],
                    penalty_area=foul["penalty_area"],
                    opponent_player_id=challenger.id,
                )
                if foul["card"] == "direct_red":
                    event("direct_red", culprit, team_id=opponent.id)
                    event("red_card", culprit, team_id=opponent.id, reason="direct_red")
                    dismissed[defender].add(culprit.id)
                elif foul["card"] == "yellow":
                    event("yellow_card", culprit, team_id=opponent.id)
                    yellows[defender][culprit.id] = yellows[defender].get(culprit.id, 0) + 1
                    if yellows[defender][culprit.id] == 2:
                        event("second_yellow", culprit, team_id=opponent.id)
                        event("red_card", culprit, team_id=opponent.id, reason="second_yellow")
                        dismissed[defender].add(culprit.id)
                presence_cache.clear()
                if foul["penalty_area"]:
                    event("penalty_awarded", challenger)
                    shooters = self.sectors.participants(
                        team, "finish", lane, rng, dismissed[attacker]
                    )
                    if shooters:
                        keeper = next(
                            (
                                p
                                for p in opponent.lineup
                                if p.assigned_position == "GK" and p.id not in dismissed[defender]
                            ),
                            None,
                        )
                        shot = self.penalties.resolve(shooters[0], keeper, rng)
                        event(shot, shooters[0], penalty=True)
                        scores[attacker] += shot == "goal"
                    continue
                defenders = [p for p in defenders if p.id not in dismissed[defender]]
            quality = 0.5
            for phase, resolver in self.phases:
                participants = (
                    build_players
                    if phase == "build"
                    else self.sectors.participants(team, phase, lane, rng, dismissed[attacker])
                )
                attack = self.sectors.contribution(participants, *resolver.skills)
                attack *= sector_presence(attacker, phase)
                if phase == "build":
                    attack *= self.config.marking_build_up[own_mark]
                    if attacker == 0:
                        attack *= self.config.home_advantage
                defense = self.sectors.contribution(defenders, "tackling", "speed")
                defense *= self.config.marking_containment[mark]
                defense *= sector_presence(defender, "defend")
                if opponent.style == "all_out_attack":
                    defense *= self.config.attacking_exposure
                bonus = (
                    self.config.attacking_creation_bonus
                    if team.style == "all_out_attack" and phase == "create"
                    else 0
                )
                if transition_attack:
                    bonus += {
                        "progress": self.config.counter_progression_bonus,
                        "create": self.config.counter_creation_bonus,
                    }.get(phase, 0)
                stats[attacker]["phases"][phase]["attempts"] += 1
                if not participants or not resolver.resolve(attack, defense, rng, bonus):
                    event("attack_lost", phase=phase)
                    break
                stats[attacker]["phases"][phase]["successes"] += 1
                quality = clamp(0.5 + (attack - defense) / max(1, attack + defense), 0, 1)
            else:
                shooters = self.sectors.participants(team, "finish", lane, rng, dismissed[attacker])
                shooter = shooters[0]
                event("chance", shooter, quality=quality, transition=transition_attack)
                stats[attacker]["transition_chances"] += int(transition_attack)
                keeper = next(
                    (
                        p
                        for p in opponent.lineup
                        if p.assigned_position == "GK" and p.id not in dismissed[defender]
                    ),
                    None,
                )
                shot = self.finishing.resolve(
                    self.calculator.calculate(shooter, "finishing"),
                    self.goalkeeper.strength(keeper),
                    quality,
                    rng,
                )
                event(shot, shooter)
                scores[attacker] += shot == "goal"
        for command in pending:
            events.append(
                {
                    "minute": 90,
                    "type": "command_rejected",
                    "team_id": command["team_id"],
                    "command": command,
                    "reason": "Sem bloco futuro para aplicar o comando.",
                }
            )
        result = {
            "score": {home.id: scores[0], away.id: scores[1]},
            "events": events,
            "statistics": {
                team.id: {**stat, "possession": stat["possession_minutes"] / 90}
                for team, stat in zip(teams, stats)
            },
        }
        if capture_snapshot:
            final = [asdict(t) for t in teams]
            for index, lineup in enumerate(final):
                lineup["lineup"] = [p for p in lineup["lineup"] if p["id"] not in dismissed[index]]
                lineup["dismissed_player_ids"] = sorted(dismissed[index])
            result.update(snapshot=snapshot, final_lineups=final)
        return result
