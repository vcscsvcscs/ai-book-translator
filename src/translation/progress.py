"""
Progress tracking for translation operations.
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from utils.exceptions import ProgressError


@dataclass
class ChapterProgress:
    """Progress information for a single chapter."""

    chapter_number: int
    total_chunks: int
    completed_chunks: int
    start_time: float
    last_update_time: float
    estimated_completion_time: Optional[float] = None
    error_count: int = 0

    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage."""
        if self.total_chunks == 0:
            return 0.0
        return (self.completed_chunks / self.total_chunks) * 100

    @property
    def is_completed(self) -> bool:
        """Check if chapter is completed."""
        return self.completed_chunks >= self.total_chunks

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time for this chapter."""
        return self.last_update_time - self.start_time

    def estimate_remaining_time(self) -> Optional[float]:
        """Estimate remaining time for this chapter."""
        if self.completed_chunks == 0:
            return None

        elapsed = self.elapsed_time
        chunks_per_second = self.completed_chunks / elapsed
        remaining_chunks = self.total_chunks - self.completed_chunks

        if chunks_per_second > 0:
            return remaining_chunks / chunks_per_second
        return None


@dataclass
class TranslationProgress:
    """Overall translation progress information."""

    total_chapters: int
    completed_chapters: int
    current_chapter: int
    start_time: float
    last_update_time: float
    chapters: Dict[int, ChapterProgress]

    @property
    def overall_progress_percentage(self) -> float:
        """Get overall progress as percentage."""
        if self.total_chapters == 0:
            return 0.0
        return (self.completed_chapters / self.total_chapters) * 100

    @property
    def elapsed_time(self) -> float:
        """Get total elapsed time."""
        return self.last_update_time - self.start_time

    def estimate_total_remaining_time(self) -> Optional[float]:
        """Estimate total remaining time."""
        if self.completed_chapters == 0:
            return None

        elapsed = self.elapsed_time
        chapters_per_second = self.completed_chapters / elapsed
        remaining_chapters = self.total_chapters - self.completed_chapters

        if chapters_per_second > 0:
            return remaining_chapters / chapters_per_second
        return None


class ProgressTracker:
    """Handles progress tracking and persistence."""

    def __init__(self, progress_file: Optional[str] = None, auto_save: bool = True):
        """
        Initialize progress tracker.

        Args:
            progress_file: Path to save progress data
            auto_save: Whether to automatically save progress updates
        """
        self.progress_file = Path(progress_file) if progress_file else None
        self.auto_save = auto_save
        self._progress: Optional[TranslationProgress] = None
        self._callbacks = []
        
        # Automatically load existing progress if file exists
        if self.progress_file and self.progress_file.exists():
            try:
                self.load_progress()
                print(f"📄 Loaded existing progress from {self.progress_file}")
            except Exception as e:
                print(f"⚠️  Warning: Could not load existing progress: {e}")

    def start_translation(self, total_chapters: int) -> None:
        """
        Start tracking a new translation.

        Args:
            total_chapters: Total number of chapters to translate
        """
        current_time = time.time()

        # If we have existing progress, preserve it and update total chapters
        if self._progress:
            print("📄 Resuming existing translation progress...")
            self._progress.total_chapters = total_chapters
            self._progress.last_update_time = current_time
            
            # Recalculate completed chapters count in case it's out of sync
            completed_count = sum(
                1 for cp in self._progress.chapters.values() if cp.is_completed
            )
            self._progress.completed_chapters = completed_count
        else:
            # Start fresh translation
            self._progress = TranslationProgress(
                total_chapters=total_chapters,
                completed_chapters=0,
                current_chapter=1,
                start_time=current_time,
                last_update_time=current_time,
                chapters={},
            )

        if self.auto_save:
            self._save_progress()

        self._notify_callbacks("translation_started", self._progress)

    def start_chapter(self, chapter_number: int, total_chunks: int) -> None:
        """
        Start tracking a new chapter.

        Args:
            chapter_number: Chapter number
            total_chunks: Total number of chunks in the chapter
        """
        if not self._progress:
            raise ProgressError(
                "Translation not started. Call start_translation() first."
            )

        current_time = time.time()

        # Check if chapter already exists (resuming)
        if chapter_number in self._progress.chapters:
            existing_chapter = self._progress.chapters[chapter_number]
            # Update total chunks in case it changed
            existing_chapter.total_chunks = total_chunks
            existing_chapter.last_update_time = current_time
            print(f"📄 Resuming chapter {chapter_number} from chunk {existing_chapter.completed_chunks + 1}/{total_chunks}")
        else:
            # Create new chapter progress
            chapter_progress = ChapterProgress(
                chapter_number=chapter_number,
                total_chunks=total_chunks,
                completed_chunks=0,
                start_time=current_time,
                last_update_time=current_time,
            )
            self._progress.chapters[chapter_number] = chapter_progress

        self._progress.current_chapter = chapter_number
        self._progress.last_update_time = current_time

        if self.auto_save:
            self._save_progress()

        self._notify_callbacks("chapter_started", self._progress.chapters[chapter_number])

    def update_progress(
        self,
        chapter_number: int,
        completed_chunks: int,
        total_chunks: Optional[int] = None,
    ) -> None:
        """
        Update progress for a specific chapter.

        Args:
            chapter_number: Chapter number
            completed_chunks: Number of completed chunks
            total_chunks: Total chunks (if different from initial)
        """
        if not self._progress:
            raise ProgressError(
                "Translation not started. Call start_translation() first."
            )

        if chapter_number not in self._progress.chapters:
            # Auto-start chapter if not already started
            if total_chunks is None:
                raise ProgressError(
                    f"Chapter {chapter_number} not started and no total_chunks provided"
                )
            self.start_chapter(chapter_number, total_chunks)

        current_time = time.time()
        chapter_progress = self._progress.chapters[chapter_number]

        # Update chapter progress
        chapter_progress.completed_chunks = completed_chunks
        if total_chunks is not None:
            chapter_progress.total_chunks = total_chunks
        chapter_progress.last_update_time = current_time

        # Update overall progress
        self._progress.last_update_time = current_time

        if self.auto_save:
            self._save_progress()

        self._notify_callbacks("progress_updated", chapter_progress)

    def complete_chapter(self, chapter_number: int) -> None:
        """
        Mark a chapter as completed.

        Args:
            chapter_number: Chapter number to mark as completed
        """
        if not self._progress:
            raise ProgressError("Translation not started.")

        if chapter_number in self._progress.chapters:
            chapter_progress = self._progress.chapters[chapter_number]
            chapter_progress.completed_chunks = chapter_progress.total_chunks
            chapter_progress.last_update_time = time.time()

            # Update overall completed chapters count
            completed_count = sum(
                1 for cp in self._progress.chapters.values() if cp.is_completed
            )
            self._progress.completed_chapters = completed_count

            if self.auto_save:
                self._save_progress()

            self._notify_callbacks("chapter_completed", chapter_progress)

    def record_error(self, chapter_number: int, error_message: str) -> None:
        """
        Record an error for a specific chapter.

        Args:
            chapter_number: Chapter number where error occurred
            error_message: Error message
        """
        if not self._progress:
            return

        if chapter_number in self._progress.chapters:
            self._progress.chapters[chapter_number].error_count += 1

            if self.auto_save:
                self._save_progress()

            self._notify_callbacks(
                "error_recorded",
                {
                    "chapter": chapter_number,
                    "error": error_message,
                    "error_count": self._progress.chapters[chapter_number].error_count,
                },
            )

    def get_chapter_progress(self, chapter_number: int) -> int:
        """
        Get the number of completed chunks for a chapter.

        Args:
            chapter_number: Chapter number

        Returns:
            Number of completed chunks (0 if chapter not found)
        """
        if not self._progress or chapter_number not in self._progress.chapters:
            return 0

        return self._progress.chapters[chapter_number].completed_chunks

    def get_overall_progress(self) -> Optional[TranslationProgress]:
        """Get overall translation progress."""
        return self._progress

    def load_progress(self) -> bool:
        """
        Load progress from file.

        Returns:
            True if progress was loaded successfully, False otherwise
        """
        if not self.progress_file or not self.progress_file.exists():
            return False

        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Reconstruct progress objects
            chapters = {}
            for chapter_num_str, chapter_data in data.get("chapters", {}).items():
                chapter_num = int(chapter_num_str)
                chapters[chapter_num] = ChapterProgress(**chapter_data)

            self._progress = TranslationProgress(
                total_chapters=data["total_chapters"],
                completed_chapters=data["completed_chapters"],
                current_chapter=data["current_chapter"],
                start_time=data["start_time"],
                last_update_time=data["last_update_time"],
                chapters=chapters,
            )

            return True

        except Exception as e:
            raise ProgressError(f"Failed to load progress: {e}")

    def _save_progress(self) -> None:
        """Save progress to file."""
        if not self.progress_file or not self._progress:
            return

        try:
            # Ensure directory exists
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert to serializable format
            data = asdict(self._progress)

            # Convert chapter keys to strings for JSON
            chapters_data = {}
            for chapter_num, chapter_progress in data["chapters"].items():
                chapters_data[str(chapter_num)] = chapter_progress
            data["chapters"] = chapters_data

            # Write to file
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            raise ProgressError(f"Failed to save progress: {e}")

    def cleanup(self) -> None:
        """Clean up progress file and reset state."""
        if self.progress_file and self.progress_file.exists():
            try:
                self.progress_file.unlink()
            except Exception:
                pass  # Ignore cleanup errors

        self._progress = None
        self._notify_callbacks("cleanup_completed", None)

    def add_callback(self, callback) -> None:
        """
        Add a progress callback function.

        Args:
            callback: Function that takes (event_type, data) parameters
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback) -> None:
        """Remove a progress callback function."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self, event_type: str, data: Any) -> None:
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception:
                # Don't let callback errors break progress tracking
                pass

    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current progress.

        Returns:
            Dictionary with progress summary
        """
        if not self._progress:
            return {"status": "not_started"}

        summary = {
            "status": "in_progress",
            "overall_progress": self._progress.overall_progress_percentage,
            "completed_chapters": self._progress.completed_chapters,
            "total_chapters": self._progress.total_chapters,
            "current_chapter": self._progress.current_chapter,
            "elapsed_time": self._progress.elapsed_time,
            "estimated_remaining_time": self._progress.estimate_total_remaining_time(),
            "start_time": datetime.fromtimestamp(self._progress.start_time).isoformat(),
            "last_update": datetime.fromtimestamp(
                self._progress.last_update_time
            ).isoformat(),
        }

        # Add current chapter details
        if self._progress.current_chapter in self._progress.chapters:
            current_chapter = self._progress.chapters[self._progress.current_chapter]
            summary["current_chapter_progress"] = {
                "progress": current_chapter.progress_percentage,
                "completed_chunks": current_chapter.completed_chunks,
                "total_chunks": current_chapter.total_chunks,
                "estimated_remaining_time": current_chapter.estimate_remaining_time(),
                "error_count": current_chapter.error_count,
            }

        return summary