"""
Output format definitions and enums.
"""

from enum import Enum
from typing import List, Set
from utils.exceptions import TranslationError


class OutputFormat(Enum):
    """Supported output formats."""

    EPUB = "epub"
    PDF = "pdf"
    MARKDOWN = "markdown"


def parse_output_formats(formats: List[str]) -> Set[OutputFormat]:
    """Parse and validate output formats."""
    valid_formats = set()
    for fmt in formats:
        try:
            valid_formats.add(OutputFormat(fmt.lower()))
        except ValueError:
            raise TranslationError(
                f"Invalid output format: {fmt}. Supported formats: epub, pdf, markdown"
            )

    if not valid_formats:
        valid_formats.add(OutputFormat.MARKDOWN)  # Default fallback

    return valid_formats