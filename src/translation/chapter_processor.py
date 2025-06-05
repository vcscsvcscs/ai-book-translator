"""
Handles chapter processing and translation.
"""

from bs4 import BeautifulSoup
import re
from .chunker import TextChunker
from utils.exceptions import TranslationError


class ChapterProcessor:
    """Processes individual chapters for translation."""

    def __init__(
        self, llm, chunk_size, max_retries, retry_delay, extra_prompts, progress_tracker
    ):
        self.llm = llm
        self.chunker = TextChunker(chunk_size)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts
        self.progress_tracker = progress_tracker

    def process_chapter(self, item, from_lang, to_lang, chapter_num):
        """Process and translate a single chapter."""
        soup = BeautifulSoup(item.content, "html.parser")
        text = self._extract_clean_text(soup)

        chunks = self.chunker.split_text(text)
        total_chunks = len(chunks)

        print(f"  📄 Split into {total_chunks} chunks")

        translated_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"    🔄 Chunk {i + 1}/{total_chunks}...")
            translated_chunks.append(self._translate_chunk(chunk, from_lang, to_lang))

        return {
            "number": chapter_num,
            "title": self._extract_chapter_title(soup, chapter_num),
            "content": "\n\n".join(translated_chunks),
        }

    def _extract_clean_text(self, soup):
        """Extract clean text from HTML."""
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator="\n\n", strip=True)
        return re.sub(r"\s+", " ", text).strip()

    def _translate_chunk(self, text, from_lang, to_lang):
        """Translate a single chunk."""
        prompt = f"Translate the following text from {from_lang} to {to_lang}:\n{text}"
        for _ in range(self.max_retries):
            try:
                return self.llm.complete(prompt).text.strip()
            except Exception as e:
                print(f"⚠️ Error: {e}")
        raise TranslationError("Failed to translate chunk.")
