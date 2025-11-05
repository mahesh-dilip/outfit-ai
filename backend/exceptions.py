"""
Custom Exception Classes for Outfit AI
Provides specific exceptions for better error handling
"""

from typing import Any, Dict, Optional


class OutfitAIException(Exception):
    """Base exception for all OutfitAI custom exceptions"""
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(OutfitAIException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTH_FAILED",
            status_code=401,
            details=details
        )


class AuthorizationError(OutfitAIException):
    """Raised when user doesn't have permission"""
    def __init__(self, message: str = "Not authorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="NOT_AUTHORIZED",
            status_code=403,
            details=details
        )


class ResourceNotFoundError(OutfitAIException):
    """Raised when a requested resource doesn't exist"""
    def __init__(self, resource: str, resource_id: Any, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{resource} with id {resource_id} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details=details or {"resource": resource, "id": resource_id}
        )


class ValidationError(OutfitAIException):
    """Raised when input validation fails"""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details or {"field": field} if field else details
        )


class GCSUploadError(OutfitAIException):
    """Raised when GCS upload fails"""
    def __init__(self, message: str = "Failed to upload file to cloud storage", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="GCS_UPLOAD_FAILED",
            status_code=500,
            details=details
        )


class VectorDBError(OutfitAIException):
    """Raised when vector database operations fail"""
    def __init__(self, message: str = "Vector database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VECTOR_DB_ERROR",
            status_code=500,
            details=details
        )


class AIGenerationError(OutfitAIException):
    """Raised when AI generation fails"""
    def __init__(self, message: str = "AI generation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AI_GENERATION_FAILED",
            status_code=500,
            details=details
        )


class DatabaseError(OutfitAIException):
    """Raised when database operations fail"""
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details
        )

