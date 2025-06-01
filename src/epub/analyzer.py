"""
Chapter analysis functionality for EPUB books.
"""

import re
from collections import Counter
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .reader import EPUBReader, EPUBChapter
from ..utils.text_utils import clean_text


@dataclass
class ChapterStats:
    """Statistics for a single chapter."""

    chapter_number: int
    title: str
    character_count: int
    word_count: int
    sentence_count: int
    paragraph_count: int
    unique_words: int
    avg_words_per_sentence: float
    avg_sentences_per_paragraph: float
    readability_score: Optional[float] = None
    complexity_score: Optional[float] = None


@dataclass
class BookStats:
    """Overall statistics for the entire book."""

    total_chapters: int
    total_characters: int
    total_words: int
    total_sentences: int
    total_paragraphs: int
    unique_words: int
    avg_chapter_length: float
    avg_words_per_chapter: float
    avg_sentences_per_chapter: float
    most_common_words: List[Tuple[str, int]]
    chapter_stats: List[ChapterStats]


class EpubAnalyzer:
    """Analyzes EPUB content for various statistics and insights."""

    def __init__(self, reader: EPUBReader):
        """
        Initialize analyzer with an EPUB reader.

        Args:
            reader: EPUBReader instance
        """
        self.reader = reader
        self._stop_words = {
            "the",
            "and",
            "a",
            "an",
            "as",
            "are",
            "was",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "can",
            "may",
            "might",
            "must",
            "shall",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "by",
            "from",
            "up",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "among",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
            "my",
            "your",
            "his",
            "its",
            "our",
            "their",
            "this",
            "that",
            "these",
            "those",
            "is",
            "am",
            "at",
            "but",
            "or",
            "if",
            "not",
            "no",
            "yes",
            "so",
            "what",
            "when",
            "where",
            "why",
            "how",
        }

    def analyze_chapter(self, chapter: EPUBChapter) -> ChapterStats:
        """
        Analyze a single chapter.

        Args:
            chapter: EPUBChapter to analyze

        Returns:
            ChapterStats object with analysis results
        """
        text = chapter.text_content
        clean_text_content = clean_text(text)

        # Basic counts
        character_count = len(chapter.content)
        word_count = len(clean_text_content.split())
        sentence_count = self._count_sentences(clean_text_content)
        paragraph_count = self._count_paragraphs(text)
        unique_words = len(
            set(word.lower() for word in clean_text_content.split() if word.isalpha())
        )

        # Averages
        avg_words_per_sentence = word_count / max(sentence_count, 1)
        avg_sentences_per_paragraph = sentence_count / max(paragraph_count, 1)

        # Advanced metrics
        readability_score = self._calculate_readability_score(
            clean_text_content, word_count, sentence_count
        )
        complexity_score = self._calculate_complexity_score(clean_text_content)

        return ChapterStats(
            chapter_number=chapter.chapter_number,
            title=chapter.title,
            character_count=character_count,
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            unique_words=unique_words,
            avg_words_per_sentence=avg_words_per_sentence,
            avg_sentences_per_paragraph=avg_sentences_per_paragraph,
            readability_score=readability_score,
            complexity_score=complexity_score,
        )

    def analyze_book(self) -> BookStats:
        """
        Analyze the entire book.

        Returns:
            BookStats object with comprehensive analysis
        """
        chapters = self.reader.get_chapters()
        chapter_stats = []
        all_words = []

        # Analyze each chapter
        for chapter in chapters:
            stats = self.analyze_chapter(chapter)
            chapter_stats.append(stats)

            # Collect words for overall analysis
            text = clean_text(chapter.text_content)
            words = [word.lower() for word in text.split() if word.isalpha()]
            all_words.extend(words)

        # Calculate overall statistics
        total_chapters = len(chapters)
        total_characters = sum(stats.character_count for stats in chapter_stats)
        total_words = sum(stats.word_count for stats in chapter_stats)
        total_sentences = sum(stats.sentence_count for stats in chapter_stats)
        total_paragraphs = sum(stats.paragraph_count for stats in chapter_stats)
        unique_words = len(set(all_words))

        # Averages
        avg_chapter_length = total_characters / max(total_chapters, 1)
        avg_words_per_chapter = total_words / max(total_chapters, 1)
        avg_sentences_per_chapter = total_sentences / max(total_chapters, 1)

        # Most common words (excluding stop words)
        filtered_words = [word for word in all_words if word not in self._stop_words]
        most_common_words = Counter(filtered_words).most_common(20)

        return BookStats(
            total_chapters=total_chapters,
            total_characters=total_characters,
            total_words=total_words,
            total_sentences=total_sentences,
            total_paragraphs=total_paragraphs,
            unique_words=unique_words,
            avg_chapter_length=avg_chapter_length,
            avg_words_per_chapter=avg_words_per_chapter,
            avg_sentences_per_chapter=avg_sentences_per_chapter,
            most_common_words=most_common_words,
            chapter_stats=chapter_stats,
        )

    def _count_sentences(self, text: str) -> int:
        """
        Count the number of sentences in the text.

        Args:
            text: Text to analyze

        Returns:
            Number of sentences
        """
        # Simple heuristic: split by '.', '!', '?'
        sentences = re.split(r"[.!?]+", text)
        return len([s for s in sentences if s.strip()])

    def _count_paragraphs(self, text: str) -> int:
        """
        Count the number of paragraphs in the text.
        Args:
            text: Text to analyze
        Returns:
            Number of paragraphs
        """
        # Split by double newlines or HTML paragraph tags
        paragraphs = re.split(r"\n\s*\n|<p.*?>.*?</p>", text, flags=re.DOTALL)
        return len([p for p in paragraphs if p.strip()])

    def _calculate_readability_score(
        self, text: str, word_count: int, sentence_count: int
    ) -> Optional[float]:
        """
        Calculate a basic readability score using the Flesch-Kincaid formula.

        Args:
            text: Text to analyze
            word_count: Total number of words
            sentence_count: Total number of sentences

        Returns:
            Readability score (higher is easier to read)
        """
        if sentence_count == 0 or word_count == 0:
            return None

        # Flesch-Kincaid Grade Level formula
        score = (
            206.835
            - (1.015 * (word_count / sentence_count))
            - (84.6 * (len(text.split()) / sentence_count))
        )
        return score

    def _calculate_complexity_score(self, text: str) -> Optional[float]:
        """
        Calculate a basic complexity score based on vocabulary diversity.

        Args:
            text: Text to analyze

        Returns:
            Complexity score (higher is more complex)
        """
        words = [word.lower() for word in text.split() if word.isalpha()]
        if not words:
            return None

        unique_word_count = len(set(words))
        total_word_count = len(words)

        # Simple complexity metric: unique words / total words
        complexity_score = unique_word_count / total_word_count
        return complexity_score

    def show_chapters(self, detailed: bool = False) -> None:
        """
        Print a summary or detailed info for each chapter in the book.

        Args:
            detailed: If True, show detailed info for each chapter.
        """
        chapters = self.reader.get_chapters()
        total_characters = 0
        total_chapters = len(chapters)

        for idx, chapter in enumerate(chapters, start=1):
            chapter_length = len(chapter.content)
            total_characters += chapter_length
            print(
                f"▶️  Chapter {idx}/{total_chapters} ({chapter_length} characters): {chapter.title}"
            )

            if detailed:
                preview = chapter.get_preview(250)
                print(preview)
                print("-" * 40)

        print(f"Total characters in the book: {total_characters}")
