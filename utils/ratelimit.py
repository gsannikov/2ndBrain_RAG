"""Rate limiting middleware for FastAPI."""

import logging
import time
from typing import Dict
from threading import RLock
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with token bucket algorithm."""

    def __init__(self, requests_per_minute: int = 60, cleanup_interval: float = 300):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Allowed requests per minute per client
            cleanup_interval: How often to clean up stale clients (seconds)
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_minute / 60
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()

        # Track requests: {client_ip: [(timestamp, tokens_remaining)]}
        self.buckets: Dict[str, list] = defaultdict(list)
        self.lock = RLock()

    def _get_client_key(self, client_ip: str) -> str:
        """Get cache key for client IP."""
        return f"rate_limit:{client_ip}"

    def _cleanup_expired(self) -> None:
        """Remove old entries (older than 1 minute)."""
        current_time = time.time()
        cutoff_time = current_time - 60

        with self.lock:
            # Only cleanup if interval passed
            if current_time - self.last_cleanup < self.cleanup_interval:
                return

            for client_ip in list(self.buckets.keys()):
                # Remove old entries
                self.buckets[client_ip] = [
                    (ts, tokens) for ts, tokens in self.buckets[client_ip]
                    if ts > cutoff_time
                ]

                # Remove client if no entries
                if not self.buckets[client_ip]:
                    del self.buckets[client_ip]

            self.last_cleanup = current_time
            logger.debug(f"Rate limit cleanup: {len(self.buckets)} active clients")

    def is_allowed(self, client_ip: str) -> bool:
        """
        Check if request from client is allowed.

        Args:
            client_ip: Client IP address

        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()
        cutoff_time = current_time - 60  # 1 minute window

        with self.lock:
            # Clean up expired entries periodically
            self._cleanup_expired()

            # Get recent requests from this client
            recent = [
                ts for ts, _ in self.buckets[client_ip]
                if ts > cutoff_time
            ]

            # Check if under limit
            if len(recent) >= self.requests_per_minute:
                logger.warning(
                    f"Rate limit exceeded for {client_ip}: "
                    f"{len(recent)}/{self.requests_per_minute} in last minute"
                )
                return False

            # Record this request
            self.buckets[client_ip].append((current_time, None))
            return True

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        with self.lock:
            total_clients = len(self.buckets)
            total_requests = sum(len(reqs) for reqs in self.buckets.values())

            return {
                "active_clients": total_clients,
                "total_requests_tracked": total_requests,
                "limit_per_minute": self.requests_per_minute
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting to all endpoints."""

    def __init__(self, app, requests_per_minute: int = 60):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute per client
        """
        super().__init__(app)
        self.rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
        logger.info(f"Rate limit middleware enabled: {requests_per_minute} req/min")

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to request."""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit response for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded: {self.rate_limiter.requests_per_minute} requests per minute allowed"
                }
            )

        # Proceed with request
        response = await call_next(request)
        return response

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return self.rate_limiter.get_stats()
