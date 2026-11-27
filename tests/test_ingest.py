from datetime import UTC, datetime

from chessmirror.ingest import to_row


def sample_game(**overrides) -> dict:
    """A realistic Chess.com game. Pass keys to change, e.g. sample_game(rules="chess960")."""
    game = {
        "url": "https://www.chess.com/game/live/1",
        "rules": "chess",
        "white": {"username": "Saoum", "rating": 1200, "result": "win"},
        "black": {"username": "Opponent", "rating": 1350, "result": "resigned"},
        "time_class": "blitz",
        "time_control": "180+2",
        "rated": True,
        "eco": "https://www.chess.com/openings/Sicilian-Defense",
        "end_time": 0,
        "pgn": "1. e4 c5 *",
    }
    game.update(overrides)  # replace the defaults with whatever was passed in
    return game


def test_flattens_and_lowercases():
    row = to_row(sample_game())
    assert row["white_username"] == "saoum"
    assert row["black_rating"] == 1350


def test_end_time_becomes_utc_datetime():
    row = to_row(sample_game(end_time=0))
    assert row["ended_at"] == datetime(1970, 1, 1, tzinfo=UTC)


def test_missing_eco_becomes_none():
    game = sample_game()
    del game["eco"]  # delete the key, like a real game with no opening link
    assert to_row(game)["eco_url"] is None


def test_variants_are_skipped():
    assert to_row(sample_game(rules="chess960")) is None
