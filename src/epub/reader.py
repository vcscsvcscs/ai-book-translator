"""
EPUB reading functionality.
"""

from pathlib import Path
from typing import List, Dict, Optional, Any
import re

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from ..utils.exceptions import EpubError
from ..utils.text_utils import extract_text_from_html


class EPUBChapter:
    """Represents a single chapter in an EPUB book."""
    
    def __init__(self, item: epub.EpubHtml, chapter_number: int):
        """
        Initialize chapter.
        
        Args:
            item: EPUB item
            chapter_number: Chapter number
        """
        self.item = item
        self.chapter_number = chapter_number
        self._content = None
        self._text_content = None
        self._title = None
    
    @property
    def id(self) -> str:
        """Get chapter ID."""
        return self.item.get_id() or f"chapter_{self.chapter_number}"
    
    @property
    def title(self) -> str:
        """Get chapter title."""
        if self._title is None:
            self._title = self._extract_title()
        return self._title
    
    @property
    def content(self) -> str:
        """Get raw HTML content."""
        if self._content is None:
            content = self.item.get_content()
            if isinstance(content, bytes):
                self._content = content.decode('utf-8')
            else:
                self._content = content
        return self._content
    
    @property
    def text_content(self) -> str:
        """Get plain text content."""
        if self._text_content is None:
            self._text_content = extract_text_from_html(self.content)
        return self._text_content
    
    @property
    def character_count(self) -> int:
        """Get character count of the chapter."""
        return len(self.content)
    
    @property
    def word_count(self) -> int:
        """Get word count of the chapter."""
        return len(self.text_content.split())
    
    def _extract_title(self) -> str:
        """Extract title from chapter content."""
        soup = BeautifulSoup(self.content, 'html.parser')
        
        # Try to find title in various ways
        title_tags = ['h1', 'h2', 'h3', 'title']
        for tag in title_tags:
            element = soup.find(tag)
            if element and element.get_text().strip():
                return element.get_text().strip()
        
        # Fallback to first few words
        text = self.text_content.strip()
        if text:
            words = text.split()[:10]  # First 10 words
            title = ' '.join(words)
            if len(title) > 50:
                title = title[:47] + "..."
            return title
        
        return f"Chapter {self.chapter_number}"
    
    def get_preview(self, max_length: int = 250) -> str:
        """
        Get a preview of the chapter content.
        
        Args:
            max_length: Maximum length of preview
            
        Returns:
            Preview text
        """
        text = self.text_content.strip()
        if len(text) <= max_length:
            return text
        
        # Find a good breaking point
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        last_sentence = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
        
        if last_sentence > max_length * 0.7:  # If sentence end is reasonably close
            return text[:last_sentence + 1]
        elif last_space > max_length * 0.8:  # If word boundary is close
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."
    
    def update_content(self, new_content: str) -> None:
        """
        Update chapter content.
        
        Args:
            new_content: New HTML content
        """
        self.item.content = new_content.encode('utf-8')
        self._content = new_content
        self._text_content = None  # Reset cached text content


