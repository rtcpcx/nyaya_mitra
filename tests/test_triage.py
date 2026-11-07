from src.triage import triage_text


def test_immediate_danger_is_urgent():
    result = triage_text("Someone threatened to kill me and is outside my home")
    assert result["level"] == "urgent"
    assert result["lawyer_recommended"] is True


def test_court_notice_is_prompt():
    result = triage_text("I received a court notice and hearing date")
    assert result["level"] == "prompt"
    assert result["lawyer_recommended"] is True


def test_no_keyword_is_not_claimed_safe():
    result = triage_text("My neighbour is arguing about a boundary wall")
    assert result["level"] == "routine"
    assert "can miss risk" in result["reasons"][0]
