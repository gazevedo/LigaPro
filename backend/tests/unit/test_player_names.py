from random import Random

from app.config.names import player_name, player_name_library


def test_brazilian_names_have_two_or_three_library_components():
    library = player_name_library("BR")
    rng = Random(42)
    names = [player_name(rng, "BR") for _ in range(300)]
    assert {len(name.split()) for name in names} == {2, 3}
    assert len(set(names)) > 250
    for name in names:
        parts = name.split()
        assert parts[0] in library["first_names"]
        assert parts[-1] in library["third_names"]
        if len(parts) == 3:
            assert parts[1] in library["second_names"] and parts[0] != parts[1]


def test_names_are_seeded_and_fall_back_to_brazil():
    first, second = Random(17), Random(17)
    assert [player_name(first, "BR") for _ in range(50)] == [
        player_name(second, "BR") for _ in range(50)
    ]
    assert player_name_library("XX") == player_name_library("BR")
    assert player_name_library("../../secrets") == player_name_library("BR")
    assert player_name_library("br") == player_name_library("BR")
