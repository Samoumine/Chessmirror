import time

import httpx

BASE_URL = "https://api.chess.com/pub"
USER_AGENT = "ChessMirror/0.1 (github.com/Samoumine/chessmirror)"
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4


class ChessComClient:
    """Talks to Chess.com's public API. Never sends two requests at once."""

    def __init__(self, http: httpx.Client | None = None, sleep=time.sleep) -> None:
        self.http = http or httpx.Client(
            base_url=BASE_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
        self.sleep = sleep  # how to wait; tests swap in a fake that doesn't really wait

    def _get(self, url: str) -> httpx.Response:
        """GET with retries on temporary errors. Safe because GET changes nothing."""
        for attempt in range(MAX_ATTEMPTS):  # attempt = 0, 1, 2, 3
            response = self.http.get(url)
            is_last_try = attempt == MAX_ATTEMPTS - 1
            if response.status_code in RETRY_STATUSES and not is_last_try:  # [2]
                self.sleep(2**attempt)
                continue
            response.raise_for_status()  # 200 passes; 404 (or a 429 on the last try) becomes an error
            return response

    def get_archives(self, username: str) -> list[str]:
        """URLs of every month the player has games in, oldest first."""
        response = self._get(f"/player/{username.lower()}/games/archives")
        return response.json()["archives"]

    def get_month(self, archive_url: str) -> list[dict]:
        """All games in one month."""
        response = self._get(archive_url)
        return response.json()["games"]

    def get_all_games(self, username: str) -> list[dict]:
        """Every game, month by month, one request at a time."""
        games: list[dict] = []
        for url in self.get_archives(username):
            games.extend(self.get_month(url))
        return games
