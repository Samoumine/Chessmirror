import httpx
import pytest

from chessmirror.sources.chesscom import BASE_URL, ChessComClient

OCT = "https://api.chess.com/pub/player/testplayer/games/2026/10"
NOV = "https://api.chess.com/pub/player/testplayer/games/2026/11"
MONTH = "https://api.chess.com/pub/player/testplayer/games/2026/11"


# ---------- 2.4: basic fetching ----------


def fake_chesscom(request: httpx.Request) -> httpx.Response:
    """Pretends to be Chess.com: looks at the URL and returns a canned answer."""
    if request.url.path == "/pub/player/testplayer/games/archives":
        return httpx.Response(200, json={"archives": [OCT, NOV]})
    if str(request.url) == OCT:
        return httpx.Response(200, json={"games": [{"url": "g1"}, {"url": "g2"}]})
    if str(request.url) == NOV:
        return httpx.Response(200, json={"games": [{"url": "g3"}]})
    return httpx.Response(404)


def make_client() -> ChessComClient:
    fake_http = httpx.Client(
        base_url=BASE_URL, transport=httpx.MockTransport(fake_chesscom)
    )
    return ChessComClient(http=fake_http)


def test_username_is_lowercased():
    archives = make_client().get_archives("TestPlayer")
    assert archives == [OCT, NOV]


def test_all_games_combines_every_month():
    games = make_client().get_all_games("testplayer")
    assert len(games) == 3


def test_unknown_player_raises():
    with pytest.raises(httpx.HTTPStatusError):
        make_client().get_archives("nobody")


# ---------- 2.5: retries ----------


def client_with(handler, sleep=lambda seconds: None) -> ChessComClient:
    """A client whose 'internet' is `handler`. By default, sleeping does nothing."""
    http = httpx.Client(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return ChessComClient(http=http, sleep=sleep)


def test_retries_after_429_then_succeeds():
    answers = [
        httpx.Response(429),
        httpx.Response(429),
        httpx.Response(200, json={"archives": [OCT]}),
    ]
    waits: list[float] = []
    client = client_with(lambda request: answers.pop(0), sleep=waits.append)
    assert client.get_archives("testplayer") == [OCT]
    assert waits == [1, 2]


def test_gives_up_after_max_attempts():
    calls = []

    def always_down(request):
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(httpx.HTTPStatusError):
        client_with(always_down).get_archives("testplayer")
    assert len(calls) == 4


def test_404_is_not_retried():
    calls = []

    def not_found(request):
        calls.append(request)
        return httpx.Response(404)

    with pytest.raises(httpx.HTTPStatusError):
        client_with(not_found).get_archives("nobody")
    assert len(calls) == 1


# ---------- 2.6: ETag caching ----------


def test_second_request_uses_cache_on_304():
    seen_labels = []  # the label each request carried (None if it carried none)

    def fake(request):
        label = request.headers.get("If-None-Match")
        seen_labels.append(label)
        if label == '"v1"':
            return httpx.Response(304)
        return httpx.Response(
            200, json={"games": [{"url": "g1"}]}, headers={"ETag": '"v1"'}
        )

    client = client_with(fake)
    first = client.get_month(MONTH)
    second = client.get_month(MONTH)

    assert second == first  # same games, even though the 2nd answer had no data
    assert seen_labels == [None, '"v1"']  # 1st carried nothing, 2nd carried our label


def test_changed_data_replaces_cache():
    versions = [
        httpx.Response(200, json={"games": [{"url": "g1"}]}, headers={"ETag": '"v1"'}),
        httpx.Response(
            200,
            json={"games": [{"url": "g1"}, {"url": "g2"}]},
            headers={"ETag": '"v2"'},
        ),
    ]
    client = client_with(lambda request: versions.pop(0))
    client.get_month(MONTH)
    second = client.get_month(MONTH)

    assert len(second) == 2  # new data was used
    assert client.cache[MONTH][0] == '"v2"'  # and the stored label was replaced


def test_no_etag_means_no_cache():
    client = client_with(lambda request: httpx.Response(200, json={"games": []}))
    client.get_month(MONTH)
    assert MONTH not in client.cache
