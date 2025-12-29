"""
CiteKit – Rate Limiting Middleware
Request rate limiting for API protection
"""

import time
from collections import defaultdict
from typing import Dict, Tuple, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiter middleware.
    Limits requests per IP address to prevent abuse.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        
        # Store: {ip: (tokens, last_refill_time)}
        self._minute_buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (float(requests_per_minute), time.time())
        )
        self._hour_buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (float(requests_per_hour), time.time())
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Direct connection
        if request.client:
            return request.client.host
        
        return "unknown"

    def _check_rate_limit(
        self,
        bucket: Dict[str, Tuple[float, float]],
        ip: str,
        rate: int,
        window_seconds: int
    ) -> Tuple[bool, float]:
        """
        Check and update rate limit for an IP.
        Returns (allowed, tokens_remaining).
        """
        tokens, last_refill = bucket[ip]
        now = time.time()
        
        # Refill tokens based on time passed
        time_passed = now - last_refill
        refill_amount = (time_passed / window_seconds) * rate
        tokens = min(float(rate), tokens + refill_amount)
        
        if tokens >= 1:
            # Allow request, consume token
            tokens -= 1
            bucket[ip] = (tokens, now)
            return True, tokens
        else:
            # Rate limited
            bucket[ip] = (tokens, now)
            return False, tokens

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        ip = self._get_client_ip(request)
        
        # Check minute limit
        allowed_minute, remaining_minute = self._check_rate_limit(
            self._minute_buckets, ip, self.requests_per_minute, 60
        )
        
        if not allowed_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": 60
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Check hour limit
        allowed_hour, remaining_hour = self._check_rate_limit(
            self._hour_buckets, ip, self.requests_per_hour, 3600
        )
        
        if not allowed_hour:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Hourly rate limit exceeded. Please try again later.",
                    "retry_after": 3600
                },
                headers={
                    "Retry-After": "3600",
                    "X-RateLimit-Limit": str(self.requests_per_hour),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(int(remaining_minute))
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Request validation middleware.
    Validates request size and content type.
    """

    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB

    async def dispatch(self, request: Request, call_next):
        """Validate request before processing."""
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "payload_too_large",
                    "message": f"Request body exceeds maximum size of {self.MAX_BODY_SIZE // (1024*1024)} MB"
                }
            )
        
        return await call_next(request)
