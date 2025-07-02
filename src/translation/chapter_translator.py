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
        chunk_size: int = 1000,
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

    def translate_text_directly(
        self,
        text: str,
        from_lang: str,
        to_lang: str,
        chunk_size: int = None
    ) -> str:
        """
        Translate raw text directly without EPUB processing.
        Useful for standalone text translation.
        """
        if chunk_size:
            # Use custom chunk size for this translation
            temp_chunker = TextChunker(chunk_size)
            chunks = temp_chunker.split_text(text)
        else:
            chunks = self.chunker.split_text(text)
        
        translated_chunks = []
        
        for i, chunk in enumerate(chunks):
            print(f"  🔄 Translating chunk {i + 1}/{len(chunks)}...")
            
            try:
                translated_chunk = self._translate_chunk(chunk, from_lang, to_lang)
                translated_chunks.append(translated_chunk)
            except Exception as e:
                raise TranslationError(f"Failed to translate text chunk {i + 1}: {e}")
        
        return "\n\n".join(translated_chunks)

    def translate_chunk_with_context(
        self,
        chunk: str,
        from_lang: str,
        to_lang: str,
        context: str = "",
        preserve_formatting: bool = False
    ) -> str:
        """
        Translate a single chunk with additional context.
        
        Args:
            chunk: Text chunk to translate
            from_lang: Source language
            to_lang: Target language  
            context: Additional context to help with translation
            preserve_formatting: Whether to preserve specific formatting
        """
        try:
            prompt = self._create_translation_prompt(
                chunk, from_lang, to_lang, context, preserve_formatting
            )
            
            for attempt in range(self.max_retries):
                try:
                    response = self.llm.complete(prompt)
                    return response.text.strip()
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        self._handle_translation_error(e, attempt)
                        continue
                    raise
                    
        except Exception as e:
            raise TranslationError(f"Failed to translate chunk with context: {e}")

    def _translate_chunk(self, text: str, from_lang: str, to_lang: str) -> str:
        """Translate a single chunk of text."""
        prompt = self._create_translation_prompt(text, from_lang, to_lang)

        for attempt in range(self.max_retries):
            try:
                response = self.llm.complete(prompt)
                return response.text.strip()

            except Exception as e:
                if attempt < self.max_retries - 1:
                    self._handle_translation_error(e, attempt)
                    continue
                
                # Final attempt failed
                raise TranslationError(
                    f"Translation failed after {self.max_retries} attempts: {e}"
                )

        return ""

    def _handle_translation_error(self, error: Exception, attempt: int):
        """Handle translation errors with appropriate retry logic."""
        error_msg = str(error).lower()

        # Handle rate limiting
        if "rate limit" in error_msg or "quota" in error_msg:
            print(
                f"    ⏳ Rate limit hit. Waiting {self.retry_delay}s... "
                f"(attempt {attempt + 1}/{self.max_retries})"
            )
            time.sleep(self.retry_delay)
        else:
            # Handle other errors with shorter delay
            print(f"    ⚠️  Error on attempt {attempt + 1}: {error}")
            time.sleep(5)  # Short delay for other errors

    def _create_translation_prompt(
        self, 
        text: str, 
        from_lang: str, 
        to_lang: str,
        context: str = "",
        preserve_formatting: bool = False
    ) -> str:
        """Create translation prompt with optional context and formatting instructions."""
        base_prompt = (
            f"You are a professional {from_lang}-to-{to_lang} translator. "
            f"Translate the following text naturally and fluently to {to_lang}. "
        )
        
        # Add extra prompts if provided
        if self.extra_prompts:
            base_prompt += f"{self.extra_prompts}. "
        
        # Add context if provided
        if context:
            base_prompt += f"Context: {context}. "
        
        # Add formatting instructions
        if preserve_formatting:
            base_prompt += (
                "Preserve the original formatting, structure, and paragraph breaks. "
            )
        
        base_prompt += (
            f"Maintain readability and consistency with the source text while making it read naturally in {to_lang}. "
            f"Do not add explanations, comments, or notes - only provide the translation.\n\n"
            f"Text to translate:\n{text}"
        )
        
        return base_prompt

    def get_translation_stats(self) -> dict:
        """Get statistics about the translator configuration."""
        return {
            "chunk_size": self.chunker.chunk_size if hasattr(self.chunker, 'chunk_size') else "unknown",
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "has_extra_prompts": bool(self.extra_prompts),
            "llm_type": type(self.llm).__name__
        }

    def update_settings(
        self,
        chunk_size: int = None,
        max_retries: int = None,
        retry_delay: int = None,
        extra_prompts: str = None
    ):
        """Update translator settings during runtime."""
        if chunk_size is not None:
            self.chunker = TextChunker(chunk_size)
        if max_retries is not None:
            self.max_retries = max_retries
        if retry_delay is not None:
            self.retry_delay = retry_delay
        if extra_prompts is not None:
            self.extra_prompts = extra_prompts