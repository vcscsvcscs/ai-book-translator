"""
Chapter caching functionality for storing and loading completed chapters.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class ChapterCache:
    """Handles caching of completed chapters."""

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file
        self.translated_chapters = []

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