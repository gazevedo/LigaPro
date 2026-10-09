"""Reusable name combinations for generated clubs and players."""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=None)
def player_name_library(country_id):
    code = str(country_id).upper()
    directory = Path(__file__).with_name("player_names")
    path = (
        directory / f"{code}.json"
        if len(code) == 2 and code.isascii() and code.isalpha()
        else directory / "BR.json"
    )
    if not path.is_file():
        path = directory / "BR.json"
    return json.loads(path.read_text(encoding="utf-8"))


def player_name(rng, country_id):
    library = player_name_library(country_id)
    first = rng.choice(library["first_names"])
    parts = [first]
    if rng.choice((False, True)):
        parts.append(rng.choice([name for name in library["second_names"] if name != first]))
    parts.append(rng.choice(library["third_names"]))
    return " ".join(parts)


CLUB_PREFIXES = (
    "Atlético",
    "Esportivo",
    "União",
    "Real",
    "Nacional",
    "Estrela",
    "Grêmio",
    "Juventude",
    "Ferroviário",
    "Racing",
    "Cruzeiro",
    "Sporting",
    "Independente",
    "Olimpique",
    "Vitória",
    "Imperial",
    "Guarani",
    "Fortaleza",
    "Operário",
    "Aurora",
)
CLUB_SUFFIXES = (
    "do Vale",
    "da Serra",
    "do Norte",
    "do Sul",
    "de Santa Luzia",
    "de Monte Alto",
    "de Vila Nova",
    "do Litoral",
    "de Porto Azul",
    "de Bela Vista",
    "de Rio Claro",
    "de Campo Verde",
    "de Nova Esperança",
    "de Santa Cruz",
    "de São Miguel",
    "de Horizonte",
    "de Ponta Nova",
    "da Capital",
    "de Boa Vista",
    "de Lagoa Dourada",
)


def club_name(rng):
    return f"{rng.choice(CLUB_PREFIXES)} {rng.choice(CLUB_SUFFIXES)}"
