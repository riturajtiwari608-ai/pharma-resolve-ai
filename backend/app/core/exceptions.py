class AIServiceError(Exception):
    """Base exception for AI service failures."""


class AIConfigurationError(AIServiceError):
    """Raised when AI configuration is missing or invalid."""


class AIModelUnavailableError(AIServiceError):
    """Raised when the requested Groq model is unavailable."""


class AIResponseValidationError(AIServiceError):
    """Raised when the model returns invalid structured data."""