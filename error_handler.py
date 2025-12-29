"""
CiteKit – Error Handler
Standardized error responses and exception handling
"""

from typing import Any, Dict, Optional, Union
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import traceback
import logging

# Configure logging
logger = logging.getLogger("geo-compiler")


class APIError(Exception):
    """
    Base API error with structured response.
    Use this for all application-level errors.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary response."""
        response = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            response["details"] = self.details
        return response


# ============================================
# PREDEFINED ERROR TYPES
# ============================================

class JobNotFoundError(APIError):
    """Raised when a job is not found."""
    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job '{job_id}' not found. It may have expired or been deleted.",
            error_code="job_not_found",
            status_code=404,
            details={"job_id": job_id}
        )


class JobNotCompletedError(APIError):
    """Raised when trying to download an incomplete job."""
    def __init__(self, job_id: str, status: str):
        super().__init__(
            message=f"Job is not yet completed. Current status: {status}",
            error_code="job_not_completed",
            status_code=400,
            details={"job_id": job_id, "current_status": status}
        )


class QuotaExceededError(APIError):
    """Raised when user exceeds their plan quota."""
    def __init__(self, limit: int, plan: str = "Free Starter"):
        super().__init__(
            message=f"{plan} plan limited to {limit} compilation(s). Please upgrade to Pro.",
            error_code="quota_exceeded",
            status_code=403,
            details={"limit": limit, "plan": plan}
        )


class InvalidURLError(APIError):
    """Raised when URL is invalid or unreachable."""
    def __init__(self, url: str, reason: str = "Invalid or unreachable"):
        super().__init__(
            message=f"Cannot process URL: {reason}",
            error_code="invalid_url",
            status_code=422,
            details={"url": url, "reason": reason}
        )


class AuthenticationError(APIError):
    """Raised when authentication fails."""
    def __init__(self, reason: str = "Invalid or expired token"):
        super().__init__(
            message=f"Authentication failed: {reason}",
            error_code="authentication_failed",
            status_code=401,
            details={"reason": reason}
        )


class InternalError(APIError):
    """Raised for unexpected internal errors."""
    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(
            message=message,
            error_code="internal_error",
            status_code=500,
            details={"support": "If this persists, please contact support."}
        )


# ============================================
# EXCEPTION HANDLERS
# ============================================

async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions."""
    logger.warning(f"APIError: {exc.error_code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException."""
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": str(exc.detail),
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """Handle Pydantic validation errors with helpful messages."""
    errors = exc.errors() if hasattr(exc, 'errors') else []
    
    # Format errors for user-friendly response
    formatted_errors = []
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "Invalid value")
        formatted_errors.append({
            "field": field,
            "message": msg
        })
    
    logger.warning(f"Validation error: {formatted_errors}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed. Check the details for specific issues.",
            "details": formatted_errors
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions - last resort error handler."""
    # Log full traceback for debugging
    logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")
    
    # Return generic error to user (don't expose internals)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred. Our team has been notified.",
            "details": {
                "support": "If this persists, please contact support with your request details."
            }
        }
    )


def setup_error_handlers(app):
    """Register all error handlers on the FastAPI app."""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
