"""
Output format generators for different file types.
"""

import time
import textwrap
from pathlib import Path
from typing import List, Dict, Any

import ebooklib
from ebooklib import epub

from utils.text_utils import create_clean_xhtml, clean_unicode_text, escape_html
from utils.font_utils import register_unicode_fonts, get_unicode_font_name
from utils.exceptions import TranslationError


def generate_markdown(
    chapters: List[Dict[str, Any]],
    output_path: Path,
    from_lang: str,
    to_lang: str,
    original_book=None,
    **kwargs,
):
    """Generate Markdown output."""
    with open(output_path, "w", encoding="utf-8") as f:
        # Write header
        f.write(f"# Translated Book ({from_lang} → {to_lang})\n\n")
        f.write(f"*Translation generated on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write("---\n\n")

        # Write chapters
        for chapter in chapters:
            if chapter["content"].strip():
                f.write(f"## {chapter['title']}\n\n")
                f.write(f"{chapter['content']}\n\n")
                f.write("---\n\n")

        # Write footer
        f.write(f"\n*Translation completed on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n")

    print(f"📖 Markdown saved to: {output_path}")


def generate_epub(
    chapters: List[Dict[str, Any]],
    output_path: Path,
    from_lang: str,
    to_lang: str,
    original_book=None,
    **kwargs,
):
    """Generate EPUB output with proper XML handling."""
    if not original_book:
        raise TranslationError("Original book required for EPUB generation")

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

        for chapter in chapters:
            if not chapter["content"].strip():
                continue

            # Create clean XHTML content
            xhtml_content = create_clean_xhtml(chapter["title"], chapter["content"])

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
        for chapter in chapters:
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


def generate_pdf(
    chapters: List[Dict[str, Any]],
    output_path: Path,
    from_lang: str,
    to_lang: str,
    original_book=None,
    **kwargs,
):
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
        unicode_font = get_unicode_font_name()

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
            keepWithNext=1,
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
        story.append(
            Paragraph(
                f"Translation generated on {time.strftime('%B %d, %Y at %H:%M')}",
                subtitle_style,
            )
        )
        story.append(Spacer(1, 30))

        # Add chapters
        for i, chapter in enumerate(chapters):
            if not chapter["content"].strip():
                continue

            # Add page break for new chapters (except first)
            if i > 0:
                story.append(PageBreak())

            # Add chapter title
            story.append(Paragraph(escape_html(chapter["title"]), chapter_title_style))

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
                            Paragraph(escape_html(clean_paragraph), body_style)
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
