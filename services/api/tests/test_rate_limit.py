import pytest
from fastapi import HTTPException, Request

from app.rate_limit import make_rate_limiter


def _fake_request(path: str = "/api/chat", ip: str = "1.2.3.4") -> Request:
    scope = {
        "type": "http",
        "path": path,
        "headers": [],
        "client": (ip, 12345),
        "method": "POST",
    }
    return Request(scope)


def test_allows_requests_under_the_limit() -> None:
    limiter = make_rate_limiter(max_requests=3)
    request = _fake_request(ip="10.0.0.1")
    for _ in range(3):
        limiter(request)  # should not raise


def test_blocks_requests_over_the_limit() -> None:
    limiter = make_rate_limiter(max_requests=2)
    request = _fake_request(ip="10.0.0.2")
    limiter(request)
    limiter(request)
    with pytest.raises(HTTPException) as exc_info:
        limiter(request)
    assert exc_info.value.status_code == 429


def test_limits_are_tracked_independently_per_client() -> None:
    limiter = make_rate_limiter(max_requests=1)
    limiter(_fake_request(ip="10.0.0.3"))
    limiter(_fake_request(ip="10.0.0.4"))  # different client, should not raise
