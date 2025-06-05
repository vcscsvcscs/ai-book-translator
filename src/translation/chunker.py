"""
Text chunking logic for breaking down large texts into manageable pieces.
"""

import re
from typing import List
from dataclasses import dataclass


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""

    index: int
    character_count: int
    sentence_count: int
    has_html: bool
    start_position: int
    end_position: int


class TextChunker:
    """Handles text chunking with various strategies."""

    def __init__(
        self,
        max_chunk_size: int = 20000,
        overlap_size: int = 200,
        preserve_html: bool = True,
        min_chunk_size: int = 1000,
    ):
        """
        Initialize the text chunker.

        Args:
            max_chunk_size: Maximum size of each chunk in characters
            overlap_size: Number of characters to overlap between chunks
            preserve_html: Whether to preserve HTML structure when chunking
            min_chunk_size: Minimum size of a chunk (prevents very small chunks)
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.preserve_html = preserve_html
        self.min_chunk_size = min_chunk_size

    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks using the most appropriate strategy.

        Args:
            text: The text to split

        Returns:
            List of text chunks
        """
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)

        if not text or not text.strip():
            logger.debug("Input text is empty or whitespace only.")
            return []

        # Choose strategy based on content
        if self.preserve_html and self._has_html_content(text):
            return self._split_html_by_sentences(text)
        else:
            return self._split_by_sentences(text)

    def split_with_metadata(self, text: str) -> List[tuple[str, ChunkMetadata]]:
        """
        Split text into chunks and return with metadata.

        Args:
            text: The text to split

        Returns:
            List of tuples containing (chunk_text, metadata)
        """
        chunks = self.split_text(text)
        result = []
        current_position = 0

        for i, chunk in enumerate(chunks):
            metadata = ChunkMetadata(
                index=i,
                character_count=len(chunk),
                sentence_count=self._count_sentences(chunk),
                has_html=self._has_html_content(chunk),
                start_position=current_position,
                end_position=current_position + len(chunk),
            )
            result.append((chunk, metadata))
            current_position += len(chunk) - self.overlap_size

        return result

    def _split_html_by_sentences(self, html_text: str) -> List[str]:
        """
        Split HTML text by sentences while preserving HTML structure.

        Args:
            html_text: HTML text to split

        Returns:
            List of HTML chunks
        """
        # Split by sentence endings, but be careful with HTML tags
        sentences = self._split_sentences_preserve_html(html_text)

        chunks = []
        logger.debug(f"Splitting text into chunks. Text length: {len(text)}")
        current_chunk = ""

        for sentence in sentences:
            # Check if adding this sentence would exceed the limit
            if len(current_chunk) + len(sentence) > self.max_chunk_size:
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    # Start new chunk with overlap if possible
                    current_chunk = self._get_overlap_text(current_chunk) + sentence
                else:
                    # Current chunk is too small, continue building
                    current_chunk += " " + sentence if current_chunk else sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        # Add the final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return self._clean_chunks(chunks)

    def _split_by_sentences(self, text: str) -> List[str]:
        """
        Split plain text by sentences.

        Args:
            text: Plain text to split

        Returns:
            List of text chunks
        """
        sentences = self._split_sentences(text)
        logger.debug(f"Split text into {len(sentences)} sentences.")

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.max_chunk_size:
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = self._get_overlap_text(current_chunk) + sentence
                else:
                    current_chunk += " " + sentence if current_chunk else sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        logger.debug(f"Created {len(chunks)} chunks. Chunk sizes: {[len(chunk) for chunk in chunks]}")
        logger.debug(f"Final chunks: {chunks}")
        return chunks

    def _split_sentences_preserve_html(self, html_text: str) -> List[str]:
        """
        Split sentences while preserving HTML tags.

        Args:
            html_text: HTML text to split

        Returns:
            List of sentences with HTML preserved
        """
        # More sophisticated sentence splitting that considers HTML
        # Split on sentence endings but not inside HTML tags
        pattern = r"(?<=[.!?])\s+(?![^<]*>)"
        sentences = re.split(pattern, html_text)

        # Clean up empty sentences
        return [s.strip() for s in sentences if s.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split plain text into sentences.

        Args:
            text: Plain text to split

        Returns:
            List of sentences
        """
        # Basic sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_overlap_text(self, text: str) -> str:
        """
        Get overlap text from the end of a chunk.

        Args:
            text: The text to get overlap from

        Returns:
            Overlap text
        """
        if len(text) <= self.overlap_size:
            return text

        # Try to find a good breaking point (end of sentence)
        overlap_candidate = text[-self.overlap_size:]
        logger.debug(f"Overlap candidate: {overlap_candidate}")
        sentence_end = overlap_candidate.rfind(".")

        if sentence_end > self.overlap_size // 2:
            return overlap_candidate[sentence_end + 1 :].strip()
        else:
            return overlap_candidate

    def _has_html_content(self, text: str) -> bool:
        """Check if text contains HTML tags."""
        return bool(re.search(r"<[^>]+>", text))

    def _count_sentences(self, text: str) -> int:
        """Count sentences in text."""
        sentences = re.split(r"[.!?]+", text)
        return len([s for s in sentences if s.strip()])

    def _clean_chunks(self, chunks: List[str]) -> List[str]:
        """
        Clean and validate chunks.

        Args:
            chunks: List of chunks to clean

        Returns:
            Cleaned chunks
        """
        cleaned = []

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            # Ensure chunk ends properly
            if self.preserve_html and self._has_html_content(chunk):
                # For HTML, just ensure it's not empty
                if chunk:
                    cleaned.append(chunk)
            else:
                # For plain text, ensure proper sentence ending
                if not chunk.endswith((".", "!", "?")):
                    chunk += "."
                cleaned.append(chunk)

        return cleaned

    def estimate_chunks(self, text: str) -> int:
        """
        Estimate the number of chunks that will be created.

        Args:
            text: Text to estimate chunks for

        Returns:
            Estimated number of chunks
        """
        if not text:
            return 0

        text_length = len(text)
        if text_length <= self.max_chunk_size:
            return 1

        # Account for overlap
        effective_chunk_size = self.max_chunk_size - self.overlap_size
        return max(1, (text_length + effective_chunk_size - 1) // effective_chunk_size)

    def validate_chunks(self, chunks: List[str]) -> List[str]:
        """
        Validate and report issues with chunks.

        Args:
            chunks: List of chunks to validate

        Returns:
            List of validation warnings
        """
        warnings = []

        for i, chunk in enumerate(chunks):
            if len(chunk) > self.max_chunk_size:
                warnings.append(
                    f"Chunk {i + 1} exceeds maximum size: {len(chunk)} > {self.max_chunk_size}"
                )

            if len(chunk) < self.min_chunk_size:
                warnings.append(
                    f"Chunk {i + 1} is below minimum size: {len(chunk)} < {self.min_chunk_size}"
                )

            if self.preserve_html and self._has_html_content(chunk):
                # Basic HTML validation
                open_tags = len(re.findall(r"<(?!/)([^>]+)>", chunk))
                close_tags = len(re.findall(r"</([^>]+)>", chunk))
                if open_tags != close_tags:
                    warnings.append(f"Chunk {i + 1} may have unbalanced HTML tags")

        return warnings
