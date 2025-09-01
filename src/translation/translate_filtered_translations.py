"""
Chunk fixer for re-translating filtered chunks with different LLM providers.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from llama_index.core.llms import LLM

from translation.output.formats import parse_output_formats, OutputFormat
from translation.output.generators import generate_epub, generate_pdf, generate_markdown

from translation.chapter_cache import ChapterCache
from translation.chapter_translator import ChapterTranslator
from translation.chunker import TextChunker
from translation.progress import ProgressTracker

from utils.exceptions import TranslationError
from utils.text_utils import extract_clean_text


class ChunkFixer:
    """Handles fixing filtered chunks by re-translating them with different LLM providers."""

    def __init__(
        self,
        llm: LLM,
        chunk_size: int = 1000,
        max_retries: int = 3,
        retry_delay: int = 180,
        extra_prompts: str = "",
        progress_file: Optional[str] = None,
        output_formats: Optional[List[str]] = None,
    ):
        self.llm = llm
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts
        
        # Initialize progress tracking
        self.progress_tracker = (
            ProgressTracker(progress_file) if progress_file else None
        )

        # Initialize chapter cache
        cache_file = None
        if progress_file:
            cache_file = Path(progress_file).with_suffix('.chapters.json')
        self.chapter_cache = ChapterCache(cache_file)
        
        # Initialize the cache (loads existing chunk cache)
        self.chapter_cache.initialize_cache()

        # Initialize chapter translator for fixing
        self.chapter_translator = ChapterTranslator(
            llm=llm,
            chunk_size=chunk_size,
            max_retries=max_retries,
            retry_delay=retry_delay,
            extra_prompts=extra_prompts,
            chapter_cache=self.chapter_cache
        )

        # Parse output formats
        self.output_formats = parse_output_formats(output_formats or ["markdown"])

        # Store translated chapters for multi-format output
        self.translated_chapters = []
        
        # Track original chunker for consistency
        self.chunker = TextChunker(chunk_size)

    def fix_filtered_chunks(
        self,
        input_path: str,
        output_path: str,
        from_lang: str = "EN",
        to_lang: str = "HU",
        strategy: str = "original_prompt"
    ):
        """
        Fix filtered chunks by re-translating them.
        
        Args:
            input_path: Path to original EPUB file
            output_path: Path for fixed output files
            from_lang: Source language code
            to_lang: Target language code
            strategy: Strategy for fixing ('original_prompt' or 'alternative_prompt')
        """
        if not self.progress_tracker:
            raise TranslationError("Progress tracker is required for fixing filtered chunks")
            
        # Load existing progress
        if not self.progress_tracker.progress_file.exists():
            raise TranslationError("No progress file found. Run translation first.")
            
        try:
            self.progress_tracker.load_progress()
        except Exception as e:
            raise TranslationError(f"Failed to load progress: {e}")

        # Get filtered chunks from progress
        progress = self.progress_tracker.get_overall_progress()
        if not progress or not progress.filtered_chunks:
            print("✅ No filtered chunks found. Nothing to fix.")
            return

        print(f"🔧 Found {len(progress.filtered_chunks)} filtered chunks to fix")
        print(f"🔄 Translation: {from_lang} → {to_lang}")
        print(f"📋 Strategy: {strategy}")
        print(f"📄 Output formats: {', '.join([fmt.value for fmt in self.output_formats])}")

        try:
            # Load original book for context
            book = epub.read_epub(input_path)
            chapters = self._get_document_items(book)
            
            # Load previously completed chapters from cache
            self.translated_chapters = self.chapter_cache.load_chapters()
            
            # Group filtered chunks by chapter
            chunks_by_chapter = self._group_filtered_chunks_by_chapter(progress.filtered_chunks)
            
            # Process each chapter that has filtered chunks
            for chapter_num, chunk_hashes in chunks_by_chapter.items():
                print(f"\n🔧 Fixing chapter {chapter_num} ({len(chunk_hashes)} chunks)...")
                
                # Get the original chapter content
                if chapter_num <= len(chapters):
                    original_item = chapters[chapter_num - 1]  # 0-based index
                    
                    # Extract and chunk the original content
                    soup = BeautifulSoup(original_item.content, "html.parser")
                    text = extract_clean_text(soup)
                    chunks = self.chunker.split_text(text)
                    
                    # Find and fix the filtered chunks
                    fixed_count = self._fix_chapter_chunks(
                        chapter_num, chunks, chunk_hashes, from_lang, to_lang, strategy
                    )
                    
                    if fixed_count > 0:
                        # Rebuild the chapter from all chunks (including fixed ones)
                        rebuilt_content = self._rebuild_chapter_content(chapter_num, chunks)
                        
                        # Update the chapter in translated_chapters
                        self._update_translated_chapter(chapter_num, rebuilt_content, original_item)
                        
                        print(f"✅ Fixed {fixed_count} chunks in chapter {chapter_num}")
                    else:
                        print(f"⚠️  No chunks were successfully fixed in chapter {chapter_num}")
                else:
                    print(f"⚠️  Chapter {chapter_num} not found in original book")

            # Update progress to remove fixed chunks
            self._update_progress_after_fixing()
            
            # Generate fixed outputs
            self._generate_outputs(book, output_path, from_lang, to_lang)
            
            print("\n✅ Chunk fixing completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Chunk fixing failed: {e}")
            raise TranslationError(f"Chunk fixing failed: {e}")

    def _group_filtered_chunks_by_chapter(self, filtered_chunks: List[Tuple[int, str]]) -> Dict[int, List[str]]:
        """Group filtered chunks by chapter number."""
        chunks_by_chapter = {}
        for chapter_num, chunk_hash in filtered_chunks:
            if chapter_num not in chunks_by_chapter:
                chunks_by_chapter[chapter_num] = []
            chunks_by_chapter[chapter_num].append(chunk_hash)
        return chunks_by_chapter

    def _fix_chapter_chunks(
        self, 
        chapter_num: int, 
        chunks: List[str], 
        chunk_hashes: List[str],
        from_lang: str,
        to_lang: str,
        strategy: str
    ) -> int:
        """Fix filtered chunks in a specific chapter."""
        fixed_count = 0
        
        for i, chunk in enumerate(chunks):
            chunk_hash = self.chapter_cache._get_chunk_hash(chunk)
            
            if chunk_hash in chunk_hashes:
                print(f"    🔧 Fixing chunk {i + 1}/{len(chunks)}...")
                
                try:
                    # Choose fixing strategy
                    if strategy == "original_prompt":
                        fixed_chunk = self._fix_chunk_original_prompt(chunk, from_lang, to_lang)
                    else:
                        fixed_chunk = self._fix_chunk_alternative_prompt(chunk, from_lang, to_lang)
                    
                    # Update the chunk in cache
                    self.chapter_cache.save_chunk(chapter_num, chunk, fixed_chunk)
                    fixed_count += 1
                    
                    print(f"    ✅ Fixed chunk {i + 1}")
                    
                except Exception as e:
                    print(f"    ❌ Failed to fix chunk {i + 1}: {e}")
                    continue
        
        return fixed_count

    def _fix_chunk_original_prompt(self, chunk: str, from_lang: str, to_lang: str) -> str:
        """Fix chunk using the original translation prompt."""
        prompt = self.chapter_translator._create_translation_prompt(
            chunk, from_lang, to_lang
        )
        
        for attempt in range(self.max_retries):
            try:
                response = self.llm.complete(prompt)
                return response.text.strip()
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"      ⚠️  Attempt {attempt + 1} failed: {e}")
                    continue
                raise
        
        raise TranslationError(f"Failed to fix chunk after {self.max_retries} attempts")

    def _fix_chunk_alternative_prompt(self, chunk: str, from_lang: str, to_lang: str) -> str:
        """Fix chunk using an alternative prompt strategy."""
        # Alternative prompt with more explicit instructions
        prompt = (
            f"You are a professional translator specializing in {from_lang} to {to_lang} translation. "
            f"Please provide a natural, fluent translation of the following text. "
            f"Focus on maintaining the original meaning while making it read naturally in {to_lang}. "
            f"Avoid literal translations and ensure cultural appropriateness. "
            f"{self.extra_prompts} "
            f"Only provide the translation without any additional commentary.\n\n"
            f"Text to translate:\n{chunk}"
        )
        
        for attempt in range(self.max_retries):
            try:
                response = self.llm.complete(prompt)
                return response.text.strip()
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"      ⚠️  Attempt {attempt + 1} failed: {e}")
                    continue
                raise
        
        raise TranslationError(f"Failed to fix chunk after {self.max_retries} attempts")

    def _rebuild_chapter_content(self, chapter_num: int, original_chunks: List[str]) -> str:
        """Rebuild chapter content from cached chunks."""
        translated_chunks = []
        
        for chunk in original_chunks:
            cached_chunk = self.chapter_cache.get_cached_chunk(chapter_num, chunk)
            if cached_chunk:
                translated_chunks.append(cached_chunk)
            else:
                # This shouldn't happen if fixing worked correctly
                print("⚠️  Warning: No cached translation found for chunk, using original")
                translated_chunks.append(chunk)
        
        return "\n\n".join(translated_chunks)

    def _update_translated_chapter(self, chapter_num: int, content: str, original_item):
        """Update or add a chapter in the translated_chapters list."""
        chapter_data = {
            "number": chapter_num,
            "title": self._extract_chapter_title(original_item, chapter_num),
            "content": content,
            "original_item": original_item,
        }
        
        # Find existing chapter or add new one
        existing_chapter_idx = None
        for i, ch in enumerate(self.translated_chapters):
            if ch["number"] == chapter_num:
                existing_chapter_idx = i
                break
        
        if existing_chapter_idx is not None:
            self.translated_chapters[existing_chapter_idx] = chapter_data
        else:
            self.translated_chapters.append(chapter_data)
            # Keep list sorted by chapter number
            self.translated_chapters.sort(key=lambda x: x["number"])
        
        # Save updated chapters to cache
        self.chapter_cache.save_chapters(self.translated_chapters)

    def _update_progress_after_fixing(self):
        """Update progress to remove fixed chunks from filtered_chunks list."""
        if not self.progress_tracker:
            return
            
        progress = self.progress_tracker.get_overall_progress()
        if not progress:
            return
            
        # For now, we'll clear all filtered chunks since we attempted to fix them
        # In a more sophisticated implementation, we could track which ones were successfully fixed
        progress.filtered_chunks = []
        
        # Save the updated progress
        if self.progress_tracker.auto_save:
            self.progress_tracker._save_progress()

    def _generate_outputs(self, original_book, output_path: str, from_lang: str, to_lang: str):
        """Generate all requested output formats."""
        base_path = Path(output_path).with_suffix("")

        # Ensure we have all chapters sorted by number
        self.translated_chapters.sort(key=lambda x: x["number"])

        print(f"\n📄 Generating fixed outputs with {len(self.translated_chapters)} chapters")

        for format_type in self.output_formats:
            try:
                output_file = None
                if format_type == OutputFormat.MARKDOWN:
                    output_file = base_path.with_suffix(".md")
                    generate_markdown(
                        self.translated_chapters,
                        output_file, from_lang, to_lang
                    )
                elif format_type == OutputFormat.EPUB:
                    output_file = base_path.with_suffix(".epub")
                    generate_epub(
                        self.translated_chapters,
                        output_file,
                        from_lang,
                        to_lang,
                        original_book,
                    )
                elif format_type == OutputFormat.PDF:
                    output_file = base_path.with_suffix(".pdf")
                    generate_pdf(
                        self.translated_chapters,
                        output_file, from_lang, to_lang
                    )

                print(f"✅ {format_type.value.upper()} output generated: {output_file}")

            except Exception as e:
                print(f"❌ Failed to generate {format_type.value.upper()}: {e}")

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

    def get_fixing_stats(self) -> Dict[str, Any]:
        """Get statistics about the fixing process."""
        stats = {
            "chunk_size": self.chunk_size,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "has_extra_prompts": bool(self.extra_prompts),
            "llm_type": type(self.llm).__name__,
            "output_formats": [fmt.value for fmt in self.output_formats],
            "has_cache": self.chapter_cache is not None,
            "has_progress_tracker": self.progress_tracker is not None,
        }
        
        if self.chapter_cache:
            stats["cache_stats"] = self.chapter_cache.get_cache_stats()
        
        if self.progress_tracker:
            progress = self.progress_tracker.get_overall_progress()
            if progress:
                stats["progress_stats"] = {
                    "total_chapters": progress.total_chapters,
                    "completed_chapters": progress.completed_chapters,
                    "filtered_chunks_count": len(progress.filtered_chunks) if progress.filtered_chunks else 0,
                }
        
        return stats

    def preview_filtered_chunks(self) -> Dict[str, Any]:
        """Preview filtered chunks without fixing them."""
        if not self.progress_tracker:
            return {"error": "Progress tracker is required"}
            
        # Load existing progress
        if not self.progress_tracker.progress_file.exists():
            return {"error": "No progress file found"}
            
        try:
            self.progress_tracker.load_progress()
        except Exception as e:
            return {"error": f"Failed to load progress: {e}"}

        progress = self.progress_tracker.get_overall_progress()
        if not progress or not progress.filtered_chunks:
            return {"message": "No filtered chunks found"}

        # Group by chapter
        chunks_by_chapter = self._group_filtered_chunks_by_chapter(progress.filtered_chunks)
        
        return {
            "total_filtered_chunks": len(progress.filtered_chunks),
            "affected_chapters": len(chunks_by_chapter),
            "chunks_by_chapter": {
                chapter_num: len(chunk_hashes) 
                for chapter_num, chunk_hashes in chunks_by_chapter.items()
            },
            "filtered_chunks": progress.filtered_chunks
        }