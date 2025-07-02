"""
Chapter caching functionality for storing and loading completed chapters and individual chunks.
"""
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


class ChapterCache:
    """Handles caching of completed chapters and individual translated chunks."""
    
    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file
        self.chunk_cache_file = None
        
        if cache_file:
            # Create separate file for chunk cache
            self.chunk_cache_file = cache_file.with_suffix('.chunks.json')
        
        self.translated_chapters = []
        self.chunk_cache = {}  # Format: {chapter_num: {chunk_hash: translated_text}}
    
    def _get_chunk_hash(self, text: str) -> str:
        """Generate a hash for a text chunk to use as cache key."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def save_chapters(self, chapters: List[Dict[str, Any]]):
        """Save completed chapters to cache file."""
        if not self.cache_file:
            return
            
        try:
            # Prepare serializable data
            cache_data = []
            for chapter in chapters:
                cache_data.append({
                    'number': chapter['number'],
                    'title': chapter['title'],
                    'content': chapter['content'],
                    # Don't save original_item as it's not serializable
                })
                
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️  Warning: Could not save chapter cache: {e}")
    
    def load_chapters(self) -> List[Dict[str, Any]]:
        """Load completed chapters from cache file."""
        if not self.cache_file or not self.cache_file.exists():
            return []
            
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # Convert back to chapter format
            cached_chapters = []
            for chapter_data in cache_data:
                cached_chapters.append({
                    'number': chapter_data['number'],
                    'title': chapter_data['title'],
                    'content': chapter_data['content'],
                    'original_item': None  # Will be None for cached chapters
                })
                
            # Sort by chapter number
            cached_chapters.sort(key=lambda x: x['number'])
            print(f"📄 Loaded {len(cached_chapters)} completed chapters from cache")
            return cached_chapters
            
        except Exception as e:
            print(f"⚠️  Warning: Could not load chapter cache: {e}")
            return []
    
    def save_chunk(self, chapter_num: int, original_chunk: str, translated_chunk: str):
        """Save a single translated chunk to cache."""
        if not self.chunk_cache_file:
            return
            
        chunk_hash = self._get_chunk_hash(original_chunk)
        
        # Update in-memory cache
        if chapter_num not in self.chunk_cache:
            self.chunk_cache[chapter_num] = {}
        self.chunk_cache[chapter_num][chunk_hash] = translated_chunk
        
        # Save to file
        self._save_chunk_cache()
    
    def get_cached_chunk(self, chapter_num: int, original_chunk: str) -> Optional[str]:
        """Get a cached translation for a chunk if it exists."""
        chunk_hash = self._get_chunk_hash(original_chunk)
        
        if chapter_num in self.chunk_cache:
            return self.chunk_cache[chapter_num].get(chunk_hash)
        return None
    
    def get_cached_chunks_for_chapter(self, chapter_num: int) -> Dict[str, str]:
        """Get all cached chunks for a specific chapter."""
        return self.chunk_cache.get(chapter_num, {})
    
    def build_chapter_from_chunks(
        self, 
        chapter_num: int, 
        original_chunks: List[str]
    ) -> Tuple[str, int]:
        """
        Build chapter content from cached chunks.
        
        Returns:
            Tuple of (partial_content, num_completed_chunks)
        """
        translated_chunks = []
        completed_chunks = 0
        
        for chunk in original_chunks:
            cached_translation = self.get_cached_chunk(chapter_num, chunk)
            if cached_translation:
                translated_chunks.append(cached_translation)
                completed_chunks += 1
            else:
                break  # Stop at first missing chunk to maintain order
        
        partial_content = "\n\n".join(translated_chunks)
        return partial_content, completed_chunks
    
    def is_chunk_cached(self, chapter_num: int, original_chunk: str) -> bool:
        """Check if a specific chunk is already cached."""
        return self.get_cached_chunk(chapter_num, original_chunk) is not None
    
    def get_chapter_progress(self, chapter_num: int, total_chunks: int) -> Dict[str, Any]:
        """Get progress information for a specific chapter."""
        cached_chunks = self.get_cached_chunks_for_chapter(chapter_num)
        completed_chunks = len(cached_chunks)
        
        return {
            'chapter_num': chapter_num,
            'completed_chunks': completed_chunks,
            'total_chunks': total_chunks,
            'progress_percentage': (completed_chunks / total_chunks * 100) if total_chunks > 0 else 0,
            'is_complete': completed_chunks == total_chunks
        }
    
    def _save_chunk_cache(self):
        """Save chunk cache to file."""
        if not self.chunk_cache_file:
            return
            
        try:
            with open(self.chunk_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.chunk_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Warning: Could not save chunk cache: {e}")
    
    def _load_chunk_cache(self):
        """Load chunk cache from file."""
        if not self.chunk_cache_file or not self.chunk_cache_file.exists():
            return
            
        try:
            with open(self.chunk_cache_file, 'r', encoding='utf-8') as f:
                self.chunk_cache = json.load(f)
                
            # Convert string keys back to integers for chapter numbers
            converted_cache = {}
            for chapter_key, chunks in self.chunk_cache.items():
                converted_cache[int(chapter_key)] = chunks
            self.chunk_cache = converted_cache
            
            total_chunks = sum(len(chunks) for chunks in self.chunk_cache.values())
            print(f"📄 Loaded {total_chunks} cached chunks across {len(self.chunk_cache)} chapters")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not load chunk cache: {e}")
            self.chunk_cache = {}
    
    def initialize_cache(self):
        """Initialize the cache by loading existing data."""
        self._load_chunk_cache()
    
    def clear_chapter_chunks(self, chapter_num: int):
        """Clear all cached chunks for a specific chapter."""
        if chapter_num in self.chunk_cache:
            del self.chunk_cache[chapter_num]
            self._save_chunk_cache()
    
    def clear_all_chunks(self):
        """Clear all cached chunks."""
        self.chunk_cache = {}
        if self.chunk_cache_file and self.chunk_cache_file.exists():
            self.chunk_cache_file.unlink()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the current cache."""
        total_chapters_with_chunks = len(self.chunk_cache)
        total_chunks = sum(len(chunks) for chunks in self.chunk_cache.values())
        completed_chapters = len(self.translated_chapters)
        
        chapter_stats = {}
        for chapter_num, chunks in self.chunk_cache.items():
            chapter_stats[chapter_num] = len(chunks)
        
        return {
            'completed_chapters': completed_chapters,
            'chapters_with_cached_chunks': total_chapters_with_chunks,
            'total_cached_chunks': total_chunks,
            'chunks_per_chapter': chapter_stats,
            'cache_files': {
                'chapter_cache': str(self.cache_file) if self.cache_file else None,
                'chunk_cache': str(self.chunk_cache_file) if self.chunk_cache_file else None
            }
        }
    
    def cleanup_orphaned_chunks(self, valid_chapters: List[int]):
        """Remove cached chunks for chapters that are no longer valid."""
        chapters_to_remove = []
        for chapter_num in self.chunk_cache:
            if chapter_num not in valid_chapters:
                chapters_to_remove.append(chapter_num)
        
        for chapter_num in chapters_to_remove:
            del self.chunk_cache[chapter_num]
        
        if chapters_to_remove:
            print(f"🧹 Cleaned up cached chunks for {len(chapters_to_remove)} orphaned chapters")
            self._save_chunk_cache()