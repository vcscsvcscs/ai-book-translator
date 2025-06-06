import re
import html
import unicodedata
from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    """
    Clean and normalize text by stripping and collapsing whitespace.
    """
    if not text:
        return ""
    # Remove extra whitespace and normalize newlines
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text_from_html(html: str) -> str:
    """
    Extract plain text from HTML content.
    """
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def count_characters(text: str) -> int:
    """
    Count the number of characters in the text.
    """
    if not text:
        return 0
    return len(text)

def extract_clean_text(soup: BeautifulSoup) -> str:
    """Extract clean text from HTML, preserving paragraph structure."""
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text with some structure preservation
    text = soup.get_text(separator="\n\n", strip=True)

    # Clean up excessive whitespace
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def extract_chapter_title(item, chapter_num: int) -> str:
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


def clean_unicode_text(text: str) -> str:
    """Clean and normalize Unicode text for PDF generation."""
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


def escape_html(text: str) -> str:
    """Escape HTML characters for reportlab."""
    # First escape HTML entities
    escaped = html.escape(text)

    # Handle reportlab-specific escaping
    escaped = escaped.replace("&", "&amp;")
    escaped = escaped.replace("<", "&lt;")
    escaped = escaped.replace(">", "&gt;")

    return escaped


def create_clean_xhtml(title: str, content: str) -> str:
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