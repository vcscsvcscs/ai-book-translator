"""
Handles output generation for translated books.
"""
from enum import Enum
from pathlib import Path
import time
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
        self.output_formats = {OutputFormat.MARKDOWN}  # Default format
    
    def generate_outputs(
        self, original_book, output_path: str, from_lang: str, to_lang: str
    ):
        """Generate all requested output formats."""
        if not self.translated_chapters:
            raise TranslationError("No translated chapters available for output generation")
        
        print(f"📝 Generating outputs for {len(self.translated_chapters)} chapters")
        
        base_path = Path(output_path).with_suffix("")
        
        for format_type in self.output_formats:
            try:
                print(f"🔄 Generating {format_type.value.upper()} output...")
                
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
                print(f"✅ {format_type.value.upper()} output generated successfully")
                
            except Exception as e:
                error_msg = f"Failed to generate {format_type.value.upper()}: {e}"
                print(f"❌ {error_msg}")
                raise TranslationError(error_msg)

    def _generate_markdown(self, output_path: Path, from_lang: str, to_lang: str):
        """Generate markdown output."""
        try:
            content = []
            
            # Add title and metadata
            content.append(f"# Translated Book ({from_lang} → {to_lang})")
            content.append(f"*Translation completed on {time.strftime('%Y-%m-%d %H:%M:%S')}*")
            content.append("")
            content.append("---")
            content.append("")
            
            # Add chapters
            for chapter in self.translated_chapters:
                chapter_title = chapter.get('title', f"Chapter {chapter.get('number', '?')}")
                chapter_content = chapter.get('content', '')
                
                print(f"  📄 Adding chapter: {chapter_title} ({len(chapter_content)} chars)")
                
                # Add chapter header
                content.append(f"## {chapter_title}")
                content.append("")
                
                # Add chapter content
                if chapter_content and chapter_content.strip():
                    # Clean up the content for markdown
                    cleaned_content = self._clean_content_for_markdown(chapter_content)
                    content.append(cleaned_content)
                else:
                    content.append("*[No content available for this chapter]*")
                
                content.append("")
                content.append("---")
                content.append("")
            
            # Write to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            print(f"  📝 Markdown file written: {output_path} ({output_path.stat().st_size} bytes)")
            
        except Exception as e:
            raise TranslationError(f"Failed to generate markdown: {e}")

    def _generate_epub(self, original_book, output_path: Path, from_lang: str, to_lang: str):
        """Generate EPUB output."""
        try:
            # Create new book
            book = epub.EpubBook()
            
            # Set metadata
            book.set_identifier(f'translated-{time.time()}')
            book.set_title(f"Translated Book ({from_lang} → {to_lang})")
            book.set_language(to_lang.lower())
            
            # Try to copy metadata from original book
            try:
                if hasattr(original_book, 'get_metadata'):
                    for meta in original_book.get_metadata('DC', 'title'):
                        book.set_title(f"{meta[0]} (Translated)")
                        break
                    
                    for meta in original_book.get_metadata('DC', 'creator'):
                        book.add_author(meta[0])
                        break
            except Exception:
                book.add_author('Unknown Author')
            
            # Add chapters
            chapters = []
            spine = ['nav']
            
            for i, chapter in enumerate(self.translated_chapters):
                chapter_title = chapter.get('title', f"Chapter {chapter.get('number', i+1)}")
                chapter_content = chapter.get('content', '')
                
                print(f"  📄 Adding EPUB chapter: {chapter_title}")
                
                # Create chapter
                chapter_id = f"chapter_{i+1}"
                chapter_filename = f"{chapter_id}.xhtml"
                
                # Create HTML content
                html_content = self._create_html_content(chapter_title, chapter_content)
                
                # Create EPUB chapter
                epub_chapter = epub.EpubHtml(
                    title=chapter_title,
                    file_name=chapter_filename,
                    lang=to_lang.lower()
                )
                epub_chapter.content = html_content
                
                # Add to book
                book.add_item(epub_chapter)
                chapters.append(epub_chapter)
                spine.append(epub_chapter)
            
            # Add navigation
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # Set spine
            book.spine = spine
            
            # Add default CSS
            style = '''
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                p { line-height: 1.6; margin-bottom: 1em; }
            '''
            nav_css = epub.EpubItem(
                uid="nav_css",
                file_name="style/nav.css",
                media_type="text/css",
                content=style
            )
            book.add_item(nav_css)
            
            # Write EPUB
            output_path.parent.mkdir(parents=True, exist_ok=True)
            epub.write_epub(str(output_path), book)
            
            print(f"  📚 EPUB file written: {output_path} ({output_path.stat().st_size} bytes)")
            
        except Exception as e:
            raise TranslationError(f"Failed to generate EPUB: {e}")

    def _generate_pdf(self, output_path: Path, from_lang: str, to_lang: str):
        """Generate PDF output (requires additional dependencies)."""
        try:
            # For now, generate a simple text-based PDF
            # In a real implementation, you'd use reportlab or weasyprint
            print("  ⚠️  PDF generation not fully implemented - generating text file instead")
            
            # Generate as text file for now
            text_path = output_path.with_suffix('.txt')
            
            content = []
            content.append(f"Translated Book ({from_lang} → {to_lang})")
            content.append("=" * 50)
            content.append(f"Translation completed on {time.strftime('%Y-%m-%d %H:%M:%S')}")
            content.append("")
            
            for chapter in self.translated_chapters:
                chapter_title = chapter.get('title', f"Chapter {chapter.get('number', '?')}")
                chapter_content = chapter.get('content', '')
                
                content.append(f"\n{chapter_title}")
                content.append("-" * len(chapter_title))
                content.append("")
                
                if chapter_content and chapter_content.strip():
                    content.append(chapter_content)
                else:
                    content.append("[No content available for this chapter]")
                
                content.append("")
            
            text_path.parent.mkdir(parents=True, exist_ok=True)
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            print(f"  📄 Text file written: {text_path} ({text_path.stat().st_size} bytes)")
            
        except Exception as e:
            raise TranslationError(f"Failed to generate PDF: {e}")

    def _clean_content_for_markdown(self, content: str) -> str:
        """Clean content for markdown output."""
        if not content:
            return ""
        
        # Basic cleanup
        content = content.strip()
        
        # Ensure proper paragraph breaks
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Escape markdown special characters if needed
        # content = re.sub(r'([*_`])', r'\\\1', content)
        
        return content

    def _create_html_content(self, title: str, content: str) -> str:
        """Create HTML content for EPUB chapters."""
        if not content:
            content = "[No content available for this chapter]"
        
        # Escape HTML special characters
        title = html.escape(title)
        content = html.escape(content)
        
        # Convert line breaks to HTML
        content = content.replace('\n\n', '</p><p>')
        content = content.replace('\n', '<br/>')
        
        html_content = f'''<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.1//EN' 'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd'>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="../style/nav.css"/>
</head>
<body>
    <h1>{title}</h1>
    <p>{content}</p>
</body>
</html>'''
        
        return html_content