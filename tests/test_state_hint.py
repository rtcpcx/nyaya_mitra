from src.service import _state_hint


def test_state_hint_recognises_state_from_city_string():
    assert _state_hint("Guwahati, Assam") == "assam"
    assert _state_hint("Pune, Maharashtra") == "maharashtra"


def test_state_hint_does_not_guess_from_unknown_city():
    assert _state_hint("Somewhere in India") is None
