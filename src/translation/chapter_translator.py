"""
Chapter translation functionality.
"""

import time
from bs4 import BeautifulSoup
from llama_index.core.llms import LLM

from utils.text_utils import extract_clean_text
from .chunker import TextChunker
from utils.exceptions import TranslationError


class ChapterTranslator:
    """Handles translation of individual chapters."""

    def __init__(
        self, 
        llm: LLM, 
        chunk_size: int = 20000,
        max_retries: int = 3,
        retry_delay: int = 180,
        extra_prompts: str = ""
    ):
        self.llm = llm
        self.chunker = TextChunker(chunk_size)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts

    def translate_chapter(
        self, 
        item, 
        from_lang: str, 
        to_lang: str, 
        chapter_num: int, 
        start_chunk: int = 0,
        progress_tracker=None
    ) -> str:
        """Translate a single chapter."""
        soup = BeautifulSoup(item.content, "html.parser")

        # Extract clean text content, preserving structure
        text = extract_clean_text(soup)

        chunks = self.chunker.split_text(text)
        total_chunks = len(chunks)

        print(f"  📄 Split into {total_chunks} chunks")

        # Initialize progress tracking for this chapter
        if progress_tracker:
            progress_tracker.start_chapter(chapter_num, total_chunks)

        translated_chunks = []

        for i, chunk in enumerate(chunks[start_chunk:], start=start_chunk):
            print(f"    🔄 Chunk {i + 1}/{total_chunks}...")

            try:
                translated_chunk = self._translate_chunk(chunk, from_lang, to_lang)
                translated_chunks.append(translated_chunk)

                # Update progress
                if progress_tracker:
                    progress_tracker.update_progress(
                        chapter_num, i + 1, total_chunks
                    )

            except Exception as e:
                # Record error in progress tracker
                if progress_tracker:
                    progress_tracker.record_error(chapter_num, str(e))
                raise TranslationError(f"Failed to translate chunk {i + 1}: {e}")

        return "\n\n".join(translated_chunks)

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