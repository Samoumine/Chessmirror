import httpx
import pytest

from chessmirror.sources.chesscom import BASE_URL, ChessComClient

OCT = "https://api.chess.com/pub/player/testplayer/games/2026/10"
NOV = "https://api.chess.com/pub/player/testplayer/games/2026/11"


def fake_chesscom(request: httpx.Request) -> httpx.Response:
    """Pretends to be Chess.com: looks at the URL and returns a canned answer."""
    if request.url.path == "/pub/player/testplayer/games/archives":
        return httpx.Response(200, json={"archives": [OCT, NOV]})
    if str(request.url) == OCT:
        return httpx.Response(200, json={"games": [{"url": "g1"}, {"url": "g2"}]})
    if str(request.url) == NOV:
        return httpx.Response(200, json={"games": [{"url": "g3"}]})
    return httpx.Response(404)  # [5] the status code for "not found"


def make_client() -> ChessComClient:
    # the real client class, but its "internet" is our fake function
    fake_http = httpx.Client(
        base_url=BASE_URL, transport=httpx.MockTransport(fake_chesscom)
    )
    return ChessComClient(http=fake_http)


def test_username_is_lowercased():
    archives = make_client().get_archives("TestPlayer")  # capitals on purpose
    assert archives == [OCT, NOV]


def test_all_games_combines_every_month():
    games = make_client().get_all_games("testplayer")
    assert len(games) == 3  # [6] count the fake games above


def test_unknown_player_raises():
    with pytest.raises(
        httpx.HTTPStatusError
    ):  # the error that raise_for_status() throws
        make_client().get_archives("nobody")
