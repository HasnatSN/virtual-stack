from collections import defaultdict
import time
from typing import Optional

from fastapi import HTTPException, Request, status

from virtualstack.core.config import settings # Import settings


# Simple in-memory rate limiter
# Format: {key: [(timestamp1, count1), (timestamp2, count2), ...]}
rate_limit_store: dict[str, list] = defaultdict(list)


def _clean_old_requests(key: str, window_seconds: int) -> None:
    """Clean up old requests outside the time window."""
    current_time = time.time()
    # Keep only entries within the time window
    rate_limit_store[key] = [
        (timestamp, count)
        for timestamp, count in rate_limit_store.get(key, [])
        if current_time - timestamp < window_seconds
    ]


def _add_request(key: str) -> None:
    """Add a new request to the rate limit store."""
    current_time = time.time()

    # Try to find the current second in the store
    for i, (timestamp, count) in enumerate(rate_limit_store.get(key, [])):
        if abs(current_time - timestamp) < 1.0:  # Same second
            # Update the count
            rate_limit_store[key][i] = (timestamp, count + 1)
            return

    # No matching second found, add a new entry
    rate_limit_store[key].append((current_time, 1))


def _get_total_requests(key: str) -> int:
    """Get the total number of requests within the time window."""
    return sum(count for _, count in rate_limit_store.get(key, []))


def rate_limit(
    max_requests: int = 10, window_seconds: int = 60, key_func: Optional[callable] = None
):
    """Rate limit requests based on a key.

    Args:
        max_requests: Maximum number of requests allowed within the window
        window_seconds: Time window in seconds
        key_func: Function to extract a key from the request (defaults to client IP)
    """

    async def rate_limit_dependency(request: Request):
        # Bypass rate limiting for test environment
        if settings.RUN_ENV == "test":
            return True

        # Get a key to identify the client
        if key_func:
            key = key_func(request)
        else:
            # Default to client IP
            forwarded = request.headers.get("X-Forwarded-For")
            key = forwarded.split(",")[0].strip() if forwarded else request.client.host

        # Clean old requests
        _clean_old_requests(key, window_seconds)

        # Get current request count
        total_requests = _get_total_requests(key)

        # Check if rate limit exceeded
        if total_requests >= max_requests:
            # Calculate time to wait until reset
            oldest_timestamp = min(
                [timestamp for timestamp, _ in rate_limit_store.get(key, [])], default=time.time()
            )
            retry_after = int(window_seconds - (time.time() - oldest_timestamp))

            headers = {
                "Retry-After": str(max(1, retry_after)),
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + retry_after)),
            }

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers=headers,
            )

        # Add the current request
        _add_request(key)

        # Add rate limit headers
        request.state.rate_limit_remaining = max_requests - total_requests - 1

        return True

    return rate_limit_dependency
