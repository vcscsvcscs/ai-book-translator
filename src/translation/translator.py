"""
Enhanced translation logic with multiple output format support and proper chapter preservation.
"""

import time
from pathlib import Path
from typing import Optional, List

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from llama_index.core.llms import LLM

from .output.formats import parse_output_formats, OutputFormat
from .output.generators import generate_epub, generate_pdf, generate_markdown

from .chapter_cache import ChapterCache
from .chapter_translator import ChapterTranslator

from .progress import ProgressTracker
from utils.font_utils import register_unicode_fonts
from utils.text_utils import (
    extract_clean_text,
    clean_unicode_text,
    create_clean_xhtml,
    escape_html,
)
from utils.exceptions import TranslationError
from .chunker import TextChunker

class BookTranslator:
    """Handles book translation using LLM providers with multiple output formats."""

    def __init__(
        self,
        llm: LLM,
        chunk_size: int = 20000,
        max_retries: int = 3,
        retry_delay: int = 180,
        progress_file: Optional[str] = None,
        extra_prompts: str = "",
        output_formats: Optional[List[str]] = None,
    ):
        self.llm = llm
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts
        
        # Initialize progress tracking
        self.progress_tracker = (
            ProgressTracker(progress_file) if progress_file else None
        )

        self.chunker = TextChunker(chunk_size)

        # Initialize chapter cache
        cache_file = None
        if progress_file:
            cache_file = Path(progress_file).with_suffix('.chapters.json')
        self.chapter_cache = ChapterCache(cache_file)

        # Initialize chapter translator
        self.chapter_translator = ChapterTranslator(
            llm=llm,
            chunk_size=chunk_size,
            max_retries=max_retries,
            retry_delay=retry_delay,
            extra_prompts=extra_prompts
        )

        # Parse output formats
        self.output_formats = parse_output_formats(output_formats or ["markdown"])

        # Store translated chapters for multi-format output
        self.translated_chapters = []

    def translate_book(
        self,
        input_path: str,
        output_path: str,
        from_chapter: int = 1,
        to_chapter: int = 9999,
        from_lang: str = "EN",
        to_lang: str = "HU",
    ):
        """Translate entire book and generate requested output formats."""
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
        print(
            f"📄 Output formats: {', '.join([fmt.value for fmt in self.output_formats])}"
        )

        # Initialize progress tracking
        if self.progress_tracker:
            self.progress_tracker.start_translation(total_chapters)

            # Show progress summary if resuming
            progress = self.progress_tracker.get_overall_progress()
            if progress and progress.chapters:
                print("📄 Resuming from previous session:")
                print(
                    f"   - Overall progress: {progress.overall_progress_percentage:.1f}%"
                )
                print(
                    f"   - Completed chapters: {progress.completed_chapters}/{progress.total_chapters}"
                )
                print(f"   - Current chapter: {progress.current_chapter}")

        # Load previously completed chapters from cache
        self.translated_chapters = self.chapter_cache.load_chapters()

        current_chapter = 1

        try:
            for item in chapters:
                if from_chapter <= current_chapter <= to_chapter:
                    print(
                        f"\n🔄 Processing chapter {current_chapter}/{total_chapters}..."
                    )

                    # Check if chapter is already completed
                    if (
                        self.progress_tracker
                        and self.progress_tracker.is_chapter_completed(current_chapter)
                    ):
                        print(
                            f"✅ Chapter {current_chapter} already completed, skipping..."
                        )

                        # Ensure the chapter is in our translated_chapters list
                        if not any(
                            ch["number"] == current_chapter
                            for ch in self.translated_chapters
                        ):
                            # This shouldn't happen if cache is working, but as a fallback
                            # we can try to reconstruct from the original if needed
                            chapter_title = self._extract_chapter_title(
                                item, current_chapter
                            )
                            print(
                                f"⚠️  Chapter {current_chapter} was completed but not in cache, adding placeholder"
                            )
                            self.translated_chapters.append(
                                {
                                    "number": current_chapter,
                                    "title": chapter_title,
                                    "content": "[Previously translated content not available in cache]",
                                    "original_item": item,
                                }
                            )

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

                    # Store chapter data for multi-format output
                    chapter_data = {
                        "number": current_chapter,
                        "title": self._extract_chapter_title(item, current_chapter),
                        "content": translated_content,
                        "original_item": item,
                    }

                    # Add or update chapter in our list
                    existing_chapter_idx = None
                    for i, ch in enumerate(self.translated_chapters):
                        if ch["number"] == current_chapter:
                            existing_chapter_idx = i
                            break

                    if existing_chapter_idx is not None:
                        self.translated_chapters[existing_chapter_idx] = chapter_data
                    else:
                        self.translated_chapters.append(chapter_data)
                        # Keep list sorted by chapter number
                        self.translated_chapters.sort(key=lambda x: x["number"])

                    # Mark chapter as complete
                    if self.progress_tracker:
                        self.progress_tracker.complete_chapter(current_chapter)

                    # Save chapter cache after each completed chapter
                    self.chapter_cache.save_chapters(self.translated_chapters)

                    print(f"✅ Chapter {current_chapter} completed")

                current_chapter += 1

            # Generate all requested output formats
            self._generate_outputs(book, output_path, from_lang, to_lang)

        except Exception as e:
            print(f"\n❌ Translation interrupted at chapter {current_chapter}")
            print(f"💾 Progress saved. Resume with: --from-chapter {current_chapter}")
            raise TranslationError(f"Translation failed: {e}")

    def _generate_outputs(
        self, original_book, output_path: str, from_lang: str, to_lang: str
    ):
        """Generate all requested output formats."""
        base_path = Path(output_path).with_suffix("")

        # Ensure we have all chapters sorted by number
        self.translated_chapters.sort(key=lambda x: x["number"])

        print(f"📄 Generating outputs with {len(self.translated_chapters)} chapters")

        for format_type in self.output_formats:
            try:
                if format_type == OutputFormat.MARKDOWN:
                    generate_markdown(
                        base_path.with_suffix(".md"), from_lang, to_lang
                    )
                elif format_type == OutputFormat.EPUB:
                    generate_epub(
                        original_book,
                        base_path.with_suffix(".epub"),
                        from_lang,
                        to_lang,
                    )
                elif format_type == OutputFormat.PDF:
                    generate_pdf(
                        base_path.with_suffix(".pdf"), from_lang, to_lang
                    )

                print(f"✅ {format_type.value.upper()} output generated")

            except Exception as e:
                print(f"❌ Failed to generate {format_type.value.upper()}: {e}")

    def _generate_markdown(self, output_path: Path, from_lang: str, to_lang: str):
        """Generate Markdown output."""
        with open(output_path, "w", encoding="utf-8") as f:
            # Write header
            f.write(f"# Translated Book ({from_lang} → {to_lang})\n\n")
            f.write(
                f"*Translation generated on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            )
            f.write("---\n\n")

            # Write chapters
            for chapter in self.translated_chapters:
                if chapter["content"].strip():
                    f.write(f"## {chapter['title']}\n\n")
                    f.write(f"{chapter['content']}\n\n")
                    f.write("---\n\n")

            # Write footer
            f.write(
                f"\n*Translation completed on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n"
            )

        print(f"📖 Markdown saved to: {output_path}")

    def _generate_epub(
        self, original_book, output_path: Path, from_lang: str, to_lang: str
    ):
        """Generate EPUB output with proper XML handling."""
        try:
            # Create new book based on original
            new_book = epub.EpubBook()

            # Copy metadata
            new_book.set_identifier(
                original_book.get_metadata("DC", "identifier")[0][0]
                if original_book.get_metadata("DC", "identifier")
                else "translated_book"
            )

            original_title = (
                original_book.get_metadata("DC", "title")[0][0]
                if original_book.get_metadata("DC", "title")
                else "Translated Book"
            )
            new_book.set_title(f"{original_title} ({from_lang} → {to_lang})")

            new_book.set_language(to_lang.lower())

            if original_book.get_metadata("DC", "creator"):
                new_book.add_author(original_book.get_metadata("DC", "creator")[0][0])

            # Copy non-document items (CSS, images, etc.)
            for item in original_book.get_items():
                if item.get_type() != ebooklib.ITEM_DOCUMENT:
                    new_book.add_item(item)

            # Add translated chapters with proper XML structure
            spine_items = []

            for chapter in self.translated_chapters:
                if not chapter["content"].strip():
                    continue

                # Create clean XHTML content
                xhtml_content = create_clean_xhtml(
                    chapter["title"], chapter["content"]
                )

                # Create chapter item
                chapter_item = epub.EpubHtml(
                    title=chapter["title"],
                    file_name=f"chapter_{chapter['number']:03d}.xhtml",
                    lang=to_lang.lower(),
                )

                chapter_item.content = xhtml_content.encode("utf-8")
                new_book.add_item(chapter_item)
                spine_items.append(chapter_item)

            # Set spine (reading order)
            new_book.spine = ["nav"] + spine_items

            # Add navigation
            new_book.add_item(epub.EpubNcx())
            new_book.add_item(epub.EpubNav())

            # Set table of contents
            toc_items = []
            for i, chapter in enumerate(self.translated_chapters):
                if chapter["content"].strip():
                    toc_items.append(
                        epub.Link(
                            f"chapter_{chapter['number']:03d}.xhtml",
                            chapter["title"],
                            f"chapter_{chapter['number']}",
                        )
                    )

            new_book.toc = toc_items

            # Write EPUB
            epub.write_epub(str(output_path), new_book, {})
            print(f"📖 EPUB saved to: {output_path}")

        except Exception as e:
            raise TranslationError(f"Failed to generate EPUB: {e}")

    def _generate_pdf(self, output_path: Path, from_lang: str, to_lang: str):
        """Generate PDF output using reportlab (pure Python)."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                PageBreak,
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.colors import HexColor
            from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
            import textwrap
        except ImportError:
            print("⚠️  PDF generation requires 'reportlab' package")
            print("   Install with: pip install reportlab")
            return

        try:
            # Register Unicode-compatible fonts
            register_unicode_fonts()

            # Create PDF document
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
            )

            # Get styles
            styles = getSampleStyleSheet()

            # Create custom styles with Unicode font
            unicode_font = self._get_unicode_font_name()

            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Title"],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=HexColor("#2c3e50"),
                fontName=unicode_font,
            )

            chapter_title_style = ParagraphStyle(
                "ChapterTitle",
                parent=styles["Heading1"],
                fontSize=18,
                spaceAfter=20,
                spaceBefore=30,
                textColor=HexColor("#34495e"),
                keepWithNext=1,  # Keep chapter title with following paragraph
                fontName=unicode_font,
            )

            body_style = ParagraphStyle(
                "CustomBody",
                parent=styles["Normal"],
                fontSize=11,
                leading=16,
                alignment=TA_JUSTIFY,
                spaceAfter=12,
                firstLineIndent=20,
                fontName=unicode_font,
            )

            subtitle_style = ParagraphStyle(
                "Subtitle",
                parent=styles["Normal"],
                fontSize=10,
                alignment=TA_CENTER,
                textColor=HexColor("#7f8c8d"),
                spaceAfter=20,
                fontName=unicode_font,
            )

            # Build story (content list)
            story = []

            # Add title
            story.append(
                Paragraph(f"Translated Book ({from_lang} → {to_lang})", title_style)
            )
            story.append(Spacer(1, 12))

            # Add subtitle with timestamp
            import time

            story.append(
                Paragraph(
                    f"Translation generated on {time.strftime('%B %d, %Y at %H:%M')}",
                    subtitle_style,
                )
            )
            story.append(Spacer(1, 30))

            # Add chapters
            for i, chapter in enumerate(self.translated_chapters):
                if not chapter["content"].strip():
                    continue

                # Add page break for new chapters (except first)
                if i > 0:
                    story.append(PageBreak())

                # Add chapter title
                story.append(
                    Paragraph(escape_html(chapter["title"]), chapter_title_style)
                )

                # Process chapter content
                content = chapter["content"].strip()

                # Split content into paragraphs
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

                for paragraph in paragraphs:
                    if paragraph:
                        # Handle long paragraphs by splitting them
                        if len(paragraph) > 1000:
                            # Split very long paragraphs into smaller chunks
                            wrapped_lines = textwrap.wrap(paragraph, width=80)
                            current_chunk = []

                            for line in wrapped_lines:
                                current_chunk.append(line)
                                if len(" ".join(current_chunk)) > 800:
                                    story.append(
                                        Paragraph(
                                            escape_html(" ".join(current_chunk)),
                                            body_style,
                                        )
                                    )
                                    current_chunk = []

                            # Add remaining content
                            if current_chunk:
                                story.append(
                                    Paragraph(
                                        escape_html(" ".join(current_chunk)),
                                        body_style,
                                    )
                                )
                        else:
                            # Ensure proper Unicode handling
                            clean_paragraph = clean_unicode_text(paragraph)
                            story.append(
                                Paragraph(
                                    escape_html(clean_paragraph), body_style
                                )
                            )

                # Add spacing after chapter
                story.append(Spacer(1, 20))

            # Add footer
            story.append(PageBreak())
            story.append(Spacer(1, 200))
            story.append(
                Paragraph(
                    f"Translation completed on {time.strftime('%B %d, %Y at %H:%M')}",
                    subtitle_style,
                )
            )

            # Build PDF
            doc.build(story)
            print(f"📖 PDF saved to: {output_path}")

        except Exception as e:
            raise TranslationError(f"Failed to generate PDF: {e}")

    def _create_markdown_content(self, from_lang: str, to_lang: str) -> str:
        """Create markdown content from translated chapters."""
        lines = []
        lines.append(f"# Translated Book ({from_lang} → {to_lang})")
        lines.append("")
        lines.append(f"*Translation generated on {time.strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        for chapter in self.translated_chapters:
            if chapter["content"].strip():
                lines.append(f"## {chapter['title']}")
                lines.append("")
                lines.append(chapter["content"])
                lines.append("")
                lines.append("---")
                lines.append("")

        lines.append("")
        lines.append(f"*Translation completed on {time.strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

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

        return f"Chapter {chapter_num}"

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
        text = extract_clean_text(soup)

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
