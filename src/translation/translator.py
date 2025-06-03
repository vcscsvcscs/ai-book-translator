"""
Main translation logic.
"""

import time
from pathlib import Path
from typing import Optional

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from llama_index.core.llms import LLM

from .chunker import TextChunker
from .progress import ProgressTracker
from utils.exceptions import TranslationError


class BookTranslator:
    """Handles book translation using LLM providers."""

    def __init__(
        self,
        llm: LLM,
        chunk_size: int = 20000,
        max_retries: int = 3,
        retry_delay: int = 180,
        progress_file: Optional[str] = None,
    ):
        self.llm = llm
        self.chunker = TextChunker(chunk_size)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.progress_tracker = (
            ProgressTracker(progress_file) if progress_file else None
        )

    def translate_book(
        self,
        input_path: str,
        output_path: str,
        from_chapter: int = 1,
        to_chapter: int = 9999,
        from_lang: str = "EN",
        to_lang: str = "HU",
    ):
        """Translate entire book."""
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

        current_chapter = 1

        try:
            for item in chapters:
                if from_chapter <= current_chapter <= to_chapter:
                    print(
                        f"\n🔄 Processing chapter {current_chapter}/{total_chapters}..."
                    )

                    # Load progress if available
                    start_chunk = 0
                    if self.progress_tracker:
                        start_chunk = self.progress_tracker.get_chapter_progress(
                            current_chapter
                        )

                    # Translate chapter
                    translated_content = self._translate_chapter(
                        item, from_lang, to_lang, current_chapter, start_chunk
                    )

                    # Update book content
                    item.content = translated_content.encode("utf-8")

                    # Save intermediate progress
                    self._save_intermediate_progress(output_path, book)

                    print(f"✅ Chapter {current_chapter} completed")

                current_chapter += 1

            # Final cleanup and save
            self._finalize_translation(output_path, book)

        except Exception as e:
            print(f"\n❌ Translation interrupted at chapter {current_chapter}")
            print(f"💾 Progress saved. Resume with: --from-chapter {current_chapter}")
            raise TranslationError(f"Translation failed: {e}")

    def _get_document_items(self, book):
        """Get all document items from the book."""
        return [
            item
            for item in book.get_items()
            if item.get_type() == ebooklib.ITEM_DOCUMENT
        ]

    def _translate_chapter(
        self, item, from_lang: str, to_lang: str, chapter_num: int, start_chunk: int = 0
    ) -> str:
        """Translate a single chapter."""
        soup = BeautifulSoup(item.content, "html.parser")
        text = str(soup)

        chunks = self.chunker.split_text(text)
        total_chunks = len(chunks)

        print(f"  📄 Split into {total_chunks} chunks")

        translated_chunks = [
            ""
        ] * start_chunk  # Placeholders for already translated chunks

        for i, chunk in enumerate(chunks[start_chunk:], start=start_chunk):
            print(f"    🔄 Chunk {i + 1}/{total_chunks}...")

            try:
                translated_chunk = self._translate_chunk(chunk, from_lang, to_lang)
                translated_chunks.append(translated_chunk)

                # Update progress
                if self.progress_tracker:
                    self.progress_tracker.update_progress(
                        chapter_num, i + 1, total_chunks
                    )

            except Exception as e:
                raise TranslationError(f"Failed to translate chunk {i + 1}: {e}")

        return " ".join(translated_chunks)

    def _translate_chunk(self, text: str, from_lang: str, to_lang: str) -> str:
        """Translate a single chunk of text."""
        prompt = self._create_translation_prompt(text, from_lang, to_lang)

        for attempt in range(self.max_retries):
            try:
                response = self.llm.complete(prompt)
                return response.text.strip()

            except Exception as e:
                error_msg = str(e).lower()

                # Handle rate limiting
                if "rate limit" in error_msg or "quota" in error_msg:
                    if attempt < self.max_retries - 1:
                        print(
                            f"    ⏳ Rate limit hit. Waiting {self.retry_delay}s... (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(self.retry_delay)
                        continue

                # Handle other errors
                if attempt < self.max_retries - 1:
                    print(f"    ⚠️  Error on attempt {attempt + 1}: {e}")
                    time.sleep(5)  # Short delay
                    continue

                # Final attempt failed
                raise TranslationError(
                    f"Translation failed after {self.max_retries} attempts: {e}"
                )
        # If somehow all attempts are exhausted without raising, return an empty string
        return ""

    def _create_translation_prompt(
        self, text: str, from_lang: str, to_lang: str
    ) -> str:
        """Create translation prompt."""
        return (
            f"You are a {from_lang}-to-{to_lang} specialized translator. "
            f"Keep all special characters and HTML tags exactly as in the source text. "
            f"Your translation should be in {to_lang} only. "
            f"Ensure the translation is comfortable to read by avoiding overly literal translations. "
            f"Maintain readability and consistency with the source text. "
            f"Do not add any explanations or comments, just provide the translation.\n\n"
            f"Text to translate:\n{text}"
        )

    def _save_intermediate_progress(self, output_path: str, book):
        """Save intermediate progress."""
        partial_path = f"{output_path}.partial"
        try:
            epub.write_epub(partial_path, book, {})
        except Exception as e:
            print(f"⚠️  Warning: Could not save intermediate progress: {e}")

    def _finalize_translation(self, output_path: str, book):
        """Finalize translation and cleanup."""
        try:
            # Write final EPUB
            epub.write_epub(output_path, book, {})

            # Cleanup
            partial_path = Path(f"{output_path}.partial")
            if partial_path.exists():
                partial_path.unlink()

            if self.progress_tracker:
                self.progress_tracker.cleanup()

            print("\n🎉 Translation completed successfully!")
            print(f"📖 Output saved to: {output_path}")

        except Exception as e:
            raise TranslationError(f"Failed to finalize translation: {e}")
