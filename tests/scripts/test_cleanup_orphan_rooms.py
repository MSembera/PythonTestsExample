from scripts.cleanup_orphan_rooms import is_orphan_room_name


def test_seeded_room_names_are_not_orphans() -> None:
    assert is_orphan_room_name("101") is False
    assert is_orphan_room_name("102") is False
    assert is_orphan_room_name("103") is False


def test_our_room_name_range_is_an_orphan() -> None:
    assert is_orphan_room_name("500") is True
    assert is_orphan_room_name("99999") is True
    assert is_orphan_room_name("42317") is True


def test_outside_our_range_is_not_an_orphan() -> None:
    assert is_orphan_room_name("499") is False
    assert is_orphan_room_name("100000") is False


def test_non_numeric_name_is_not_an_orphan() -> None:
    assert is_orphan_room_name("Suite 12") is False
    assert is_orphan_room_name("") is False
