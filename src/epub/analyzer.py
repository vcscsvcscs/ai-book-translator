"""
Enhanced chapter analysis functionality for EPUB books with translation cost estimation.
"""

import re
import tiktoken
from collections import Counter
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from .reader import EPUBReader, EPUBChapter
from utils.text_utils import clean_text
from translation.language_expansion import get_expansion_factor, get_language_name


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
    token_count: int
    avg_words_per_sentence: float
    avg_sentences_per_paragraph: float
    readability_score: Optional[float] = None
    complexity_score: Optional[float] = None


@dataclass
class TranslationEstimate:
    """Translation cost and token estimates."""

    source_language: str
    target_language: str
    source_lang_name: str
    target_lang_name: str
    expansion_factor: float
    input_tokens: int
    predicted_output_tokens: int
    total_tokens: int
    model: str
    input_cost: float
    output_cost: float
    total_cost: float


@dataclass
class BookStats:
    """Overall statistics for the entire book."""

    total_chapters: int
    total_characters: int
    total_words: int
    total_sentences: int
    total_paragraphs: int
    unique_words: int
    total_tokens: int
    avg_chapter_length: float
    avg_words_per_chapter: float
    avg_sentences_per_chapter: float
    avg_tokens_per_chapter: float
    most_common_words: List[Tuple[str, int]]
    chapter_stats: List[ChapterStats]
    translation_estimate: Optional[TranslationEstimate] = None