class EPUBReader:
    """Handles EPUB file reading and analysis."""
    
    def __init__(self, file_path: str):
        """
        Initialize EPUB reader.
        
        Args:
            file_path: Path to EPUB file
        """
        self.file_path = Path(file_path)
        self._book = None
        self._chapters = None
        self._metadata = None
        
        if not self.file_path.exists():
            raise EpubError(f"EPUB file not found: {file_path}")
        
        self._load_book()
    
    def _load_book(self) -> None:
        """Load the EPUB book."""
        try:
            self._book = epub.read_epub(str(self.file_path))
        except Exception as e:
            raise EpubError(f"Failed to read EPUB file: {e}")

    @property
    def book(self) -> epub.EpubBook:
        """Get the underlying EPUB book object."""
        if self._book is None:
            raise EpubError("EPUB book is not loaded.")
        return self._book
    
    @property
    def metadata(self) -> Dict[str, str]:
        """Get book metadata."""
        if self._metadata is None:
            self._metadata = self._extract_metadata()
        return self._metadata
    
    def _extract_metadata(self) -> Dict[str, str]:
        """Extract metadata from the book."""
        metadata = {}

        if self._book is None:
            metadata['title'] = 'Unknown'
            metadata['author'] = 'Unknown'
            metadata['language'] = 'Unknown'
            metadata['publisher'] = 'Unknown'
            metadata['description'] = ''
            metadata['subjects'] = []
            return metadata

        # Basic metadata
        metadata['title'] = self._book.get_metadata('DC', 'title')[0][0] if self._book.get_metadata('DC', 'title') else 'Unknown'
        metadata['author'] = self._book.get_metadata('DC', 'creator')[0][0] if self._book.get_metadata('DC', 'creator') else 'Unknown'
        metadata['language'] = self._book.get_metadata('DC', 'language')[0][0] if self._book.get_metadata('DC', 'language') else 'Unknown'
        metadata['publisher'] = self._book.get_metadata('DC', 'publisher')[0][0] if self._book.get_metadata('DC', 'publisher') else 'Unknown'

        # Additional metadata
        description = self._book.get_metadata('DC', 'description')
        metadata['description'] = description[0][0] if description else ''

        subjects = self._book.get_metadata('DC', 'subject')
        metadata['subjects'] = [subj[0] for subj in subjects] if subjects else []

        return metadata
    
    def get_chapters(self) -> List[EPUBChapter]:
        """
        Get all chapters from the book.
        
        Returns:
            List of EPUBChapter objects
        """
        if self._chapters is None:
            self._chapters = self._load_chapters()
        return self._chapters
    
    def _load_chapters(self) -> List[EPUBChapter]:
        """Load all chapters from the book."""
        chapters = []
        chapter_number = 1
        
        if self._book is not None:
            for item in self._book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    chapter = EPUBChapter(item, chapter_number)
                    chapters.append(chapter)
                    chapter_number += 1
        
        return chapters
    
    def get_chapter(self, chapter_number: int) -> Optional[EPUBChapter]:
        """
        Get a specific chapter by number.
        
        Args:
            chapter_number: Chapter number (1-based)
            
        Returns:
            EPUBChapter object or None if not found
        """
        chapters = self.get_chapters()
        if 1 <= chapter_number <= len(chapters):
            return chapters[chapter_number - 1]
        return None
    
    def get_chapter_range(self, start: int, end: int) -> List[EPUBChapter]:
        """
        Get a range of chapters.
        
        Args:
            start: Start chapter number (1-based, inclusive)
            end: End chapter number (1-based, inclusive)
            
        Returns:
            List of EPUBChapter objects
        """
        chapters = self.get_chapters()
        start_idx = max(0, start - 1)
        end_idx = min(len(chapters), end)
        return chapters[start_idx:end_idx]
    
    def get_total_chapters(self) -> int:
        """Get total number of chapters."""
        return len(self.get_chapters())
    
    def get_total_character_count(self) -> int:
        """Get total character count of all chapters."""
        return sum(chapter.character_count for chapter in self.get_chapters())
    
    def get_total_word_count(self) -> int:
        """Get total word count of all chapters."""
        return sum(chapter.word_count for chapter in self.get_chapters())
    
    def get_book_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the book.
        
        Returns:
            Dictionary with book information
        """
        chapters = self.get_chapters()
        
        return {
            'metadata': self.metadata,
            'file_path': str(self.file_path),
            'file_size': self.file_path.stat().st_size,
            'total_chapters': len(chapters),
            'total_characters': sum(ch.character_count for ch in chapters),
            'total_words': sum(ch.word_count for ch in chapters),
            'chapters': [
                {
                    'number': ch.chapter_number,
                    'title': ch.title,
                    'character_count': ch.character_count,
                    'word_count': ch.word_count,
                    'preview': ch.get_preview()
                }
                for ch in chapters
            ]
        }
    
    def search_text(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Search for text across all chapters.
        
        Args:
            query: Search query
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            List of search results with chapter and position info
        """
        results = []
        chapters = self.get_chapters()
        
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)
        
        for chapter in chapters:
            text = chapter.text_content
            matches = pattern.finditer(text)
            
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                results.append({
                    'chapter_number': chapter.chapter_number,
                    'chapter_title': chapter.title,
                    'position': match.start(),
                    'match': match.group(),
                    'context': context,
                    'start_in_context': match.start() - start,
                    'end_in_context': match.end() - start
                })
        
        return results
    
    def validate_epub(self) -> List[str]:
        """
        Validate the EPUB file and return any issues found.
        
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        try:
            # Check basic structure
            if not self._book:
                warnings.append("Failed to load EPUB structure")
                return warnings
            
            # Check metadata
            if not self.metadata.get('title') or self.metadata['title'] == 'Unknown':
                warnings.append("Missing or invalid title")
            
            if not self.metadata.get('author') or self.metadata['author'] == 'Unknown':
                warnings.append("Missing or invalid author")
            
            # Check chapters
            chapters = self.get_chapters()
            if not chapters:
                warnings.append("No chapters found")
            else:
                for chapter in chapters:
                    if not chapter.content.strip():
                        warnings.append(f"Chapter {chapter.chapter_number} is empty")
                    
                    # Basic HTML validation
                    try:
                        BeautifulSoup(chapter.content, 'html.parser')
                    except Exception:
                        warnings.append(f"Chapter {chapter.chapter_number} has invalid HTML")
            
            # Check file integrity
            try:
                # Try to access all items
                for item in self._book.get_items():
                    item.get_content()
            except Exception as e:
                warnings.append(f"File integrity issue: {e}")
        
        except Exception as e:
            warnings.append(f"Validation error: {e}")
        
        return warnings
    
    def get_navigation(self) -> List[Dict[str, Any]]:
        """
        Get navigation/table of contents information.
        
        Returns:
            List of navigation entries
        """
        navigation = []
        
        try:
            # Try to get table of contents
            toc = getattr(self._book, 'toc', None) if self._book is not None else None
            if toc:
                for item in toc:
                    if hasattr(item, 'title') and hasattr(item, 'href'):
                        navigation.append({
                            'title': item.title,
                            'href': item.href,
                            'level': 0
                        })
            
            # Fallback to chapters if no TOC
            if not navigation:
                chapters = self.get_chapters()
                for chapter in chapters:
                    navigation.append({
                        'title': chapter.title,
                        'href': chapter.id,
                        'level': 0,
                        'chapter_number': chapter.chapter_number
                    })
        
        except Exception:
            # If navigation extraction fails, use chapter list
            chapters = self.get_chapters()
            for chapter in chapters:
                navigation.append({
                    'title': chapter.title,
                    'href': chapter.id,
                    'level': 0,
                    'chapter_number': chapter.chapter_number
                })
        
        return navigation
    
    def extract_images(self) -> List[Dict[str, 'Any']]:
        """
        Extract information about images in the EPUB.
        
        Returns:
            List of image information
        """
        images = []
        
        try:
            if self._book is not None:
                for item in self._book.get_items():
                    if item.get_type() == ebooklib.ITEM_IMAGE:
                        images.append({
                            'id': item.get_id(),
                            'file_name': item.get_name(),
                            'media_type': item.media_type,
                            'size': len(item.get_content())
                        })
        except Exception:
            pass  # Ignore image extraction errors
        
        return images
    
    def get_spine_order(self) -> List[str]:
        """
        Get the reading order of the book.
        
        Returns:
            List of item IDs in spine order
        """
        try:
            if self._book is not None and hasattr(self._book, 'spine'):
                return [item[0] for item in self._book.spine]
            else:
                return []
        except Exception:
            return []
    
    def close(self) -> None:
        """Clean up resources."""
        self._book = None
        self._chapters = None
        self._metadata = None