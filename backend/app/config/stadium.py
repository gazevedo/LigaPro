"""Stadium progression in game currency; capacities follow common venue scales."""

STADIUM_LEVELS = (
    (1, "Estádio local", 10000, 0, "Arquibancadas inferiores e serviços essenciais."),
    (2, "Estádio municipal", 20000, 20_000_000, "Academia, salas de treinamento e salas VIP."),
    (3, "Estádio regional", 30000, 40_000_000, "Arquibancadas superiores, spa e museu."),
    (4, "Arena nacional", 45000, 80_000_000, "Skyboxes e operação de grandes eventos."),
    (5, "Grande arena", 60000, 150_000_000, "Expansão de hospitalidade e serviços integrados."),
    (6, "Arena internacional", 80000, 250_000_000, "Estrutura completa para grandes públicos."),
)

# key: name, minimum arena level, cost multiplier, sprite tile, benefit
FACILITY_DEFINITIONS = {
    "stands": ("Arquibancadas inferiores", 1, 1, 0, "+1.000 lugares por melhoria."),
    "upper_stands": ("Arquibancadas superiores", 3, 8, 1, "+1.000 lugares na expansão superior."),
    "pitch": ("Campo principal", 1, 1, 14, "Melhora a experiência do público."),
    "lights": ("Iluminação", 1, 1, 15, "Melhora a experiência do público em jogos noturnos."),
    "lockers": ("Vestiários", 1, 1, 3, "Melhora a recuperação diária de moral."),
    "medical": ("Departamento médico", 1, 1, 4, "+2 pontos de recuperação física/dia por nível."),
    "training": ("Centro de treinamento", 1, 1, 2, "Até +2 pontos de progresso por sessão."),
    "training_rooms": ("Salas de treinamento", 2, 4, 3, "Até +2 pontos de progresso por sessão."),
    "training_pitch": (
        "Campo de treinamento",
        1,
        3,
        14,
        "+1 ponto de progresso a partir do nível 3.",
    ),
    "gym": ("Academia", 2, 4, 5, "+0,5 ponto de recuperação de energia/dia por nível."),
    "spa": ("Spa", 3, 5, 6, "Melhora recuperação física, energia e moral."),
    "parking": ("Estacionamento", 1, 1, 7, "Melhora acesso e gera receita em dias de jogo."),
    "shops": ("Lanchonetes", 1, 1, 8, "Gera receita adicional por torcedor presente."),
    "boxes": ("Camarotes", 1, 1, 9, "Amplia a oferta de lugares premium."),
    "vip_lounges": ("Salas VIP", 2, 6, 9, "Amplia lugares premium com preço próprio."),
    "skyboxes": ("Skyboxes", 4, 12, 10, "Cria lugares exclusivos com preço próprio."),
    "infrastructure": ("Infraestrutura", 1, 3, 11, "Melhora conforto e demanda do público."),
    "museum": ("Museu", 3, 3, 12, "Aumenta atratividade e receita de visitas."),
    "trophy_room": ("Sala de troféus", 1, 2, 13, "Aumenta a atratividade do clube."),
}
FACILITY_NAMES = {key: value[0] for key, value in FACILITY_DEFINITIONS.items()}
LEGACY_FACILITIES = {
    "stands",
    "pitch",
    "lights",
    "lockers",
    "medical",
    "training",
    "parking",
    "shops",
    "boxes",
}
DEFAULT_FACILITIES = {key: 1 if key in LEGACY_FACILITIES else 0 for key in FACILITY_DEFINITIONS}
FACILITY_LEVEL_NAMES = (
    "Não construído",
    "Essencial",
    "Estruturado",
    "Profissional",
    "Avançado",
    "Referência",
)
SECTOR_NAMES = {
    "lower_north": "Inferior Norte",
    "lower_east": "Inferior Leste",
    "lower_south": "Inferior Sul",
    "lower_west": "Inferior Oeste",
    "upper_north": "Superior Norte",
    "upper_east": "Superior Leste",
    "upper_south": "Superior Sul",
    "upper_west": "Superior Oeste",
    "vip": "Premium e camarotes",
    "skybox": "Skyboxes",
}


def facilities(stadium):
    return {**DEFAULT_FACILITIES, **stadium.get("facilities", {})}


def arena_level(stadium):
    return max(
        level
        for level, _, capacity, _, _ in STADIUM_LEVELS
        if capacity <= max(10000, stadium["capacity"])
    )


def effects(stadium):
    f = facilities(stadium)

    def bounded(key):
        return min(5, max(0, f.get(key, 0)))

    comfort = min(
        0.12,
        sum(
            max(0, bounded(key) - 1) * factor
            for key, factor in (
                ("infrastructure", 0.015),
                ("parking", 0.005),
                ("lights", 0.005),
                ("pitch", 0.005),
            )
        ),
    )
    return {
        "training_extra": min(2, (bounded("training_rooms") + 2) // 3)
        + bounded("training_pitch") // 3,
        "recovery_bonus": bounded("spa") * 0.5,
        "energy_bonus": (bounded("gym") + bounded("spa")) * 0.5,
        "morale_recovery_per_day": (max(0, bounded("lockers") - 1) + bounded("spa")) * 0.25,
        "attendance_bonus": comfort + (bounded("museum") + bounded("trophy_room")) * 0.005,
        "services_income_per_attendee": max(0, bounded("shops") - 1) * 100
        + max(0, bounded("parking") - 1) * 25
        + bounded("museum") * 50,
    }


def sectors(stadium):
    total = stadium["capacity"]
    f = facilities(stadium)
    level = arena_level(stadium)
    upper = min(round(total * 0.7), max(0, total - 20000)) if level >= 3 else 0
    vip = min(total // 10, f.get("boxes", 1) * 100 + f.get("vip_lounges", 0) * 200)
    skybox = min(total // 50, f.get("skyboxes", 0) * 40)
    lower = max(0, total - upper - vip - skybox)
    capacities = {"vip": vip, "skybox": skybox}
    for floor, count in (("lower", lower), ("upper", upper)):
        capacities[f"{floor}_north"] = count * 20 // 100
        capacities[f"{floor}_east"] = count * 30 // 100
        capacities[f"{floor}_south"] = count * 20 // 100
        capacities[f"{floor}_west"] = count - sum(
            capacities[f"{floor}_{side}"] for side in ("north", "east", "south")
        )
    prices = stadium.get("sector_prices", {})
    return [
        {
            "id": key,
            "name": name,
            "capacity": capacities[key],
            "price": prices.get(key, stadium.get("ticket_price", 2000)),
            "available": capacities[key] > 0,
        }
        for key, name in SECTOR_NAMES.items()
    ]
