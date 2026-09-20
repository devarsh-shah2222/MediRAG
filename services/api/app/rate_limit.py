import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

# ponytail: in-memory, per-process sliding-window counter instead of a
# Redis-backed limiter. Correct and sufficient for a single-instance
# deployment; resets on restart and does not coordinate across multiple
# instances. Upgrade trigger: running more than one API process/replica.
_WINDOW_SECONDS = 60
_hits: dict[str, deque] = defaultdict(deque)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def make_rate_limiter(max_requests: int, window_seconds: int = _WINDOW_SECONDS):
    def limiter(request: Request) -> None:
        key = f"{_client_key(request)}:{request.url.path}"
        now = time.monotonic()
        hits = _hits[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a moment and try again.",
            )
        hits.append(now)

    return limiter
