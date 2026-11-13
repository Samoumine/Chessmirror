import httpx

BASE_URL = "https://api.chess.com/pub"
USER_AGENT = "ChessMirror/0.1 (github.com/Samoumine/chessmirror)"


class ChessComClient:
    """Talks to Chess.com's public API. Never sends two requests at once."""

    def __init__(self, http: httpx.Client | None = None) -> None:
        self.http = http or httpx.Client(
            base_url=BASE_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,  # give up after 10 s instead of hanging forever
        )

    def get_archives(self, username: str) -> list[str]:
        """URLs of every month the player has games in, oldest first."""
        response = self.http.get(f"/player/{username.lower()}/games/archives")
        response.raise_for_status()
        return response.json()["archives"]

    def get_month(self, archive_url: str) -> list[dict]:
        """All games in one month."""
        response = self.http.get(archive_url)
        response.raise_for_status()
        return response.json()["games"]

    def get_all_games(self, username: str) -> list[dict]:
        """Every game, month by month, one request at a time."""
        games: list[dict] = []
        for url in self.get_archives(username):
            games.extend(self.get_month(url))
        return games
