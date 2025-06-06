"""
Improved text chunking and translation logic for ebooks.
"""

import re
from typing import List
from dataclasses import dataclass
from bs4 import BeautifulSoup


@dataclass
class ChunkMetadata:
    """Enhanced metadata for a text chunk."""

    index: int
    character_count: int
    word_count: int
    paragraph_count: int
    has_html: bool
    start_position: int
    end_position: int
    is_dialogue: bool
    chapter_section: str  # beginning, middle, end


class TextChunker:
    """Enhanced text chunker with better book-aware splitting."""

    def __init__(
        self,
        max_chunk_size: int = 8000,  # Reduced for better GPT-4 handling
        overlap_size: int = 300,  # Increased overlap for better context
        preserve_html: bool = True,
        min_chunk_size: int = 500,
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.preserve_html = preserve_html
        self.min_chunk_size = min_chunk_size

        # Enhanced sentence splitting patterns
        self.sentence_endings = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z"\'\'])|'  # Standard sentence endings
            r'(?<=[.!?])\s*\n\s*(?=[A-Z"\'\'])|'  # Sentence endings with newlines
            r'(?<=\.)\s*\n\s*\n\s*(?=[A-Z"\'\'])'  # Paragraph breaks
        )

        # Dialogue patterns for better splitting
        self.dialogue_patterns = re.compile(r'(["\']{1,3}).*?\1')

    def split_text(self, text: str) -> List[str]:
        """Enhanced text splitting with book-aware logic."""
        if not text or not text.strip():
            return []

        # Detect if this is HTML content
        if self.preserve_html and self._has_html_content(text):
            return self._split_html_intelligently(text)
        else:
            return self._split_text_intelligently(text)

    def _split_html_intelligently(self, html_text: str) -> List[str]:
        """Split HTML text with awareness of book structure."""
        # Parse HTML to extract clean text while preserving structure
        soup = BeautifulSoup(html_text, "html.parser")

        # Get paragraphs and major structural elements
        elements = soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6"])

        chunks = []
        current_chunk = ""
        current_html_chunk = ""

        for element in elements:
            element_text = element.get_text(strip=True)
            element_html = str(element)

            # Check if adding this element would exceed chunk size
            if len(current_chunk) + len(element_text) > self.max_chunk_size:
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_html_chunk.strip())

                    # Start new chunk with intelligent overlap
                    overlap_html = self._get_html_overlap(current_html_chunk)
                    current_html_chunk = overlap_html + element_html
                    current_chunk = self._extract_text_from_html(current_html_chunk)
                else:
                    # Current chunk too small, continue building
                    current_html_chunk += "\n" + element_html
                    current_chunk += " " + element_text
            else:
                current_html_chunk += (
                    "\n" + element_html if current_html_chunk else element_html
                )
                current_chunk += " " + element_text if current_chunk else element_text

        # Add final chunk
        if current_html_chunk.strip():
            chunks.append(current_html_chunk.strip())

        return self._validate_and_clean_chunks(chunks)

    def _split_text_intelligently(self, text: str) -> List[str]:
        """Split plain text with book-aware intelligence."""
        # First, split into paragraphs
        paragraphs = re.split(r"\n\s*\n", text)

        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If this paragraph alone is too big, split it by sentences
            if len(paragraph) > self.max_chunk_size:
                # Split the large paragraph by sentences
                para_chunks = self._split_large_paragraph(paragraph)

                # Add completed current chunk if exists
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Add paragraph chunks (except maybe the last one)
                for i, para_chunk in enumerate(para_chunks):
                    if i == len(para_chunks) - 1:
                        # Last chunk - might combine with next content
                        current_chunk = para_chunk
                    else:
                        chunks.append(para_chunk)

            # Check if adding this paragraph exceeds limit
            elif (
                len(current_chunk) + len(paragraph) + 2 > self.max_chunk_size
            ):  # +2 for \n\n
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())

                    # Start new chunk with overlap
                    overlap = self._get_smart_overlap(current_chunk)
                    current_chunk = (
                        overlap + "\n\n" + paragraph if overlap else paragraph
                    )
                else:
                    # Current chunk too small, continue
                    current_chunk += "\n\n" + paragraph if current_chunk else paragraph
            else:
                # Add paragraph to current chunk
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return self._validate_and_clean_chunks(chunks)

    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """Split a large paragraph by sentences with smart breaks."""
        sentences = self._split_into_sentences(paragraph)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Start new chunk with overlap
                    overlap = self._get_sentence_overlap(current_chunk)
                    current_chunk = overlap + " " + sentence if overlap else sentence
                else:
                    # Single sentence is too long - force split by words
                    word_chunks = self._split_by_words(sentence)
                    chunks.extend(word_chunks[:-1])
                    current_chunk = word_chunks[-1] if word_chunks else ""
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Enhanced sentence splitting for books."""
        # Handle dialogue and quoted speech specially
        sentences = []

        # Split by sentence endings but be smart about dialogue
        parts = self.sentence_endings.split(text)

        current_sentence = ""
        for part in parts:
            current_sentence += part

            # Check if we have a complete sentence
            if self._is_complete_sentence(current_sentence):
                sentences.append(current_sentence.strip())
                current_sentence = ""

        # Add any remaining text
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        return [s for s in sentences if s.strip()]

    def _is_complete_sentence(self, text: str) -> bool:
        """Check if text represents a complete sentence."""
        text = text.strip()
        if not text:
            return False

        # Must end with sentence punctuation
        if not text.endswith((".", "!", "?", '"', "'")):
            return False

        # Should not end mid-dialogue
        quote_count = text.count('"') + text.count('"') + text.count('"')
        if quote_count % 2 != 0:  # Odd number of quotes = incomplete dialogue
            return False

        return True

    def _get_smart_overlap(self, text: str) -> str:
        """Get intelligent overlap that preserves context."""
        if len(text) <= self.overlap_size:
            return text

        # Try to find the last complete sentence within overlap size
        overlap_candidate = text[-self.overlap_size :]

        # Find sentence boundaries
        sentences = self._split_into_sentences(overlap_candidate)
        if len(sentences) > 1:
            # Return last complete sentence(s)
            return sentences[-1]

        # Fallback: find last paragraph break
        last_para = overlap_candidate.rfind("\n\n")
        if last_para > self.overlap_size // 3:
            return overlap_candidate[last_para + 2 :].strip()

        # Final fallback: word boundary
        words = overlap_candidate.split()
        return " ".join(words[-min(30, len(words)) :])  # Last ~30 words

    def _get_sentence_overlap(self, text: str) -> str:
        """Get overlap at sentence level."""
        sentences = self._split_into_sentences(text)
        if not sentences:
            return ""

        # Return last sentence if it fits in overlap size
        last_sentence = sentences[-1]
        if len(last_sentence) <= self.overlap_size:
            return last_sentence

        # Otherwise return last few words
        words = last_sentence.split()
        return " ".join(words[-min(20, len(words)) :])

    def _split_by_words(self, text: str) -> List[str]:
        """Emergency word-level splitting for very long sentences."""
        words = text.split()
        chunks = []
        current_chunk = ""

        for word in words:
            if len(current_chunk) + len(word) + 1 > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = word
                else:
                    # Single word is too long - just add it
                    chunks.append(word)
            else:
                current_chunk += " " + word if current_chunk else word

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _has_html_content(self, text: str) -> bool:
        """Enhanced HTML detection."""
        return bool(re.search(r"<(?:p|div|span|h[1-6]|br|em|strong|i|b)[^>]*>", text))

    def _extract_text_from_html(self, html: str) -> str:
        """Extract text from HTML for length calculations."""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(strip=True)

    def _get_html_overlap(self, html_chunk: str) -> str:
        """Get overlap from HTML chunk preserving structure."""
        soup = BeautifulSoup(html_chunk, "html.parser")
        elements = soup.find_all(["p", "div"])

        if not elements:
            return ""

        # Get last element as overlap
        last_element = elements[-1]
        return str(last_element)

    def _validate_and_clean_chunks(self, chunks: List[str]) -> List[str]:
        """Validate and clean chunks with better error handling."""
        cleaned_chunks: List[str] = []
        buffer = ""

        i = 0
        while i < len(chunks):
            chunk = chunks[i].strip()
            if not chunk:
                i += 1
                continue

            # If chunk is too small and not the last chunk, combine with the next one
            if len(chunk) < self.min_chunk_size and i < len(chunks) - 1:
                buffer += chunk + "\n\n"
                i += 1
                continue

            # Prepend any buffered content from a previous small chunk
            if buffer:
                chunk = buffer + chunk
                buffer = ""

            cleaned_chunks.append(chunk)
            i += 1

        # Add any remaining buffer as a final chunk if non-empty
        if buffer:
            cleaned_chunks.append(buffer.strip())

        return cleaned_chunks
