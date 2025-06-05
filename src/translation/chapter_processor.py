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

    def _translate_chunk(self, text, from_lang, to_lang):
        """Translate a single chunk."""
        prompt = self._create_translation_prompt(text, from_lang, to_lang)
        for _ in range(self.max_retries):
            try:
                return self.llm.complete(prompt).text.strip()
            except Exception as e:
                print(f"⚠️ Error: {e}")
        raise TranslationError("Failed to translate chunk.")
    
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

        return f"{chapter_num}"