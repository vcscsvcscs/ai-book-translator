"""
Handles output generation for translated books.
"""

from pathlib import Path
from ebooklib import epub
from utils.exceptions import TranslationError


class OutputGenerator:
    """Generates output formats for translated books."""

    def __init__(self, translated_chapters):
        self.translated_chapters = translated_chapters

    def generate_outputs(
        self, original_book, output_path, from_lang, to_lang, output_formats
    ):
        """Generate all requested output formats."""
        base_path = Path(output_path).with_suffix("")
        for format_type in output_formats:
            if format_type == "markdown":
                self._generate_markdown(
                    base_path.with_suffix(".md"), from_lang, to_lang
                )
            elif format_type == "epub":
                self._generate_epub(
                    original_book, base_path.with_suffix(".epub"), from_lang, to_lang
                )
            else:
                raise TranslationError(f"Unsupported format: {format_type}")

    def _generate_markdown(self, output_path, from_lang, to_lang):
        """Generate Markdown output."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Translated Book ({from_lang} → {to_lang})\n\n")
            for chapter in self.translated_chapters:
                f.write(f"## {chapter['title']}\n\n{chapter['content']}\n\n")