class EnhancedEpubAnalyzer:
    """Enhanced analyzer for EPUB content with tokenization and translation cost estimation."""

    # Model pricing (per million tokens)
    MODEL_PRICING = {
        "o3": {"input": 10.00, "output": 40.00},
        "o1": {"input": 15.00, "output": 60.00},
        "o4-mini": {"input": 1.10, "output": 4.40},
        "GPT-4.1-2025-04-14": {"input": 2.00, "output": 8.00},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3.5-haiku": {"input": 1.00, "output": 5.00},
    }

    def __init__(self, reader: EPUBReader, model: str = "gpt-4o"):
        """
        Initialize enhanced analyzer with an EPUB reader.

        Args:
            reader: EPUBReader instance
            model: Model name for tokenization (default: gpt-4o)
        """
        self.reader = reader
        self.model = model

        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to gpt-4o if model not found
            print(f"⚠️  Model {model} not found, using gpt-4o tokenizer")
            self.tokenizer = tiktoken.encoding_for_model("gpt-4o")

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
        Analyze a single chapter including token count.

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

        # Token count
        token_count = len(self.tokenizer.encode(clean_text_content))

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
            token_count=token_count,
            avg_words_per_sentence=avg_words_per_sentence,
            avg_sentences_per_paragraph=avg_sentences_per_paragraph,
            readability_score=readability_score,
            complexity_score=complexity_score,
        )

    def analyze_book(
        self, source_language: str = "en", target_language: str | None = None
    ) -> BookStats:
        """
        Analyze the entire book with optional translation cost estimation.

        Args:
            source_language: Source language code (default: "en")
            target_language: Target language code for translation estimation

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
        total_tokens = sum(stats.token_count for stats in chapter_stats)
        unique_words = len(set(all_words))

        # Averages
        avg_chapter_length = total_characters / max(total_chapters, 1)
        avg_words_per_chapter = total_words / max(total_chapters, 1)
        avg_sentences_per_chapter = total_sentences / max(total_chapters, 1)
        avg_tokens_per_chapter = total_tokens / max(total_chapters, 1)

        # Most common words (excluding stop words)
        filtered_words = [word for word in all_words if word not in self._stop_words]
        most_common_words = Counter(filtered_words).most_common(20)

        # Translation estimation
        translation_estimate = None
        if target_language:
            translation_estimate = self._calculate_translation_estimate(
                source_language, target_language, total_tokens
            )

        return BookStats(
            total_chapters=total_chapters,
            total_characters=total_characters,
            total_words=total_words,
            total_sentences=total_sentences,
            total_paragraphs=total_paragraphs,
            unique_words=unique_words,
            total_tokens=total_tokens,
            avg_chapter_length=avg_chapter_length,
            avg_words_per_chapter=avg_words_per_chapter,
            avg_sentences_per_chapter=avg_sentences_per_chapter,
            avg_tokens_per_chapter=avg_tokens_per_chapter,
            most_common_words=most_common_words,
            chapter_stats=chapter_stats,
            translation_estimate=translation_estimate,
        )

    def _calculate_translation_estimate(
        self, source_language: str, target_language: str, input_tokens: int
    ) -> TranslationEstimate:
        """Calculate translation cost and token estimates."""
        expansion_factor = get_expansion_factor(source_language, target_language)
        predicted_output_tokens = int(input_tokens * expansion_factor)
        total_tokens = input_tokens + predicted_output_tokens

        # Calculate pricing
        if self.model in self.MODEL_PRICING:
            pricing = self.MODEL_PRICING[self.model]
            input_cost = (input_tokens / 1_000_000) * pricing["input"]
            output_cost = (predicted_output_tokens / 1_000_000) * pricing["output"]
            total_cost = input_cost + output_cost
        else:
            input_cost = output_cost = total_cost = 0.0

        return TranslationEstimate(
            source_language=source_language,
            target_language=target_language,
            source_lang_name=get_language_name(source_language),
            target_lang_name=get_language_name(target_language),
            expansion_factor=expansion_factor,
            input_tokens=input_tokens,
            predicted_output_tokens=predicted_output_tokens,
            total_tokens=total_tokens,
            model=self.model,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
        )

    def show_chapters(
        self,
        detailed: bool = False,
        source_language: str = "en",
        target_language: str | None = None,
    ) -> None:
        """
        Print chapter analysis with optional translation cost estimation.

        Args:
            detailed: If True, show detailed info for each chapter
            source_language: Source language code (default: "en")
            target_language: Target language code for translation estimation
        """
        chapters = self.reader.get_chapters()
        total_characters = 0
        total_tokens = 0
        total_chapters = len(chapters)

        print("📚 CHAPTER ANALYSIS")
        print("=" * 60)

        for idx, chapter in enumerate(chapters, start=1):
            stats = self.analyze_chapter(chapter)
            total_characters += stats.character_count
            total_tokens += stats.token_count

            print(
                f"▶️  Chapter {idx}/{total_chapters} "
                f"({stats.character_count:,} chars, {stats.token_count:,} tokens): {stats.title}"
            )

            if detailed:
                preview = chapter.get_preview(250)
                cleaned_preview = re.sub(r"\n{2,}", "\n", preview)
                print(cleaned_preview)
                print(
                    f"📊 Words: {stats.word_count:,} | Sentences: {stats.sentence_count:,} | "
                    f"Paragraphs: {stats.paragraph_count:,}"
                )
                if stats.readability_score:
                    print(
                        f"📖 Readability: {stats.readability_score:.1f} | "
                        f"Complexity: {stats.complexity_score:.3f}"
                    )
                print("-" * 40)

        # Summary
        print("\n" + "=" * 60)
        print("📊 BOOK ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Total chapters: {total_chapters}")
        print(f"Total characters: {total_characters:,}")
        print(f"Total tokens ({self.model}): {total_tokens:,}")
        print(
            f"Average tokens per chapter: {total_tokens / max(total_chapters, 1):.0f}"
        )

        # Translation estimation
        if target_language:
            estimate = self._calculate_translation_estimate(
                source_language, target_language, total_tokens
            )

            print(
                f"\n🌐 TRANSLATION PREDICTION ({estimate.source_lang_name} → {estimate.target_lang_name}):"
            )
            print(f"Expansion factor: {estimate.expansion_factor:.2f}x")
            print(f"Predicted output tokens: {estimate.predicted_output_tokens:,}")
            print(f"Total tokens (input + output): {estimate.total_tokens:,}")

            if self.model in self.MODEL_PRICING:
                print(f"\n💰 ESTIMATED COST ({self.model}):")
                pricing = self.MODEL_PRICING[self.model]
                print(
                    f"Input cost: ${estimate.input_cost:.4f} "
                    f"({estimate.input_tokens:,} tokens × ${pricing['input']}/1M)"
                )
                print(
                    f"Output cost: ${estimate.output_cost:.4f} "
                    f"({estimate.predicted_output_tokens:,} tokens × ${pricing['output']}/1M)"
                )
                print(f"Total estimated cost: ${estimate.total_cost:.4f}")
            else:
                print(f"⚠️  Pricing not available for model: {self.model}")

        print("=" * 60)

    def get_translation_cost_breakdown(
        self, source_language: str = "en", target_language: str = "es"
    ) -> Dict:
        """
        Get detailed translation cost breakdown by chapter.

        Args:
            source_language: Source language code
            target_language: Target language code

        Returns:
            Dictionary with cost breakdown
        """
        chapters = self.reader.get_chapters()
        chapter_costs = []

        expansion_factor = get_expansion_factor(source_language, target_language)

        for chapter in chapters:
            stats = self.analyze_chapter(chapter)
            predicted_output = int(stats.token_count * expansion_factor)

            if self.model in self.MODEL_PRICING:
                pricing = self.MODEL_PRICING[self.model]
                input_cost = (stats.token_count / 1_000_000) * pricing["input"]
                output_cost = (predicted_output / 1_000_000) * pricing["output"]
                total_cost = input_cost + output_cost
            else:
                input_cost = output_cost = total_cost = 0.0

            chapter_costs.append(
                {
                    "chapter": stats.chapter_number,
                    "title": stats.title,
                    "input_tokens": stats.token_count,
                    "output_tokens": predicted_output,
                    "input_cost": input_cost,
                    "output_cost": output_cost,
                    "total_cost": total_cost,
                }
            )

        return {
            "model": self.model,
            "source_language": get_language_name(source_language),
            "target_language": get_language_name(target_language),
            "expansion_factor": expansion_factor,
            "chapters": chapter_costs,
            "total_input_tokens": sum(c["input_tokens"] for c in chapter_costs),
            "total_output_tokens": sum(c["output_tokens"] for c in chapter_costs),
            "total_cost": sum(c["total_cost"] for c in chapter_costs),
        }

    def _count_sentences(self, text: str) -> int:
        """Count the number of sentences in the text."""
        sentences = re.split(r"[.!?]+", text)
        return len([s for s in sentences if s.strip()])

    def _count_paragraphs(self, text: str) -> int:
        """Count the number of paragraphs in the text."""
        paragraphs = re.split(r"\n\s*\n|<p.*?>.*?</p>", text, flags=re.DOTALL)
        return len([p for p in paragraphs if p.strip()])

    def _calculate_readability_score(
        self, text: str, word_count: int, sentence_count: int
    ) -> Optional[float]:
        """Calculate a basic readability score using the Flesch-Kincaid formula."""
        if sentence_count == 0 or word_count == 0:
            return None

        score = (
            206.835
            - (1.015 * (word_count / sentence_count))
            - (84.6 * (len(text.split()) / sentence_count))
        )
        return score

    def _calculate_complexity_score(self, text: str) -> Optional[float]:
        """Calculate a basic complexity score based on vocabulary diversity."""
        words = [word.lower() for word in text.split() if word.isalpha()]
        if not words:
            return None

        unique_word_count = len(set(words))
        total_word_count = len(words)
        complexity_score = unique_word_count / total_word_count
        return complexity_score


# Convenience function for backward compatibility
def show_chapters(
    input_epub_path: str,
    source_language: str = "en",
    target_language: str = "es",
    model: str = "gpt-4o",
) -> None:
    """
    Convenience function to analyze EPUB and show chapters with translation costs.

    Args:
        input_epub_path: Path to EPUB file
        source_language: Source language code
        target_language: Target language code
        model: Model name for tokenization and pricing
    """
    reader = EPUBReader(input_epub_path)
    analyzer = EnhancedEpubAnalyzer(reader, model)
    analyzer.show_chapters(
        detailed=True, source_language=source_language, target_language=target_language
    )
