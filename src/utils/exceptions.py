"""
Custom exceptions for the book translator.
"""


class BookTranslatorError(Exception):
    """Base exception for book translator."""
    pass


class ConfigurationError(BookTranslatorError):
    """Raised when there's a configuration error."""
    pass


class TranslationError(BookTranslatorError):
    """Raised when translation fails."""
    pass


class EpubError(BookTranslatorError):
    """Raised when there's an EPUB processing error."""
    pass


class LLMError(BookTranslatorError):
    """Raised when there's an LLM-related error."""
    pass


class ProgressError(BookTranslatorError):
    """Raised when there's a progress tracking error."""
    pass