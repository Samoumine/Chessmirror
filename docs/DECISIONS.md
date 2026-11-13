# Decisions

## 2026-11-12 · Step 1: project setup

**What I did:** uv package (src layout), FastAPI app with GET /health, pytest + ruff, GitHub Actions CI
**Why:**
- uv: one tool for the Python version, venv and packages; uv.lock pins exact versions, so my laptop, CI and the server install the same thing.
- FastAPI: type hints give me input validation and /docs for free, and it's async-ready for slow calls to Chess.com and Claude later.
- pytest + ruff: tests catch when I break behaviour; ruff catches likely bugs and keeps the style consistent automatically.
- CI: every push is checked on a clean machine, so forgotten files and "works on my machine" bugs get caught before they reach main.
**Alternatives I rejected:** pip + venv, because it's several tools with no automatic lockfile, so installs can drift over time; Flask, because it's WSGI (synchronous) and needs extra libraries for validation and API docs that FastAPI includes.
**Proof it works:** tests/test_health.py passes locally and in CI (green ✓ on commit ______)