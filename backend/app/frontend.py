"""Serve the built React app (frontend/dist) from FastAPI for single-URL local and VPS runs.

On Vercel the static files are served by Vercel's CDN instead and this is never reached
(the function bundle contains no dist folder). Anything under /api is never answered here:
unknown API paths keep returning JSON 404s.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import REPO_DIR

DIST_DIR = REPO_DIR / "frontend" / "dist"

# Hashed assets never change; index.html must always be revalidated so deploys take effect.
IMMUTABLE = "public, max-age=31536000, immutable"
NO_CACHE = "no-cache"


def mount_frontend(app: FastAPI, dist: Path = DIST_DIR) -> bool:
    """Add the SPA fallback route if a build exists. Returns whether it was mounted."""
    index = dist / "index.html"
    if not index.is_file():
        return False
    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
        if path:
            candidate = (root / path).resolve()
            # Only files inside dist; anything else (including ../ tricks) gets the app shell.
            if candidate.is_relative_to(root) and candidate.is_file():
                cache = IMMUTABLE if candidate.parent.name == "assets" else NO_CACHE
                return FileResponse(candidate, headers={"Cache-Control": cache})
        return FileResponse(index, headers={"Cache-Control": NO_CACHE})

    return True
