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

## 2026-11-27 · Step 3: database + ingest
**What I did:** Postgres 17 (+pgvector) in Docker, players/games/http_cache tables as SQLAlchemy classes, an Alembic migration, and an idempotent ingest that saves any player's games in chunks inside one transaction.
**Why:**
- A database instead of Python lists or JSON files: data survives restarts, we can ask questions across thousands of games with SQL, and several programs can read and write safely at the same time.
- Postgres over SQLite: the API and the worker will write at the same time, v2 needs pgvector, and it's the same database we'll run in production.
- Each game stores both players' usernames, not "who fetched it": a game is a fact about two players, so it's stored once and both players' reports can find it.
- games has a number id AND a unique URL: the short number is what other tables (moves) point at, hundreds of thousands of times; the unique URL is what blocks duplicate games.
- A unique rule in the database instead of checking in Python first: the database checks and saves in one atomic step, so two workers saving the same game at once can't both slip in.
- Migrations instead of deleting and recreating tables: the live tables hold real users' games; a migration changes the structure and keeps the rows, and runs the same everywhere.
- The caller owns one transaction for the whole ingest: all or nothing; a crash or an unknown player rolls back everything, so no half-saved games and no ghost player rows.
- Saving in chunks of 1,000 rows, one statement per chunk: one statement per chunk means few round trips to Postgres, and chunks stay under its ~65,000-value limit per statement.
**Alternatives I rejected:** JSON files, because they can't be queried, don't block duplicates and break when two programs write at once; SQLite, because it's weaker with two programs writing at once and has no pgvector; checking for duplicates in Python, because two workers can both check, see nothing and both insert; committing after each chunk, because a crash would leave half the games saved and last_fetched_at wrong.
**Proof it works:** 4 to_row tests; live ingest of saoum: 963 fetched, 959 saved, 4 variants skipped; the re-run added only the 4 games played in between (7.0 s total, ~6 s waiting on Chess.com).