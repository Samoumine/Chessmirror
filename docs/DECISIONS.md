# Decisions

## 2026-11-12 · Step 1: project setup

**What I did:** uv package (src layout), FastAPI app with GET /health, pytest + ruff, GitHub Actions CI
**Why:**
- uv: one tool for the Python version, venv and packages; uv.lock pins exact versions, so my laptop, CI and the server install the same thing.
- FastAPI: type hints give me input validation and /docs for free, and it's async-ready for slow calls to Chess.com and Claude later.
- pytest + ruff: tests catch when I break behaviour; ruff catches likely bugs and keeps the style consistent automatically.
- CI: every push is checked on a clean machine, so forgotten files and "works on my machine" bugs get caught before they reach main.
**Alternatives I rejected:** pip + venv, because it's several tools with no automatic lockfile, so installs can drift over time; Flask, because it's WSGI (synchronous) and needs extra libraries for validation and API docs that FastAPI includes.

## 2026-11-24 · Step 2: Chess.com client
**What I did:** A client that fetches any player's monthly archives one request at a time, retries temporary errors with exponential backoff, and caches responses with ETags. Tests use a fake Chess.com.
**Why:**
- One request at a time: Chess.com allows unlimited requests one after another, but parallel requests can get 429s, and unusual activity can get the app blocked.
- Retrying 429 and 5xx with growing waits (1 s, 2 s, 4 s): these errors are temporary, so waiting gives the server time to recover; growing waits avoid hammering an overloaded server, and giving up after 4 attempts avoids an infinite loop.
- Not retrying 404: it's permanent, so retrying gets the same answer and only delays the "player not found" message.
- ETag cache: instead of re-downloading every month, the client sends the label it has and asks "has this changed?"; a 304 means reuse the stored copy, which is faster for the user and lighter on Chess.com.
- A fake Chess.com in tests: fast, works offline and in CI, its data never changes, and it can produce 429, 503 and 304 on demand.
**Alternatives I rejected:** parallel requests, because they risk 429s and getting blocked; retrying instantly with no wait, because it gets the same error and adds load to a server that's already struggling; testing against the real API, because it's slow, fails when the network does, its data changes daily, and it can't be made to return errors on demand.
**Proof it works:** 9 tests in tests/test_chesscom.py, CI green on commit a6582491c4a28facf542cdee2e29aea87843b0f1