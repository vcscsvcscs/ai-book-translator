"""
Handles book translation logic.
"""

from typing import Optional, List, Set

import ebooklib
from ebooklib import epub
from .chapter_processor import ChapterProcessor
from .output_generator import OutputGenerator, OutputFormat
from .progress import ProgressTracker
from utils.exceptions import TranslationError



class BookTranslator:
    """Handles book translation using LLM providers with multiple output formats."""

    def __init__(
        self,
        llm,
        chunk_size: int = 20000,
        max_retries: int = 3,
        retry_delay: int = 180,
        progress_file: Optional[str] = None,
        extra_prompts: str = "",
        output_formats: Optional[List[str]] = None,
    ):
        self.llm = llm
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts
        self.progress_tracker = (
            ProgressTracker(progress_file) if progress_file else None
        )

        # Parse output formats
        self.output_formats = self._parse_output_formats(output_formats or ["markdown"])

        # Store translated chapters for multi-format output
        self.translated_chapters = []

        # Initialize helper components
        self.chapter_processor = ChapterProcessor(
            llm,
            chunk_size,
            max_retries,
            retry_delay,
            extra_prompts,
            self.progress_tracker,
        )
        self.output_generator = OutputGenerator(self.translated_chapters)

    def _parse_output_formats(self, formats: List[str]) -> Set[OutputFormat]:
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

    def translate_book(
        self,
        input_path: str,
        output_path: str,
        from_chapter: int = 1,
        to_chapter: int = 9999,
        from_lang: str = "EN",
        to_lang: str = "HU",
    ):
        """Translate entire book and generate requested output formats."""
        try:
            book = epub.read_epub(input_path)
        except Exception as e:
            raise TranslationError(f"Failed to read EPUB file: {e}")

        chapters = self._get_document_items(book)
        total_chapters = len(chapters)

        print(f"📚 Found {total_chapters} chapters to process")
        print(f"🔄 Translation: {from_lang} → {to_lang}")
        print(
            f"📖 Processing chapters {from_chapter} to {min(to_chapter, total_chapters)}"
        )
        print(
            f"📄 Output formats: {', '.join([fmt.value for fmt in self.output_formats])}"
        )

        # Initialize progress tracking
        if self.progress_tracker:
            self.progress_tracker.start_translation(total_chapters)

        current_chapter = 1
        self.translated_chapters = []  # Reset for new translation

        try:
            for item in chapters:
                if from_chapter <= current_chapter <= to_chapter:
                    print(
                        f"\n🔄 Processing chapter {current_chapter}/{total_chapters}..."
                    )

                    # Translate chapter
                    chapter_data = self.chapter_processor.process_chapter(
                        item, from_lang, to_lang, current_chapter
                    )
                    self.translated_chapters.append(chapter_data)

                    print(f"✅ Chapter {current_chapter} completed")
                elif to_chapter < current_chapter:
                    break
                
                current_chapter += 1

            # Generate all requested output formats
            self.output_generator.generate_outputs(
                book, output_path, from_lang, to_lang, self.output_formats
            )

        except Exception as e:
            print(f"\n❌ Translation interrupted at chapter {current_chapter}")
            raise TranslationError(f"Translation failed: {e}")

    def _get_document_items(self, book):
        """Get all document items from the book."""
        return [
            item for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT
        ]
