import time
import redis.asyncio as redis
from fastapi import Request, Depends, HTTPException, status
from typing import Callable, Optional
from functools import wraps

from virtualstack.core.config import settings # Assuming Redis URL is in settings

# TODO: Configure Redis connection properly, maybe move to deps?
r = redis.from_url(settings.REDIS_URL or f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", decode_responses=True)

def rate_limit(max_requests: int, window_seconds: int):
    """
    Decorator factory for rate limiting API endpoints using Redis.

    Args:
        max_requests: Maximum number of requests allowed.
        window_seconds: Time window in seconds.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # The actual dependency function that FastAPI resolves
            request: Optional[Request] = kwargs.get('request')
            if not request:
                 # Try finding request in args if not in kwargs (e.g., direct call)
                 for arg in args:
                      if isinstance(arg, Request):
                           request = arg
                           break
            
            if not request:
                # Should not happen in normal FastAPI flow, but defensively handle
                print("Rate limiter: Could not find Request object.")
                # Allow request if context is unclear?
                # Or raise an internal server error?
                # raise HTTPException(status_code=500, detail="Rate limiter context error")
                return await func(*args, **kwargs) # Proceed without limiting for now

            # Generate a unique key for the client
            # Use X-Forwarded-For if present (common in proxied setups), else client IP
            forwarded = request.headers.get("X-Forwarded-For")
            client_host = request.client.host if request.client else "unknown_client" # <<< ADDED CHECK for request.client
            identifier = forwarded.split(",")[0].strip() if forwarded else client_host
            
            if not identifier:
                 print("Rate limiter: Could not identify client.")
                 # Allow request if client is unidentified?
                 return await func(*args, **kwargs) # Proceed without limiting

            # Use the endpoint path and identifier for the Redis key
            endpoint_path = request.url.path
            key = f"rate_limit:{endpoint_path}:{identifier}"

            # Use Redis pipeline for atomic operations
            async with r.pipeline() as pipe:
                # Record the current request timestamp
                current_time = time.time()
                pipe.zadd(key, {str(current_time): current_time})
                # Remove timestamps outside the window
                pipe.zremrangebyscore(key, 0, current_time - window_seconds)
                # Count remaining requests in the window
                pipe.zcard(key)
                # Set expiry for the key to clean up Redis
                pipe.expire(key, window_seconds)

                results = await pipe.execute()

            request_count = results[2] # Result of zcard

            if request_count > max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too Many Requests",
                    headers={"Retry-After": str(window_seconds)} # Inform client
                )
            
            # If the original function was passed via depends, we just return None
            # If used as a direct decorator, call the original function
            # This implementation assumes usage as a dependency, returning None on success.
            # To use as a direct decorator, modify the end.
            # For dependency usage:
            # return None 
            # Let's assume dependency usage for login endpoint:
            return None # Indicate success for dependency check

        # Return the dependency function itself
        return wrapper

# Example of how to use it as a dependency in an endpoint:
# @router.post("/login")
# async def login(form_data: OAuth2PasswordRequestForm = Depends(), _: None = Depends(rate_limit(5, 60))):
#    ...
