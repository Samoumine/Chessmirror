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
        self.sleep = sleep
        # url → (etag, data). In memory for now; Step 3 moves it to Postgres.
        self.cache: dict[str, tuple[str, dict]] = {}

    def _get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        """GET with retries on temporary errors. A 304 is handed back, not raised."""
        for attempt in range(MAX_ATTEMPTS):
            response = self.http.get(url, headers=headers)  # added on top of User-Agent
            is_last_try = attempt == MAX_ATTEMPTS - 1
            if response.status_code == 304:  # "not modified" is not an error
                return response
            if response.status_code in RETRY_STATUSES and not is_last_try:
                self.sleep(2**attempt)
                continue
            response.raise_for_status()
            return response

    def _get_json(self, url: str) -> dict:
        """GET a URL as JSON, reusing our stored copy if Chess.com says nothing changed."""
        cached = self.cache.get(url)  # (etag, data) if we've seen this URL, else None
        headers: dict[str, str] = {}
        if cached is not None:
            headers["If-None-Match"] = cached[
                0
            ]  # "only send data if it isn't this version"
        response = self._get(url, headers=headers)

        if response.status_code == 304:
            # cached can't be None here: we only get a 304 after sending a label,
            # and we only send a label when we have a stored copy.
            return cached[1]

        data = response.json()
        new_etag = response.headers.get("ETag")
        if (
            new_etag is not None
        ):  # no label → nothing to compare next time → don't cache
            self.cache[url] = (new_etag, data)
        return data

    def get_archives(self, username: str) -> list[str]:
        """URLs of every month the player has games in, oldest first."""
        return self._get_json(f"/player/{username.lower()}/games/archives")["archives"]

    def get_month(self, archive_url: str) -> list[dict]:
        """All games in one month."""
        return self._get_json(archive_url)["games"]

    def get_all_games(self, username: str) -> list[dict]:
        """Every game, month by month, one request at a time."""
        games: list[dict] = []
        for url in self.get_archives(username):
            games.extend(self.get_month(url))
        return games
