"""
Main translation logic.
"""

import time
import re
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
        extra_prompts: str = "",
    ):
        self.llm = llm
        self.chunker = TextChunker(chunk_size)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts
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

        # Initialize progress tracking
        if self.progress_tracker:
            self.progress_tracker.start_translation(total_chapters)
            
            # Show progress summary if resuming
            progress = self.progress_tracker.get_overall_progress()
            if progress and progress.chapters:
                print("📄 Resuming from previous session:")
                print(f"   - Overall progress: {progress.overall_progress_percentage:.1f}%")
                print(f"   - Completed chapters: {progress.completed_chapters}/{progress.total_chapters}")
                print(f"   - Current chapter: {progress.current_chapter}")

        current_chapter = 1
        
        # Initialize markdown output file
        md_output_path = self._get_markdown_path(output_path)
        self._initialize_markdown_file(md_output_path, from_lang, to_lang)

        try:
            for item in chapters:
                if from_chapter <= current_chapter <= to_chapter:
                    print(
                        f"\n🔄 Processing chapter {current_chapter}/{total_chapters}..."
                    )

                    # Check if chapter is already completed
                    if self.progress_tracker and self.progress_tracker.is_chapter_completed(current_chapter):
                        print(f"✅ Chapter {current_chapter} already completed, skipping...")
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

                    # Translate chapter
                    translated_content = self._translate_chapter(
                        item, from_lang, to_lang, current_chapter, start_chunk
                    )

                    # Save translated chapter to markdown
                    self._save_chapter_to_markdown(
                        md_output_path, current_chapter, translated_content, item
                    )

                    # Mark chapter as complete
                    if self.progress_tracker:
                        self.progress_tracker.complete_chapter(current_chapter)

                    print(f"✅ Chapter {current_chapter} completed and saved")

                current_chapter += 1

            # Finalize markdown file
            self._finalize_markdown(md_output_path)

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
        
        # Extract clean text content, preserving structure
        text = self._extract_clean_text(soup)

        chunks = self.chunker.split_text(text)
        total_chunks = len(chunks)

        print(f"  📄 Split into {total_chunks} chunks")

        # Initialize progress tracking for this chapter
        if self.progress_tracker:
            self.progress_tracker.start_chapter(chapter_num, total_chunks)

        translated_chunks = []

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
                # Record error in progress tracker
                if self.progress_tracker:
                    self.progress_tracker.record_error(chapter_num, str(e))
                raise TranslationError(f"Failed to translate chunk {i + 1}: {e}")

        return "\n\n".join(translated_chunks)

    def _extract_clean_text(self, soup: BeautifulSoup) -> str:
        """Extract clean text from HTML, preserving paragraph structure."""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text with some structure preservation
        text = soup.get_text(separator='\n\n', strip=True)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()

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
        
        return ""

    def _create_translation_prompt(
        self, text: str, from_lang: str, to_lang: str
    ) -> str:
        """Create translation prompt."""
        return (
            f"You are a professional {from_lang}-to-{to_lang} translator. "
            f"Translate the following text naturally and fluently to {to_lang}. "
            f"{self.extra_prompts}. "
            f"Maintain readability and consistency with the source text while making it read naturally in {to_lang}. "
            f"Do not add explanations, comments, or notes - only provide the translation.\n\n"
            f"Text to translate:\n{text}"
        )

    def _get_markdown_path(self, output_path: str) -> str:
        """Convert output path to markdown format."""
        path = Path(output_path)
        return str(path.with_suffix('.md'))

    def _initialize_markdown_file(self, md_path: str, from_lang: str, to_lang: str):
        """Initialize the markdown file with header."""
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Translated Book ({from_lang} → {to_lang})\n\n")
            f.write(f"*Translation generated on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write("---\n\n")

    def _save_chapter_to_markdown(self, md_path: str, chapter_num: int, content: str, item):
        """Save a translated chapter to the markdown file."""
        # Extract chapter title if available
        soup = BeautifulSoup(item.content, "html.parser")
        title_elem = soup.find(['h1', 'h2', 'title'])
        chapter_title = title_elem.get_text(strip=True) if title_elem else f"Chapter {chapter_num}"
        
        if content != "":
            with open(md_path, 'a', encoding='utf-8') as f:
                f.write(f"## {content}\n\n")
                f.write("---\n\n")
        
        print(f"  💾 Chapter saved to markdown: {chapter_title}")

    def _finalize_markdown(self, md_path: str):
        """Finalize the markdown file."""
        with open(md_path, 'a', encoding='utf-8') as f:
            f.write(f"\n*Translation completed on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        print("\n🎉 Translation completed successfully!")
        print(f"📖 Output saved to: {md_path}")
        
        if self.progress_tracker:
            self.progress_tracker.cleanup()