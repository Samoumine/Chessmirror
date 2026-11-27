from datetime import UTC, datetime

from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from chessmirror.db.models import Game, Player
from chessmirror.sources.chesscom import ChessComClient

CHUNK_SIZE = (
    1000  # rows per INSERT; ~13 values per row stays far below Postgres's ~65k cap
)


def to_row(game: dict) -> dict | None:
    """Turn one Chess.com game into a `games` row, or None for variants.
    Pure function: no network, no database."""
    if game["rules"] != "chess":  # only standard chess can be analysed
        return None
    white, black = game["white"], game["black"]
    return {
        "url": game["url"],
        "white_username": white["username"].lower(),
        "black_username": black["username"].lower(),
        "white_rating": white["rating"],
        "black_rating": black["rating"],
        "white_result": white["result"],
        "black_result": black["result"],
        "time_class": game["time_class"],
        "time_control": game["time_control"],
        "rated": game["rated"],
        "eco_url": game.get("eco"),  # missing on some games → None
        "ended_at": datetime.fromtimestamp(game["end_time"], tz=UTC),
        "pgn": game["pgn"],
    }


def save_games(session: Session, rows: list[dict]) -> int:
    """Insert rows in chunks, skipping URLs already saved. Returns how many were new."""
    new = 0
    for start in range(0, len(rows), CHUNK_SIZE):  # 0 rows → loop never runs
        chunk = rows[start : start + CHUNK_SIZE]
        statement = (
            insert(Game)
            .values(chunk)  # many rows, one statement
            .on_conflict_do_nothing(index_elements=["url"])  # duplicate URL → skip it
            .returning(Game.id)  # hand back the ID of each row actually inserted
        )
        new += len(session.execute(statement).all())
    return new


def ingest_player(session: Session, client: ChessComClient, username: str) -> dict:
    """Make sure all of a player's standard games are saved. Safe to run any number of times.
    The caller owns the transaction: commit on success, rollback on error."""
    username = username.lower()

    # 1. the player row exists (created, or already there)
    session.execute(
        insert(Player)
        .values(username=username)
        .on_conflict_do_nothing(index_elements=["username"])
    )

    # 2. fetch → 3. transform (dropping variants)
    games = client.get_all_games(username)
    rows = []
    for game in games:
        row = to_row(game)
        if row is not None:
            rows.append(row)

    # 4. save
    new = save_games(session, rows)

    # 5. remember when we last fetched this player
    session.execute(
        update(Player)
        .where(Player.username == username)
        .values(last_fetched_at=func.now())
    )

    return {
        "fetched": len(games),
        "new": new,
        "already_saved": len(rows) - new,
        "skipped_variants": len(games) - len(rows),
    }
