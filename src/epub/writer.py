"""
EPUB writing functionality.
"""

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any

import ebooklib
from ebooklib import epub

from ..utils.exceptions import EpubError
from .reader import EPUBReader


class EPUBWriter:
    """Handles EPUB file writing and modification."""
    
    def __init__(self, output_path: str):
        """
        Initialize EPUB writer.
        
        Args:
            output_path: Path where the EPUB will be written
        """
        self.output_path = Path(output_path)
        self._book = None
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def create_from_reader(self, reader: EPUBReader) -> 'EPUBWriter':
        """
        Create a new EPUB based on an existing one from EPUBReader.
        
        Args:
            reader: EPUBReader instance
            
        Returns:
            Self for method chaining
        """
        self._book = reader.book
        return self

    def create_new_book(
        self,
        title: str,
        author: str,
        language: str = 'en',
        identifier: Optional[str] = None
    ) -> 'EPUBWriter':
        """
        Create a new EPUB book from scratch.
        
        Args:
            title: Book title
            author: Book author
            language: Book language
            identifier: Unique identifier for the book
            
        Returns:
            Self for method chaining
        """
        self._book = epub.EpubBook()
        
        # Set metadata
        self._book.set_identifier(identifier or f'book_{hash(title + author)}')
        self._book.set_title(title)
        self._book.set_language(language)
        self._book.add_author(author)
        
        return self

    def update_metadata(self, metadata: Dict[str, Any]) -> 'EPUBWriter':
        """
        Update book metadata.
        
        Args:
            metadata: Dictionary of metadata to update
            
        Returns:
            Self for method chaining
        """
        if not self._book:
            raise EpubError("No book initialized. Call create_new_book() or create_from_reader() first.")
        
        if 'title' in metadata:
            self._book.set_title(metadata['title'])
        
        if 'language' in metadata:
            self._book.set_language(metadata['language'])
        
        if 'author' in metadata:
            # Clear existing authors and add new one
            self._book.metadata[epub.NAMESPACES['DC']]['creator'] = []
            self._book.add_author(metadata['author'])
        
        if 'publisher' in metadata:
            self._book.add_metadata('DC', 'publisher', metadata['publisher'])
        
        if 'description' in metadata:
            self._book.add_metadata('DC', 'description', metadata['description'])
        
        if 'subjects' in metadata and isinstance(metadata['subjects'], list):
            # Clear existing subjects
            if 'subject' in self._book.metadata[epub.NAMESPACES['DC']]:
                self._book.metadata[epub.NAMESPACES['DC']]['subject'] = []
            
            for subject in metadata['subjects']:
                self._book.add_metadata('DC', 'subject', subject)
        
        return self
    
    def update_chapter_content(self, chapter_number: int, new_content: str) -> 'EPUBWriter':
        """
        Update the content of a specific chapter.
        
        Args:
            chapter_number: Chapter number (1-based)
            new_content: New HTML content for the chapter
            
        Returns:
            Self for method chaining
        """
        if not self._book:
            raise EpubError("No book initialized.")
        
        # Find the chapter item
        chapter_count = 1
        for item in self._book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                if chapter_count == chapter_number:
                    item.content = new_content.encode('utf-8')
                    return self
                chapter_count += 1
        
        raise EpubError(f"Chapter {chapter_number} not found")
    
    def add_chapter(
        self,
        title: str,
        content: str,
        file_name: Optional[str] = None
    ) -> 'EPUBWriter':
        """
        Add a new chapter to the book.
        
        Args:
            title: Chapter title
            content: HTML content of the chapter
            file_name: Optional file name for the chapter
            
        Returns:
            Self for method chaining
        """
        if not self._book:
            raise EpubError("No book initialized.")
        
        # Generate file name if not provided
        if not file_name:
            chapter_count = len([item for item in self._book.get_items() 
                               if item.get_type() == ebooklib.ITEM_DOCUMENT])
            file_name = f'chapter_{chapter_count + 1}.xhtml'
        
        # Create chapter
        chapter = epub.EpubHtml(
            title=title,
            file_name=file_name,
            lang=self._book.language
        )
        chapter.content = content.encode('utf-8')
        
        # Add to book
        self._book.add_item(chapter)
        
        return self
    
    def remove_chapter(self, chapter_number: int) -> 'EPUBWriter':
        """
        Remove a chapter from the book.
        
        Args:
            chapter_number: Chapter number to remove (1-based)
            
        Returns:
            Self for method chaining
        """
        if not self._book:
            raise EpubError("No book initialized.")
        
        # Find and remove the chapter
        items_to_remove = []
        chapter_count = 1
        
        for item in self._book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                if chapter_count == chapter_number:
                    items_to_remove.append(item)
                    break
                chapter_count += 1
        
        if not items_to_remove:
            raise EpubError(f"Chapter {chapter_number} not found")
        
        # Remove from items and spine
        for item in items_to_remove:
            if item in self._book.items:
                self._book.items.remove(item)
            
            # Remove from spine
            self._book.spine = [spine_item for spine_item in self._book.spine 
                              if spine_item[0] != item.get_id()]
        
        return self
    
    def reorder_chapters(self, new_order: List[int]) -> 'EPUBWriter':
        """
        Reorder chapters according to the provided list.
        
        Args:
            new_order: List of chapter numbers in the desired order
            
        Returns:
            Self for method chaining
        """
        if not self._book:
            raise EpubError("No book initialized.")
        
        # Get all document items
        document_items = []
        for item in self._book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                document_items.append(item)
        
        if len(new_order) != len(document_items):
            raise EpubError("New order must include all chapters")
        
        # Validate new_order
        if set(new_order) != set(range(1, len(document_items) + 1)):
            raise EpubError("Invalid chapter numbers in new_order")
        
        # Reorder items
        reordered_items = []
        for chapter_num in new_order:
            reordered_items.append(document_items[chapter_num - 1])
        
        # Update book items (preserve non-document items)
        new_items = []
        document_index = 0
        
        for item in self._book.items:
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                new_items.append(reordered_items[document_index])
                document_index += 1
            else:
                new_items.append(item)
        
        self._book.items = new_items
        
        # Update spine
        new_spine = []
        document_index = 0
        
        for spine_item in self._book.spine:
            if spine_item[0] in [item.get_id() for item in document_items]:
                new_spine.append((reordered_items[document_index].get_id(), spine_item[1]))
                document_index += 1
            else:
                new_spine.append(spine_item)
        
        self._book.spine = new_spine
        
        return self
    
    def add_css(self, css_content: str, file_name: str = 'style.css') -> 'EPUBWriter':
        """
        Add CSS stylesheet to the book.
        
        Args:
            css_content: CSS content
            file_name: CSS file name
            
        Returns:
            Self for method chaining
        """
        if not self._book:
            raise EpubError("No book initialized.")
        
        # Create CSS item
        css_item = epub.EpubItem(
            uid="style_default",
            file_name=file_name,
            media_type="text/css",
            content=css_content.encode('utf-8')
        )
        
        # Add to book
        self._book.add_item(css_item)
        
        return self
    
    def add_cover_image(self, image_path: str) -> 'EPUBWriter':
        """
        Add cover image to the book.
        
        Args:
            image_path: Path to the cover image
            
        Returns:
            Self for method chaining
        """
        if not self._book:
            raise EpubError("No book initialized.")
        
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise EpubError(f"Cover image not found: {image_path}")
        
        # Read image content
        with open(image_path_obj, 'rb') as f:
            image_content = f.read()
        
        # Determine media type
        extension = image_path_obj.suffix.lower()
        
        # Create cover image
        self._book.set_cover(f"cover{extension}", image_content)
        
        return self
    
    def save(self, create_backup: bool = True) -> Path:
        """
        Save the EPUB file.
        
        Args:
            create_backup: Whether to create a backup if file exists
            
        Returns:
            Path to the saved file
        """
        if not self._book:
            raise EpubError("No book to save. Initialize a book first.")
        
        try:
            # Create backup if requested and file exists
            if create_backup and self.output_path.exists():
                backup_path = self.output_path.with_suffix(f'{self.output_path.suffix}.backup')
                shutil.copy2(self.output_path, backup_path)
            
            # Write the EPUB
            epub.write_epub(str(self.output_path), self._book, {})
            
            return self.output_path
            
        except Exception as e:
            raise EpubError(f"Failed to save EPUB: {e}")
    
    def save_partial(self, suffix: str = '.partial') -> Path:
        """
        Save a partial/temporary version of the EPUB.
        
        Args:
            suffix: Suffix to add to the filename
            
        Returns:
            Path to the saved partial file
        """
        if not self._book:
            raise EpubError("No book to save.")
        
        partial_path = self.output_path.with_name(f'{self.output_path.stem}{suffix}{self.output_path.suffix}')
        
        try:
            epub.write_epub(str(partial_path), self._book, {})
            return partial_path
        except Exception as e:
            raise EpubError(f"Failed to save partial EPUB: {e}")
    
    def validate_before_save(self) -> List[str]:
        """
        Validate the book before saving.
        
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        if not self._book:
            warnings.append("No book initialized")
            return warnings
        
        try:
            # Check required metadata
            if not self._book.get_metadata('DC', 'title'):
                warnings.append("Missing title")
            
            if not self._book.get_metadata('DC', 'creator'):
                warnings.append("Missing author")
            
            if not self._book.get_metadata('DC', 'language'):
                warnings.append("Missing language")
            
            # Check chapters
            document_items = [item for item in self._book.get_items() 
                            if item.get_type() == ebooklib.ITEM_DOCUMENT]
            
            if not document_items:
                warnings.append("No chapters found")
            
            # Check spine
            if not self._book.spine:
                warnings.append("Empty spine - reading order not defined")
            
            # Check for empty chapters
            for i, item in enumerate(document_items, 1):
                if not item.get_content().strip():
                    warnings.append(f"Chapter {i} is empty")
        
        except Exception as e:
            warnings.append(f"Validation error: {e}")
        
        return warnings
    
    def get_book_info(self) -> Dict[str, Any]:
        """
        Get information about the current book.
        
        Returns:
            Dictionary with book information
        """
        if not self._book:
            return {'error': 'No book initialized'}
        
        try:
            document_items = [item for item in self._book.get_items() 
                            if item.get_type() == ebooklib.ITEM_DOCUMENT]
            
            total_size = sum(len(item.get_content()) for item in document_items)
            
            return {
                'title': self._book.get_metadata('DC', 'title')[0][0] if self._book.get_metadata('DC', 'title') else 'Unknown',
                'author': self._book.get_metadata('DC', 'creator')[0][0] if self._book.get_metadata('DC', 'creator') else 'Unknown',
                'language': self._book.get_metadata('DC', 'language')[0][0] if self._book.get_metadata('DC', 'language') else 'Unknown',
                'chapter_count': len(document_items),
                'total_content_size': total_size,
                'output_path': str(self.output_path)
            }
        
        except Exception as e:
            return {'error': f'Failed to get book info: {e}'}
    
    def cleanup_temp_files(self) -> None:
        """Clean up any temporary files created during the writing process."""
        try:
            # Remove partial files
            partial_pattern = f'{self.output_path.stem}.partial{self.output_path.suffix}'
            partial_path = self.output_path.with_name(partial_pattern)
            
            if partial_path.exists():
                partial_path.unlink()
            
            # Remove backup files if they exist
            backup_pattern = f'{self.output_path.name}.backup'
            backup_path = self.output_path.with_name(backup_pattern)
            
            if backup_path.exists():
                backup_path.unlink()
                
        except Exception:
            # Ignore cleanup errors
            pass