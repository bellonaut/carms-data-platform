from __future__ import annotations

import asyncio
from collections import defaultdict
from time import monotonic
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from carms.core.config import Settings


def get_settings() -> Settings:
    # Instantiate on demand so env overrides (tests) are respected.
    return Settings()


_rate_lock = asyncio.Lock()
_request_times: defaultdict[str, list[float]] = defaultdict(list)


async def rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """
    Simple sliding-window rate limiter.
    - Respects RATE_LIMIT_REQUESTS per RATE_LIMIT_WINDOW_SEC.
    - When RATE_LIMIT_REQUESTS <= 0, the limiter is disabled.
    """
    max_requests = settings.rate_limit_requests
    window = settings.rate_limit_window_sec
    if max_requests <= 0:
        return

    ident = request.client.host if request.client else "anonymous"
    now = monotonic()
    cutoff = now - window

    async with _rate_lock:
        times = _request_times[ident]
        # Drop requests outside window
        while times and times[0] < cutoff:
            times.pop(0)

        if len(times) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please retry shortly.",
            )

        times.append(now)


async def require_api_key(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """
    Optional API key guard.
    - Set API_KEY to enforce.
    - Uses header X-API-Key.
    """
    if not settings.api_key:
        return

    header = request.headers.get("X-API-Key")
    if header != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
