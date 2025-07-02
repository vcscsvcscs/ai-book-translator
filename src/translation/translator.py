"""
Enhanced translation logic with multiple output format support and proper chapter preservation.
"""

from pathlib import Path
from typing import Optional, List

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from llama_index.core.llms import LLM

from .output.formats import parse_output_formats, OutputFormat
from .output.generators import generate_epub, generate_pdf, generate_markdown

from .chapter_cache import ChapterCache
from .chapter_translator import ChapterTranslator

from .progress import ProgressTracker

from utils.exceptions import TranslationError


class BookTranslator:
    """Handles book translation using LLM providers with multiple output formats."""

    def __init__(
        self,
        llm: LLM,
        chunk_size: int = 1000,
        max_retries: int = 3,
        retry_delay: int = 180,
        progress_file: Optional[str] = None,
        extra_prompts: str = "",
        output_formats: Optional[List[str]] = None,
    ):
        self.llm = llm
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts
        
        # Initialize progress tracking
        self.progress_tracker = (
            ProgressTracker(progress_file) if progress_file else None
        )

        # Initialize chapter cache
        cache_file = None
        if progress_file:
            cache_file = Path(progress_file).with_suffix('.chapters.json')
        self.chapter_cache = ChapterCache(cache_file)
        
        # Initialize the cache (loads existing chunk cache)
        self.chapter_cache.initialize_cache()

        # Initialize chapter translator - this will handle all translation logic
        self.chapter_translator = ChapterTranslator(
            llm=llm,
            chunk_size=chunk_size,
            max_retries=max_retries,
            retry_delay=retry_delay,
            extra_prompts=extra_prompts,
            chapter_cache=self.chapter_cache  # Pass cache to translator
        )

        # Parse output formats
        self.output_formats = parse_output_formats(output_formats or ["markdown"])

        # Store translated chapters for multi-format output
        self.translated_chapters = []

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

            # Show progress summary if resuming
            progress = self.progress_tracker.get_overall_progress()
            if progress and progress.chapters:
                print("📄 Resuming from previous session:")
                print(
                    f"   - Overall progress: {progress.overall_progress_percentage:.1f}%"
                )
                print(
                    f"   - Completed chapters: {progress.completed_chapters}/{progress.total_chapters}"
                )
                print(f"   - Current chapter: {progress.current_chapter}")

        # Load previously completed chapters from cache
        self.translated_chapters = self.chapter_cache.load_chapters()

        current_chapter = 1

        try:
            for item in chapters:
                if from_chapter <= current_chapter <= to_chapter:
                    print(
                        f"\n🔄 Processing chapter {current_chapter}/{total_chapters}..."
                    )

                    # Check if chapter is already completed
                    if (
                        self.progress_tracker
                        and self.progress_tracker.is_chapter_completed(current_chapter)
                    ):
                        print(
                            f"✅ Chapter {current_chapter} already completed, skipping..."
                        )

                        # Ensure the chapter is in our translated_chapters list
                        if not any(
                            ch["number"] == current_chapter
                            for ch in self.translated_chapters
                        ):
                            # This shouldn't happen if cache is working, but as a fallback
                            # we can try to reconstruct from the original if needed
                            chapter_title = self._extract_chapter_title(
                                item, current_chapter
                            )
                            print(
                                f"⚠️  Chapter {current_chapter} was completed but not in cache, adding placeholder"
                            )
                            self.translated_chapters.append(
                                {
                                    "number": current_chapter,
                                    "title": chapter_title,
                                    "content": "[Previously translated content not available in cache]",
                                    "original_item": item,
                                }
                            )

                        current_chapter += 1
                        continue

                    # Load progress if available
                    start_chunk = 0
                    if self.progress_tracker:
                        start_chunk = self.progress_tracker.get_chapter_progress(
                            current_chapter
                        )
                        if start_chunk > 0:
                            print(f"📄 Resuming from chunk {start_chunk + 1}")

                    # Translate chapter using ChapterTranslator
                    translated_content = self.chapter_translator.translate_chapter(
                        item=item,
                        from_lang=from_lang,
                        to_lang=to_lang,
                        chapter_num=current_chapter,
                        start_chunk=start_chunk,
                        progress_tracker=self.progress_tracker
                    )

                    # Store chapter data for multi-format output
                    chapter_data = {
                        "number": current_chapter,
                        "title": self._extract_chapter_title(item, current_chapter),
                        "content": translated_content,
                        "original_item": item,
                    }

                    # Add or update chapter in our list
                    existing_chapter_idx = None
                    for i, ch in enumerate(self.translated_chapters):
                        if ch["number"] == current_chapter:
                            existing_chapter_idx = i
                            break

                    if existing_chapter_idx is not None:
                        self.translated_chapters[existing_chapter_idx] = chapter_data
                    else:
                        self.translated_chapters.append(chapter_data)
                        # Keep list sorted by chapter number
                        self.translated_chapters.sort(key=lambda x: x["number"])

                    # Mark chapter as complete
                    if self.progress_tracker:
                        self.progress_tracker.complete_chapter(current_chapter)

                    # Save chapter cache after each completed chapter
                    self.chapter_cache.save_chapters(self.translated_chapters)

                    print(f"✅ Chapter {current_chapter} completed")

                current_chapter += 1

            # Generate all requested output formats
            self._generate_outputs(book, output_path, from_lang, to_lang)

        except Exception as e:
            print(f"\n❌ Translation interrupted at chapter {current_chapter}")
            print(f"💾 Progress saved. Resume with: --from-chapter {current_chapter}")
            raise TranslationError(f"Translation failed: {e}")

    def _generate_outputs(
        self, original_book, output_path: str, from_lang: str, to_lang: str
    ):
        """Generate all requested output formats."""
        base_path = Path(output_path).with_suffix("")

        # Ensure we have all chapters sorted by number
        self.translated_chapters.sort(key=lambda x: x["number"])

        print(f"📄 Generating outputs with {len(self.translated_chapters)} chapters")

        for format_type in self.output_formats:
            try:
                if format_type == OutputFormat.MARKDOWN:
                    generate_markdown(
                        self.translated_chapters,
                        base_path.with_suffix(".md"), from_lang, to_lang
                    )
                elif format_type == OutputFormat.EPUB:
                    generate_epub(
                        self.translated_chapters,
                        base_path.with_suffix(".epub"),
                        from_lang,
                        to_lang,
                        original_book,
                    )
                elif format_type == OutputFormat.PDF:
                    generate_pdf(
                        self.translated_chapters,
                        base_path.with_suffix(".pdf"), from_lang, to_lang
                    )

                print(f"✅ {format_type.value.upper()} output generated")

            except Exception as e:
                print(f"❌ Failed to generate {format_type.value.upper()}: {e}")

    def _extract_chapter_title(self, item, chapter_num: int) -> str:
        """Extract chapter title from EPUB item."""
        try:
            soup = BeautifulSoup(item.content, "html.parser")
            title_elem = soup.find(["h1", "h2", "h3", "title"])
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) < 100:  # Reasonable title length
                    return title
        except Exception:
            pass

        return f"Chapter {chapter_num}"

    def _get_document_items(self, book):
        """Get all document items from the book."""
        return [
            item
            for item in book.get_items()
            if item.get_type() == ebooklib.ITEM_DOCUMENT
        ]