from bs4 import BeautifulSoup
import re

def clean_text(text: str) -> str:
    """
    Clean and normalize text by stripping and collapsing whitespace.
    """
    if not text:
        return ""
    # Remove extra whitespace and normalize newlines
    text = re.sub(r'\s+', ' ', text)
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