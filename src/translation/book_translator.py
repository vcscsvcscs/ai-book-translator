"""
Handles book translation logic.
"""

from typing import Optional, List, Set

import ebooklib
from ebooklib import epub
from .chapter_processor import ChapterProcessor
from .output_generator import OutputGenerator, OutputFormat
from .progress import ProgressTracker
from utils.exceptions import TranslationError


class BookTranslator:
    """Handles book translation using LLM providers with multiple output formats."""

    def __init__(
        self,
        llm,
        chunk_size: int = 2000,
        max_retries: int = 3,
        retry_delay: int = 30,
        progress_file: Optional[str] = None,
        extra_prompts: str = "",
        output_formats: Optional[List[str]] = None,
    ):
        self.llm = llm
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts
        self.progress_tracker = (
            ProgressTracker(progress_file) if progress_file else None
        )

        # Parse output formats
        self.output_formats = self._parse_output_formats(output_formats or ["markdown"])

        # Store translated chapters for multi-format output
        self.translated_chapters = []

        # Initialize helper components
        self.chapter_processor = ChapterProcessor(
            llm,
            chunk_size,
            max_retries,
            retry_delay,
            extra_prompts,
            self.progress_tracker,
        )
        
        # Initialize output generator (will be updated with chapters later)
        self.output_generator = OutputGenerator([])

    def _parse_output_formats(self, formats: List[str]) -> Set[OutputFormat]:
        """Parse and validate output formats."""
        valid_formats = set()
        for fmt in formats:
            try:
                valid_formats.add(OutputFormat(fmt.lower()))
            except ValueError:
                raise TranslationError(
                    f"Invalid output format: {fmt}. Supported formats: epub, pdf, markdown"
                )

        if not valid_formats:
            valid_formats.add(OutputFormat.MARKDOWN)  # Default fallback

        return valid_formats

    def translate_book(
        self,
        input_path: str,
        output_path: str,
        from_chapter: int = 1,
        to_chapter: int = 9999,
        from_lang: str = "EN",
        to_lang: str = "HU",
    ):
        """Translate entire book and generate requested output formats."""
        try:
            book = epub.read_epub(input_path)
            print(f"📚 Successfully loaded EPUB: {input_path}")
        except Exception as e:
            raise TranslationError(f"Failed to read EPUB file: {e}")

        chapters = self._get_document_items(book)
        total_chapters = len(chapters)

        if total_chapters == 0:
            raise TranslationError("No chapters found in the EPUB file")

        print(f"📚 Found {total_chapters} chapters to process")
        print(f"🔄 Translation: {from_lang} → {to_lang}")
        print(
            f"📖 Processing chapters {from_chapter} to {min(to_chapter, total_chapters)}"
        )
        print(
            f"📄 Output formats: {', '.join([fmt.value for fmt in self.output_formats])}"
        )

        # Initialize progress tracking
        if self.progress_tracker:
            self.progress_tracker.start_translation(total_chapters)

        current_chapter = 1
        self.translated_chapters = []  # Reset for new translation

        try:
            for item in chapters:
                if from_chapter <= current_chapter <= to_chapter:
                    print(
                        f"\n🔄 Processing chapter {current_chapter}/{total_chapters}..."
                    )

                    # Check if chapter is already completed (for resume functionality)
                    if (self.progress_tracker and 
                        self.progress_tracker.is_chapter_completed(current_chapter)):
                        print(f"✅ Chapter {current_chapter} already completed (resuming)")
                        current_chapter += 1
                        continue

                    try:
                        # Translate chapter
                        chapter_data = self.chapter_processor.process_chapter(
                            item, from_lang, to_lang, current_chapter
                        )
                        
                        # Validate chapter data
                        if not chapter_data or not chapter_data.get('content'):
                            print(f"⚠️  Warning: Chapter {current_chapter} has no content")
                        else:
                            print(f"✅ Chapter {current_chapter} completed successfully")
                        
                        self.translated_chapters.append(chapter_data)

                    except Exception as e:
                        error_msg = f"Failed to process chapter {current_chapter}: {e}"
                        print(f"❌ {error_msg}")
                        
                        # Decide whether to continue or stop based on error type
                        if "TranslationError" in str(type(e)):
                            # For translation errors, we might want to continue with next chapter
                            print("⚠️  Continuing with next chapter...")
                            # Add empty chapter to maintain structure
                            self.translated_chapters.append({
                                "number": current_chapter,
                                "title": f"Chapter {current_chapter} (Failed)",
                                "content": "[Translation failed for this chapter]"
                            })
                        else:
                            # For other errors, stop processing
                            raise e

                elif to_chapter < current_chapter:
                    print(f"🛑 Reached chapter limit ({to_chapter}), stopping")
                    break

                current_chapter += 1

            # Validate we have some translated content
            if not self.translated_chapters:
                raise TranslationError("No chapters were successfully translated")

            print(f"\n📝 Translation completed. Processing {len(self.translated_chapters)} chapters for output...")

            # Update output generator with translated chapters and formats
            self.output_generator.translated_chapters = self.translated_chapters
            self.output_generator.output_formats = self.output_formats

            # Generate all requested output formats
            self.output_generator.generate_outputs(
                book, output_path, from_lang, to_lang
            )

            print("\n🎉 Translation completed successfully!")
            print(f"📊 Processed {len(self.translated_chapters)} chapters")
            
            # Print summary
            total_chars = sum(len(ch.get('content', '')) for ch in self.translated_chapters)
            print(f"📄 Total translated content: {total_chars:,} characters")

        except Exception as e:
            print(f"\n❌ Translation interrupted at chapter {current_chapter}")
            
            # Save progress even if failed
            if self.progress_tracker:
                try:
                    self.progress_tracker._save_progress()
                    print("💾 Progress saved for resume")
                except Exception:
                    pass
            
            raise TranslationError(f"Translation failed: {e}")

    def _get_document_items(self, book):
        """Get all document items from the book."""
        items = [
            item for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT
        ]
        
        print(f"📋 Found {len(items)} document items in EPUB")
        
        # Debug: Print some info about the items
        for i, item in enumerate(items[:3]):  # Show first 3 items
            print(f"  - Item {i+1}: {item.file_name} ({len(item.content)} bytes)")
        
        if len(items) > 3:
            print(f"  - ... and {len(items) - 3} more items")
            
        return items

    def get_translation_status(self):
        """Get current translation status."""
        if not self.progress_tracker:
            return {"status": "no_tracking"}
        
        return self.progress_tracker.get_progress_summary()

    def resume_translation(self, input_path: str, output_path: str, from_lang: str = "EN", to_lang: str = "HU"):
        """Resume a previously interrupted translation."""
        if not self.progress_tracker:
            raise TranslationError("No progress tracker configured for resume")
        
        progress = self.progress_tracker.get_overall_progress()
        if not progress:
            print("📄 No previous progress found, starting fresh translation")
            return self.translate_book(input_path, output_path, from_lang=from_lang, to_lang=to_lang)
        
        print(f"📄 Resuming translation from chapter {progress.current_chapter}")
        print(f"📊 Previous progress: {progress.completed_chapters}/{progress.total_chapters} chapters completed")
        
        # Continue from where we left off
        return self.translate_book(
            input_path, 
            output_path, 
            from_chapter=progress.current_chapter,
            from_lang=from_lang, 
            to_lang=to_lang
        )