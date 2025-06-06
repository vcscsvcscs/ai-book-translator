import time
import re
import json
from pathlib import Path
from typing import Optional, List, Set
from enum import Enum

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from llama_index.core.llms import LLM
import html

from .chunker import TextChunker
from .progress import ProgressTracker
from utils.exceptions import TranslationError


class OutputFormat(Enum):
    """Supported output formats."""

    EPUB = "epub"
    PDF = "pdf"
    MARKDOWN = "markdown"


class BookTranslator:
    """Handles book translation using LLM providers with multiple output formats."""

    def __init__(
        self,
        llm: LLM,
        chunk_size: int = 8000,  # Reduced for better GPT-4o handling
        max_retries: int = 3,
        retry_delay: int = 180,
        progress_file: Optional[str] = None,
        extra_prompts: str = "",
        output_formats: Optional[List[str]] = None,
        overlap_size: int = 300,  # Increased overlap for better context
        preserve_html: bool = True,
        min_chunk_size: int = 500,
    ):
        self.llm = llm
        # Use the improved chunker with better book-aware splitting
        self.chunker = TextChunker(
            max_chunk_size=chunk_size,
            overlap_size=overlap_size,
            preserve_html=preserve_html,
            min_chunk_size=min_chunk_size,
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts
        self.progress_tracker = (
            ProgressTracker(progress_file) if progress_file else None
        )

        # Parse output formats
        self.output_formats = self._parse_output_formats(output_formats or ["markdown"])

        # Store translated chapters for multi-format output
        self.translated_chapters = []
        
        # Cache file for storing completed chapter data
        self.chapters_cache_file = None
        if progress_file:
            cache_path = Path(progress_file).with_suffix('.chapters.json')
            self.chapters_cache_file = cache_path

        # Track chunk metadata for consistency analysis
        self.chunk_metadata_cache = {}

    def _parse_output_formats(self, formats: List[str]) -> Set[OutputFormat]:
        """Parse and validate output formats."""
        valid_formats = set()
        for fmt in formats:
            try:
                valid_formats.add(OutputFormat(fmt.lower()))
            except ValueError:
                raise TranslationError(
                    f"Invalid output format: {fmt}. Supported formats: epub, pdf, markdown"
                )

        if not valid_formats:
            valid_formats.add(OutputFormat.MARKDOWN)  # Default fallback

        return valid_formats

    def _save_chapter_cache(self):
        """Save completed chapters to cache file."""
        if not self.chapters_cache_file:
            return
            
        try:
            # Prepare serializable data
            cache_data = []
            for chapter in self.translated_chapters:
                cache_data.append({
                    'number': chapter['number'],
                    'title': chapter['title'],
                    'content': chapter['content'],
                    'metadata': chapter.get('metadata', {}),
                    # Don't save original_item as it's not serializable
                })
            
            with open(self.chapters_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️  Warning: Could not save chapter cache: {e}")

    def _load_chapter_cache(self):
        """Load completed chapters from cache file."""
        if not self.chapters_cache_file or not self.chapters_cache_file.exists():
            return
            
        try:
            with open(self.chapters_cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Convert back to chapter format
            cached_chapters = []
            for chapter_data in cache_data:
                cached_chapters.append({
                    'number': chapter_data['number'],
                    'title': chapter_data['title'],
                    'content': chapter_data['content'],
                    'metadata': chapter_data.get('metadata', {}),
                    'original_item': None  # Will be None for cached chapters
                })
            
            # Sort by chapter number
            cached_chapters.sort(key=lambda x: x['number'])
            self.translated_chapters = cached_chapters
            
            print(f"📄 Loaded {len(cached_chapters)} completed chapters from cache")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not load chapter cache: {e}")
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
        print(f"🔧 Using TextChunker with max_chunk_size={self.chunker.max_chunk_size}, overlap={self.chunker.overlap_size}")
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
        self._load_chapter_cache()

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
                        if not any(ch['number'] == current_chapter for ch in self.translated_chapters):
                            # This shouldn't happen if cache is working, but as a fallback
                            # we can try to reconstruct from the original if needed
                            chapter_title = self._extract_chapter_title(item, current_chapter)
                            print(f"⚠️  Chapter {current_chapter} was completed but not in cache, adding placeholder")
                            self.translated_chapters.append({
                                'number': current_chapter,
                                'title': chapter_title,
                                'content': '[Previously translated content not available in cache]',
                                'metadata': {},
                                'original_item': item
                            })
                        
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
                    translated_content, chapter_metadata = self._translate_chapter(
                        item, from_lang, to_lang, current_chapter, start_chunk
                    )

                    # Store chapter data for multi-format output
                    chapter_data = {
                        "number": current_chapter,
                        "title": self._extract_chapter_title(item, current_chapter),
                        "content": translated_content,
                        "metadata": chapter_metadata,
                        "original_item": item,
                    }
                    
                    # Add or update chapter in our list
                    existing_chapter_idx = None
                    for i, ch in enumerate(self.translated_chapters):
                        if ch['number'] == current_chapter:
                            existing_chapter_idx = i
                            break
                    
                    if existing_chapter_idx is not None:
                        self.translated_chapters[existing_chapter_idx] = chapter_data
                    else:
                        self.translated_chapters.append(chapter_data)
                        # Keep list sorted by chapter number
                        self.translated_chapters.sort(key=lambda x: x['number'])

                    # Mark chapter as complete
                    if self.progress_tracker:
                        self.progress_tracker.complete_chapter(current_chapter)

                    # Save chapter cache after each completed chapter
                    self._save_chapter_cache()

                    print(f"✅ Chapter {current_chapter} completed")
                    self._print_chapter_statistics(chapter_metadata)

                current_chapter += 1

            # Generate all requested output formats
            self._generate_outputs(book, output_path, from_lang, to_lang)

        except Exception as e:
            print(f"\n❌ Translation interrupted at chapter {current_chapter}")
            print(f"💾 Progress saved. Resume with: --from-chapter {current_chapter}")
            raise TranslationError(f"Translation failed: {e}")

    def _print_chapter_statistics(self, metadata: dict):
        """Print chapter translation statistics."""
        if metadata:
            print("    📊 Chapter stats:")
            print(f"       • Total chunks: {metadata.get('total_chunks', 'N/A')}")
            print(f"       • Total characters: {metadata.get('total_characters', 'N/A'):,}")
            print(f"       • Total words: {metadata.get('total_words', 'N/A'):,}")
            print(f"       • HTML content: {'Yes' if metadata.get('has_html', False) else 'No'}")
            print(f"       • Dialogue detected: {'Yes' if metadata.get('has_dialogue', False) else 'No'}")

    def _generate_outputs(
        self, original_book, output_path: str, from_lang: str, to_lang: str
    ):
        """Generate all requested output formats."""
        base_path = Path(output_path).with_suffix("")

        # Ensure we have all chapters sorted by number
        self.translated_chapters.sort(key=lambda x: x['number'])
        
        print(f"📄 Generating outputs with {len(self.translated_chapters)} chapters")

        for format_type in self.output_formats:
            try:
                if format_type == OutputFormat.MARKDOWN:
                    self._generate_markdown(
                        base_path.with_suffix(".md"), from_lang, to_lang
                    )
                elif format_type == OutputFormat.EPUB:
                    self._generate_epub(
                        original_book,
                        base_path.with_suffix(".epub"),
                        from_lang,
                        to_lang,
                    )
                elif format_type == OutputFormat.PDF:
                    self._generate_pdf(
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
            
            # Write translation statistics
            total_chapters = len([ch for ch in self.translated_chapters if ch['content'].strip()])
            total_chars = sum(len(ch['content']) for ch in self.translated_chapters)
            total_words = sum(len(ch['content'].split()) for ch in self.translated_chapters)
            
            f.write("**Translation Statistics:**\n")
            f.write(f"- Chapters translated: {total_chapters}\n")
            f.write(f"- Total characters: {total_chars:,}\n")
            f.write(f"- Total words: {total_words:,}\n\n")
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
                xhtml_content = self._create_clean_xhtml(
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

    def _create_clean_xhtml(self, title: str, content: str) -> str:
        """Create clean XHTML content with proper XML structure."""
        # Escape HTML entities in content
        clean_content = html.escape(content)

        # Convert line breaks to paragraphs
        paragraphs = clean_content.split("\n\n")
        formatted_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if para:
                # Replace single line breaks with spaces
                para = re.sub(r"\n+", " ", para)
                formatted_paragraphs.append(f"    <p>{para}</p>")

        xhtml_template = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <h1>{title}</h1>
{content}
</body>
</html>"""

        return xhtml_template.format(
            title=html.escape(title), content="\n".join(formatted_paragraphs)
        )

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
            self._register_unicode_fonts()

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
                    Paragraph(self._escape_html(chapter["title"]), chapter_title_style)
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
                                            self._escape_html(" ".join(current_chunk)),
                                            body_style,
                                        )
                                    )
                                    current_chunk = []

                            # Add remaining content
                            if current_chunk:
                                story.append(
                                    Paragraph(
                                        self._escape_html(" ".join(current_chunk)),
                                        body_style,
                                    )
                                )
                        else:
                            # Ensure proper Unicode handling
                            clean_paragraph = self._clean_unicode_text(paragraph)
                            story.append(
                                Paragraph(
                                    self._escape_html(clean_paragraph), body_style
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

    def _clean_unicode_text(self, text: str) -> str:
        """Clean and normalize Unicode text for PDF generation."""
        import unicodedata

        # Normalize Unicode characters (NFKC normalization)
        normalized = unicodedata.normalize("NFKC", text)

        # Ensure the text is properly encoded
        try:
            # Test if the text can be encoded/decoded properly
            normalized.encode("utf-8").decode("utf-8")
            return normalized
        except UnicodeError:
            # If there are encoding issues, try to fix them
            return normalized.encode("utf-8", errors="replace").decode("utf-8")

    def _register_unicode_fonts(self):
        """Register Unicode-compatible fonts for proper character rendering."""
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
            import platform

            # Common Unicode font paths by OS
            font_paths = []
            system = platform.system().lower()

            if system == "windows":
                font_paths = [
                    "C:/Windows/Fonts/arial.ttf",
                    "C:/Windows/Fonts/calibri.ttf",
                    "C:/Windows/Fonts/times.ttf",
                    "C:/Windows/Fonts/DejaVuSans.ttf",
                ]
            elif system == "darwin":  # macOS
                font_paths = [
                    "/System/Library/Fonts/Arial.ttf",
                    "/System/Library/Fonts/Times.ttc",
                    "/System/Library/Fonts/Helvetica.ttc",
                    "/opt/homebrew/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/local/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                ]
            else:  # Linux
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    "/usr/share/fonts/TTF/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                    "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
                ]

            # Try to register the first available font
            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont("UnicodeFont", font_path))
                        font_registered = True
                        print(f"📝 Using Unicode font: {os.path.basename(font_path)}")
                        break
                    except Exception:
                        continue

            if not font_registered:
                print("⚠️  No Unicode font found, falling back to built-in fonts")
                print("   Some characters may not display correctly")

        except Exception as e:
            print(f"⚠️  Font registration failed: {e}")

    def _get_unicode_font_name(self):
        """Get the name of the registered Unicode font."""
        try:
            from reportlab.pdfbase import pdfmetrics

            # Check if our Unicode font was registered
            if "UnicodeFont" in pdfmetrics.getRegisteredFontNames():
                return "UnicodeFont"
        except Exception:
            pass

        # Fall back to Helvetica which has better Unicode support than Times-Roman
        return "Helvetica"

    def _escape_html(self, text: str) -> str:
        """Escape HTML characters for reportlab."""
        import html

        # First escape HTML entities
        escaped = html.escape(text)

        # Handle reportlab-specific escaping
        escaped = escaped.replace("&", "&amp;")
        escaped = escaped.replace("<", "&lt;")
        escaped = escaped.replace(">", "&gt;")

        return escaped

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
    ) -> tuple[str, dict]:
        """Translate a single chapter using improved chunker with enhanced integration."""
        
        # Let the chunker decide how to handle the content
        raw_content = str(item.content)
        
        # The improved chunker automatically detects and handles HTML vs plain text
        chunks = self.chunker.split_text(raw_content)
        total_chunks = len(chunks)
        
        # Determine content type for logging
        is_html = self.chunker._has_html_content(raw_content)
        content_type = "HTML" if is_html else "plain text"
        print(f"  🔍 Processing as {content_type} content")
        print(f"  📄 Split into {total_chunks} chunks")

        # Initialize progress tracking for this chapter
        if self.progress_tracker:
            self.progress_tracker.start_chapter(chapter_num, total_chunks)

        translated_chunks = []
        chapter_metadata = {
            'total_chunks': total_chunks,
            'content_type': content_type,
            'start_chunk': start_chunk,
            'errors': [],
            'chunk_stats': []
        }

        for i, chunk in enumerate(chunks[start_chunk:], start=start_chunk):
            print(f"    🔄 Chunk {i + 1}/{total_chunks}...")
            
            # Generate chunk metadata for better translation context
            chunk_metadata = self._analyze_chunk(chunk, i, total_chunks, is_html)

            try:
                translated_chunk = self._translate_chunk_with_context(
                    chunk, from_lang, to_lang, chunk_metadata
                )
                translated_chunks.append(translated_chunk)
                
                # Store chunk statistics
                chapter_metadata['chunk_stats'].append({
                    'index': i,
                    'original_length': len(chunk),
                    'translated_length': len(translated_chunk),
                    'is_html': is_html,
                    'metadata': chunk_metadata
                })

                # Update progress
                if self.progress_tracker:
                    self.progress_tracker.update_progress(
                        chapter_num, i + 1, total_chunks
                    )

            except Exception as e:
                error_info = {
                    'chunk_index': i,
                    'error': str(e),
                    'chunk_preview': chunk[:100] + '...' if len(chunk) > 100 else chunk
                }
                chapter_metadata['errors'].append(error_info)
                
                # Record error in progress tracker
                if self.progress_tracker:
                    self.progress_tracker.record_error(chapter_num, str(e))
                
                raise TranslationError(f"Failed to translate chunk {i + 1}: {e}")

        # Combine translated chunks intelligently
        if is_html:
            final_translation = self._combine_html_chunks(translated_chunks)
        else:
            final_translation = self._combine_text_chunks(translated_chunks)
            
        return final_translation, chapter_metadata

    def _analyze_chunk(self, chunk: str, index: int, total_chunks: int, is_html: bool) -> dict:
        """Analyze chunk to provide context for better translation."""
        metadata = {
            'index': index,
            'total_chunks': total_chunks,
            'position': 'beginning' if index < total_chunks * 0.2 else 
                       'end' if index > total_chunks * 0.8 else 'middle',
            'character_count': len(chunk),
            'is_html': is_html,
            'has_dialogue': False,
            'paragraph_count': 0
        }
        
        if is_html:
            # Analyze HTML content
            soup = BeautifulSoup(chunk, 'html.parser')
            text_content = soup.get_text()
            metadata['paragraph_count'] = len(soup.find_all(['p', 'div']))
            metadata['has_dialogue'] = self._detect_dialogue(text_content)
        else:
            # Analyze plain text
            metadata['paragraph_count'] = len([p for p in chunk.split('\n\n') if p.strip()])
            metadata['has_dialogue'] = self._detect_dialogue(chunk)
            
        return metadata

    def _detect_dialogue(self, text: str) -> bool:
        """Detect if text contains dialogue."""
        dialogue_indicators = ['"', '"', '"', "'", "'", "'", '—', '--']
        return any(indicator in text for indicator in dialogue_indicators)

    def _translate_chunk_with_context(
        self, chunk: str, from_lang: str, to_lang: str, metadata: dict
    ) -> str:
        """Translate a chunk with contextual information, with improved retry/backoff logic."""

        prompt = self._create_contextual_translation_prompt(
            chunk, from_lang, to_lang, metadata
        )

        for attempt in range(self.max_retries):
            try:
                response = self.llm.complete(prompt)
                translated = response.text.strip()

                if self._validate_translation(chunk, translated, metadata):
                    return translated
                elif attempt == 0:
                    print("    ⚠️  Translation quality check failed, retrying...")

            except Exception as e:
                error_msg = str(e).lower()

                # Handle rate limits
                if "rate limit" in error_msg or "quota" in error_msg:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"    ⏳ Rate limit hit. Waiting {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue

                # Other errors: continue with increasing wait
                print(f"    ⚠️  Error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    print(f"    ⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue

                raise TranslationError(
                    f"Translation failed after {self.max_retries} attempts: {e}"
                )

        # Final fallback (should not reach here if retries succeed)
        raise TranslationError("Translation failed: unknown issue.")


    def _create_contextual_translation_prompt(
        self, text: str, from_lang: str, to_lang: str, metadata: dict
    ) -> str:
        """Create translation prompt with contextual information."""
        
        # Base prompt
        base_prompt = (
            f"You are a professional {from_lang}-to-{to_lang} translator specializing in literature. "
            f"Translate the following text naturally and fluently to {to_lang}. "
        )
        
        # Add context-specific instructions
        context_instructions = []
        
        if metadata['is_html']:
            context_instructions.append("Preserve HTML structure and formatting.")
        
        if metadata['has_dialogue']:
            context_instructions.append("Pay special attention to dialogue and maintain character voice consistency.")
        
        if metadata['position'] == 'beginning':
            context_instructions.append("This is from the beginning of a chapter - establish tone and context clearly.")
        elif metadata['position'] == 'end':
            context_instructions.append("This is from the end of a chapter - maintain narrative continuity and closure.")
        else:
            context_instructions.append("This is from the middle of a chapter - maintain narrative flow and consistency.")
        
        # Combine instructions
        if context_instructions:
            context_prompt = " ".join(context_instructions) + " "
        else:
            context_prompt = ""
        
        # Final prompt
        return (
            f"{base_prompt}"
            f"{context_prompt}"
            f"{self.extra_prompts}. "
            f"Maintain readability and consistency while making it read naturally in {to_lang}. "
            f"Do not add explanations, comments, or notes - only provide the translation.\n\n"
            f"Text to translate:\n{text}"
        )

    def _validate_translation(self, original: str, translated: str, metadata: dict) -> bool:
        """Basic validation of translation quality."""
        
        # Check if translation is not empty
        if not translated or not translated.strip():
            return False
        
        # Check if translation is not identical to original (unless very short)
        if len(original) > 50 and original.strip() == translated.strip():
            return False
        
        # For HTML content, check if HTML structure is preserved
        if metadata['is_html']:
            try:
                orig_soup = BeautifulSoup(original, 'html.parser')
                trans_soup = BeautifulSoup(translated, 'html.parser')
                
                # Check if major structural elements are preserved
                orig_tags = [getattr(tag, "name", None) for tag in orig_soup.find_all() if getattr(tag, "name", None) is not None]
                trans_tags = [getattr(tag, "name", None) for tag in trans_soup.find_all() if getattr(tag, "name", None) is not None]
                
                # Allow some flexibility in tag preservation
                if len(orig_tags) > 0 and len(trans_tags) == 0:
                    return False
                    
            except Exception:
                # If parsing fails, accept the translation
                pass
        
        # Check reasonable length ratio (translation shouldn't be too short or too long)
        length_ratio = len(translated) / len(original) if len(original) > 0 else 0
        if length_ratio < 0.3 or length_ratio > 3.0:
            return False
        
        return True

    def _combine_html_chunks(self, chunks: List[str]) -> str:
        """Intelligently combine HTML chunks."""
        if not chunks:
            return ""
        
        # For HTML, simply join with newlines - the chunker should have
        # preserved proper HTML structure
        return "\n".join(chunks)

    def _combine_text_chunks(self, chunks: List[str]) -> str:
        """Intelligently combine text chunks."""
        if not chunks:
            return ""
        
        # For plain text, join with double newlines to preserve paragraph structure
        return "\n\n".join(chunks)

    def _extract_clean_text(self, soup: BeautifulSoup) -> str:
        """Extract clean text from HTML, preserving paragraph structure.
        
        Note: This method is now primarily used for fallback cases
        since the improved chunker handles HTML directly.
        """
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text with some structure preservation
        text = soup.get_text(separator="\n\n", strip=True)

        # Clean up excessive whitespace
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        return text.strip()