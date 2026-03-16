"""
Chapter translation functionality with chunk-level caching support.
"""

import os
import re
import time
from bs4 import BeautifulSoup
from llama_index.core.llms import LLM

from utils.text_utils import extract_clean_text
from .chunker import TextChunker
from utils.exceptions import TranslationError


class ChapterTranslator:
    """Handles translation of individual chapters with chunk-level caching."""

    def __init__(
        self, 
        llm: LLM, 
        chunk_size: int = 1000,
        max_retries: int = 3,
        retry_delay: int = 180,
        extra_prompts: str = "",
        chapter_cache=None
    ):
        self.llm = llm
        self.chunker = TextChunker(chunk_size)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts
        self.chapter_cache = chapter_cache
        self.filtered_chunks = []  # Store filtered chunks to avoid reprocessing

    def translate_chapter(
        self, 
        item, 
        from_lang: str, 
        to_lang: str, 
        chapter_num: int, 
        start_chunk: int = 0,
        progress_tracker=None
    ) -> str:
        """Translate a single chapter with chunk-level caching."""
        soup = BeautifulSoup(item.content, "html.parser")

        # Extract clean text content, preserving structure
        text = extract_clean_text(soup)

        chunks = self.chunker.split_text(text)
        total_chunks = len(chunks)

        print(f"  📄 Split into {total_chunks} chunks")

        # Initialize progress tracking for this chapter
        if progress_tracker:
            progress_tracker.start_chapter(chapter_num, total_chunks)

        # Check for cached chunks and build partial content
        cached_content = ""
        cached_chunks_count = 0
        
        if self.chapter_cache:
            cached_content, cached_chunks_count = self.chapter_cache.build_chapter_from_chunks(
                chapter_num, chunks
            )
            
            if cached_chunks_count > 0:
                print(f"  📦 Found {cached_chunks_count}/{total_chunks} cached chunks")
                
                # Update start_chunk to skip cached chunks
                start_chunk = max(start_chunk, cached_chunks_count)

        translated_chunks = []
        
        # Add cached content if we have it
        if cached_content:
            translated_chunks.append(cached_content)

        # Translate remaining chunks
        for i, chunk in enumerate(chunks[start_chunk:], start=start_chunk):
            print(f"    🔄 Chunk {i + 1}/{total_chunks}...")

            try:
                # Check if this specific chunk is cached
                if self.chapter_cache:
                    cached_chunk = self.chapter_cache.get_cached_chunk(chapter_num, chunk)
                    if cached_chunk:
                        print(f"    📦 Using cached chunk {i + 1}")
                        translated_chunks.append(cached_chunk)
                        
                        # Update progress
                        if progress_tracker:
                            progress_tracker.update_progress(chapter_num, i + 1, total_chunks)
                        continue

                # Translate the chunk
                translated_chunk = self._translate_chunk(chunk, from_lang, to_lang, (chapter_num, self.chapter_cache._get_chunk_hash(chunk)))
                translated_chunks.append(translated_chunk)
                
                # Cache the translated chunk
                if self.chapter_cache:
                    self.chapter_cache.save_chunk(chapter_num, chunk, translated_chunk)

                # Update progress
                if progress_tracker:
                    progress_tracker.update_progress(chapter_num, i + 1, total_chunks)

            except Exception as e:
                # Record error in progress tracker
                if progress_tracker:
                    progress_tracker.record_error(chapter_num, str(e))
                raise TranslationError(f"Failed to translate chunk {i + 1}: {e}")

        # If we had cached content, we need to merge it properly
        if cached_content and len(translated_chunks) > 1:
            # Remove the cached content from the beginning and merge all chunks
            return "\n\n".join(translated_chunks[1:])
        else:
            return "\n\n".join(translated_chunks)

    def translate_text_directly(
        self,
        text: str,
        from_lang: str,
        to_lang: str,
        chunk_size: int = None,
        chapter_num: int = None
    ) -> str:
        """
        Translate raw text directly without EPUB processing.
        Optionally use chunk caching if chapter_num is provided.
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
                # Check cache if chapter_num provided
                if self.chapter_cache and chapter_num is not None:
                    cached_chunk = self.chapter_cache.get_cached_chunk(chapter_num, chunk)
                    if cached_chunk:
                        print(f"    📦 Using cached chunk {i + 1}")
                        translated_chunks.append(cached_chunk)
                        continue
                
                # Translate the chunk
                translated_chunk = self._translate_chunk(chunk, from_lang, to_lang, (chapter_num, self.chapter_cache._get_chunk_hash(chunk)))
                translated_chunks.append(translated_chunk)
                
                # Cache if chapter_num provided
                if self.chapter_cache and chapter_num is not None:
                    self.chapter_cache.save_chunk(chapter_num, chunk, translated_chunk)
                    
            except Exception as e:
                raise TranslationError(f"Failed to translate text chunk {i + 1}: {e}")
        
        return "\n\n".join(translated_chunks)

    def translate_chunk_with_context(
        self,
        chunk: str,
        from_lang: str,
        to_lang: str,
        context: str = "",
        preserve_formatting: bool = False,
        chapter_num: int = None
    ) -> str:
        """
        Translate a single chunk with additional context.
        Optionally use chunk caching if chapter_num is provided.
        """
        try:
            # Check cache first if chapter_num provided
            if self.chapter_cache and chapter_num is not None:
                cached_chunk = self.chapter_cache.get_cached_chunk(chapter_num, chunk)
                if cached_chunk:
                    print("    📦 Using cached chunk translation")
                    return cached_chunk
            
            prompt = self._create_translation_prompt(
                chunk, from_lang, to_lang, context, preserve_formatting
            )
            
            for attempt in range(self.max_retries):
                try:
                    response = self.llm.complete(prompt)
                    translated_chunk = response.text.strip()
                    
                    # Cache the result if chapter_num provided
                    if self.chapter_cache and chapter_num is not None:
                        self.chapter_cache.save_chunk(chapter_num, chunk, translated_chunk)
                    
                    return translated_chunk
                    
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        self._handle_translation_error(e, attempt)
                        continue
                    raise
                    
        except Exception as e:
            raise TranslationError(f"Failed to translate chunk with context: {e}")

    def get_chapter_translation_progress(self, chapter_num: int, total_chunks: int) -> dict:
        """Get translation progress for a specific chapter."""
        if not self.chapter_cache:
            return {
                'chapter_num': chapter_num,
                'completed_chunks': 0,
                'total_chunks': total_chunks,
                'progress_percentage': 0.0,
                'is_complete': False
            }
        
        return self.chapter_cache.get_chapter_progress(chapter_num, total_chunks)

    def estimate_remaining_chunks(self, chapter_num: int, chunks: list) -> int:
        """Estimate how many chunks still need to be translated."""
        if not self.chapter_cache:
            return len(chunks)
        
        remaining = 0
        for chunk in chunks:
            if not self.chapter_cache.is_chunk_cached(chapter_num, chunk):
                remaining += 1
        
        return remaining

    def _translate_chunk(self, text: str, from_lang: str, to_lang: str, chunk_id: tuple[int,str]) -> str:
        """Translate a single chunk of text."""
        prompt = self._create_translation_prompt(text, from_lang, to_lang)

        for attempt in range(self.max_retries):
            try:
                response = self.llm.complete(prompt)
                translated_text = self._extract_translation(
                    response.text, text, to_lang
                )
                # Accept short identical output (names, numbers, terms same in both languages)
                invalid = (
                    not translated_text
                    or (translated_text == text and len(text) > 50)
                )
                if invalid:
                    if os.environ.get("TRANSLATION_DEBUG"):
                        raw_preview = (response.text or "")[:400].replace("\n", " ")
                        print(f"    [DEBUG] raw response (first 400 chars): {raw_preview!r}")
                        print(f"    [DEBUG] extracted: {translated_text!r}")
                    if attempt < self.max_retries - 1:
                        print(f"    ⚠️  Empty or invalid translation on attempt {attempt + 1}, retrying...")
                        continue
                    else:
                        print(f"    ⚠️  Failed to get valid translation after {self.max_retries} attempts, using original text")
                        return text
                
                return translated_text

            except Exception as e:
                if str(e).lower().__contains__("filter"):
                    print("    ⚠️  Translation blocked by filter. Leaving chunk as it is, translate manually.")
                    self.filtered_chunks.append(chunk_id)  # Mark this chunk as filtered
                    return text  # Return original text if blocked by filter

                if attempt < self.max_retries - 1:
                    self._handle_translation_error(e, attempt)
                    continue
                
                # Final attempt failed
                raise TranslationError(
                    f"Translation failed after {self.max_retries} attempts: {e}"
                )

        return ""

    def _extract_translation(self, raw_response: str, original_text: str, to_lang: str) -> str:
        """Extract translation from model response; strip thinking blocks and markers."""
        if not (raw_response or "").strip():
            return ""
        out = raw_response.strip()
        out = self._strip_thinking_blocks(out)
        # Prefer content after explicit translation headers
        if f"Translation in {to_lang}:" in out:
            out = out.split(f"Translation in {to_lang}:")[-1].strip()
        elif "Translation:" in out:
            out = out.split("Translation:")[-1].strip()
        elif out.lower().startswith((f"{to_lang}:", f"{to_lang} ")):
            out = out.split(":", 1)[-1].strip() if ":" in out else out
        # Remove echoed source text only when the part after is non-empty
        if original_text in out:
            after = out.split(original_text, 1)[-1].strip()
            if after:
                out = after
        out = out.replace("<|im_end|>", "").replace("<|im_start|>", "").strip()
        # Strip common assistant/chat prefixes (Ollama sometimes adds these)
        for prefix in ("Assistant:", "assistant:", "A:", "answer:", "Answer:"):
            if out.lower().startswith(prefix.lower()):
                out = out[len(prefix):].strip()
                break
        # Instruct mode: no header; if we stripped to empty, use full reply
        if not out and raw_response.strip():
            out = self._strip_thinking_blocks(raw_response.strip())
            out = out.replace("<|im_end|>", "").replace("<|im_start|>", "").strip()
        # Unwrap markdown code block (e.g. ```hu\n...\n```) when present
        if re.match(r"^```\w*\s*\n", out) and out.rstrip().endswith("```"):
            match = re.search(r"```(?:\w*)\s*\n(.*?)```", out, re.DOTALL)
            if match:
                out = match.group(1).strip()
        elif not out and raw_response.strip():
            match = re.search(r"```(?:\w*)\s*\n(.*?)```", raw_response.strip(), re.DOTALL)
            if match:
                out = match.group(1).strip()
        # Last resort: use full response minus thinking (in case all above left empty)
        if not out:
            out = self._strip_thinking_blocks(raw_response.strip())
            out = out.replace("<|im_end|>", "").replace("<|im_start|>", "").strip()
        return out

    def _strip_thinking_blocks(self, raw: str) -> str:
        """Remove thinking/reasoning blocks (e.g. Qwen <think>...) so only the final answer remains."""
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

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
            f"Use correct grammar and natural {to_lang} sentence structure. "
            f"IMPORTANT: You must translate the text exactly, do not continue the story, do not add new content, do not summarize. "
            f"Only provide the complete translation of the given text in {to_lang}.\n\n"
            f"Text to translate:\n{text}\n\n"
            f"Translation in {to_lang}:"
        )
        
        return base_prompt

    def get_translation_stats(self) -> dict:
        """Get statistics about the translator configuration."""
        stats = {
            "chunk_size": self.chunker.chunk_size if hasattr(self.chunker, 'chunk_size') else "unknown",
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "has_extra_prompts": bool(self.extra_prompts),
            "llm_type": type(self.llm).__name__,
            "has_cache": self.chapter_cache is not None
        }
        
        if self.chapter_cache:
            stats["cache_stats"] = self.chapter_cache.get_cache_stats()
        
        return stats

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