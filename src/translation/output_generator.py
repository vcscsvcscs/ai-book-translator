"""
Handles output generation for translated books.
"""

from enum import Enum
from pathlib import Path
import time

import ebooklib
from ebooklib import epub
from utils.exceptions import TranslationError
import html
import re

class OutputFormat(Enum):
    """Supported output formats."""

    EPUB = "epub"
    PDF = "pdf"
    MARKDOWN = "markdown"

class OutputGenerator:
    """Generates output formats for translated books."""

    def __init__(self, translated_chapters):
        self.translated_chapters = translated_chapters

    def generate_outputs(
        self, original_book, output_path: str, from_lang: str, to_lang: str
    ):
        """Generate all requested output formats."""
        base_path = Path(output_path).with_suffix("")

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
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
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
                bottomMargin=72
            )

            # Get styles
            styles = getSampleStyleSheet()
            
            # Create custom styles with Unicode font
            unicode_font = self._get_unicode_font_name()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=HexColor('#2c3e50'),
                fontName=unicode_font
            )
            
            chapter_title_style = ParagraphStyle(
                'ChapterTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=20,
                spaceBefore=30,
                textColor=HexColor('#34495e'),
                keepWithNext=1,  # Keep chapter title with following paragraph
                fontName=unicode_font
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=11,
                leading=16,
                alignment=TA_JUSTIFY,
                spaceAfter=12,
                firstLineIndent=20,
                fontName=unicode_font
            )
            
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_CENTER,
                textColor=HexColor('#7f8c8d'),
                spaceAfter=20,
                fontName=unicode_font
            )

            # Build story (content list)
            story = []
            
            # Add title
            story.append(Paragraph(f"Translated Book ({from_lang} → {to_lang})", title_style))
            story.append(Spacer(1, 12))
            
            # Add subtitle with timestamp
            import time
            story.append(Paragraph(
                f"Translation generated on {time.strftime('%B %d, %Y at %H:%M')}",
                subtitle_style
            ))
            story.append(Spacer(1, 30))

            # Add chapters
            for i, chapter in enumerate(self.translated_chapters):
                if not chapter["content"].strip():
                    continue
                    
                # Add page break for new chapters (except first)
                if i > 0:
                    story.append(PageBreak())
                
                # Add chapter title
                story.append(Paragraph(self._escape_html(chapter["title"]), chapter_title_style))
                
                # Process chapter content
                content = chapter["content"].strip()
                
                # Split content into paragraphs
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                
                for paragraph in paragraphs:
                    if paragraph:
                        # Handle long paragraphs by splitting them
                        if len(paragraph) > 1000:
                            # Split very long paragraphs into smaller chunks
                            wrapped_lines = textwrap.wrap(paragraph, width=80)
                            current_chunk = []
                            
                            for line in wrapped_lines:
                                current_chunk.append(line)
                                if len(' '.join(current_chunk)) > 800:
                                    clean_chunk = self._clean_unicode_text(' '.join(current_chunk))
                                    story.append(Paragraph(
                                        self._escape_html(clean_chunk), 
                                        body_style
                                    ))
                                    current_chunk = []
                            
                            # Add remaining content
                            if current_chunk:
                                clean_chunk = self._clean_unicode_text(' '.join(current_chunk))
                                story.append(Paragraph(
                                    self._escape_html(clean_chunk), 
                                    body_style
                                ))
                        else:
                            # Ensure proper Unicode handling
                            clean_paragraph = self._clean_unicode_text(paragraph)
                            story.append(Paragraph(self._escape_html(clean_paragraph), body_style))
                
                # Add spacing after chapter
                story.append(Spacer(1, 20))

            # Add footer
            story.append(PageBreak())
            story.append(Spacer(1, 200))
            story.append(Paragraph(
                f"Translation completed on {time.strftime('%B %d, %Y at %H:%M')}",
                subtitle_style
            ))

            # Build PDF
            doc.build(story)
            print(f"📖 PDF saved to: {output_path}")

        except Exception as e:
            raise TranslationError(f"Failed to generate PDF: {e}")

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
            
            if system == 'windows':
                font_paths = [
                    'C:/Windows/Fonts/arial.ttf',
                    'C:/Windows/Fonts/calibri.ttf',
                    'C:/Windows/Fonts/times.ttf',
                    'C:/Windows/Fonts/DejaVuSans.ttf'
                ]
            elif system == 'darwin':  # macOS
                font_paths = [
                    '/System/Library/Fonts/Arial.ttf',
                    '/System/Library/Fonts/Times.ttc',
                    '/System/Library/Fonts/Helvetica.ttc',
                    '/opt/homebrew/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    '/usr/local/share/fonts/truetype/dejavu/DejaVuSans.ttf'
                ]
            else:  # Linux
                font_paths = [
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                    '/usr/share/fonts/TTF/DejaVuSans.ttf',
                    '/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf',
                    '/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf'
                ]
            
            # Try to register the first available font
            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('UnicodeFont', font_path))
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
            if 'UnicodeFont' in pdfmetrics.getRegisteredFontNames():
                return 'UnicodeFont'
        except Exception:
            pass
        
        # Fall back to Helvetica which has better Unicode support than Times-Roman
        return 'Helvetica'

    def _clean_unicode_text(self, text: str) -> str:
        """Clean and normalize Unicode text for PDF generation."""
        import unicodedata
        
        # Normalize Unicode characters (NFKC normalization)
        normalized = unicodedata.normalize('NFKC', text)
        
        # Ensure the text is properly encoded
        try:
            # Test if the text can be encoded/decoded properly
            normalized.encode('utf-8').decode('utf-8')
            return normalized
        except UnicodeError:
            # If there are encoding issues, try to fix them
            return normalized.encode('utf-8', errors='replace').decode('utf-8')

    def _escape_html(self, text: str) -> str:
        """Escape HTML characters for reportlab."""
        import html
        # First escape HTML entities
        escaped = html.escape(text)
        
        # Handle reportlab-specific escaping (but don't double-escape)
        if '&amp;' not in escaped:
            escaped = escaped.replace('&', '&amp;')
        escaped = escaped.replace('<', '&lt;')
        escaped = escaped.replace('>', '&gt;')
        
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
