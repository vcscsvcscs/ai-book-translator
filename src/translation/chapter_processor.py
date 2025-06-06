"""
Handles chapter processing and translation.
"""
from bs4 import BeautifulSoup
import re
import time
from .chunker import TextChunker
from utils.exceptions import TranslationError


class ChapterProcessor:
    """Processes individual chapters for translation."""
    
    def __init__(
        self, llm, chunk_size, max_retries, retry_delay, extra_prompts, progress_tracker
    ):
        self.llm = llm
        self.chunker = TextChunker(chunk_size)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_prompts = extra_prompts
        self.progress_tracker = progress_tracker

    def process_chapter(self, item, from_lang, to_lang, chapter_num):
        """Process and translate a single chapter."""
        try:
            soup = BeautifulSoup(item.content, "html.parser")
            text = self._extract_clean_text(soup)
            
            # Debug: Check if we extracted any text
            if not text or not text.strip():
                print(f"⚠️  Warning: No text extracted from chapter {chapter_num}")
                return {
                    "number": chapter_num,
                    "title": self._extract_chapter_title(soup, chapter_num),
                    "content": "",
                }
            
            print(f"  📄 Extracted {len(text)} characters from chapter {chapter_num}")
            
            chunks = self.chunker.split_text(text)
            total_chunks = len(chunks)
            print(f"  📄 Split into {total_chunks} chunks")
            
            # Initialize progress tracking for this chapter
            if self.progress_tracker:
                self.progress_tracker.start_chapter(chapter_num, total_chunks)
            
            translated_chunks = []
            for i, chunk in enumerate(chunks):
                print(f"    🔄 Chunk {i + 1}/{total_chunks}...")
                
                # Check if this chunk was already completed (resume functionality)
                if self.progress_tracker and self.progress_tracker.get_chapter_progress(chapter_num) > i:
                    print(f"    ✅ Chunk {i + 1} already completed (resuming)")
                    continue
                
                try:
                    translated_chunk = self._translate_chunk(chunk, from_lang, to_lang)
                    translated_chunks.append(translated_chunk)
                    
                    # Update progress
                    if self.progress_tracker:
                        self.progress_tracker.update_progress(chapter_num, i + 1, total_chunks)
                    
                    print(f"    ✅ Chunk {i + 1} completed")
                    
                except Exception as e:
                    error_msg = f"Failed to translate chunk {i + 1} in chapter {chapter_num}: {e}"
                    print(f"    ❌ {error_msg}")
                    
                    if self.progress_tracker:
                        self.progress_tracker.record_error(chapter_num, error_msg)
                    
                    # Re-raise the exception to stop processing
                    raise TranslationError(error_msg)
            
            # Complete the chapter
            if self.progress_tracker:
                self.progress_tracker.complete_chapter(chapter_num)
            
            # Join all translated chunks
            full_content = "\n\n".join(translated_chunks)
            
            # Debug: Check if we have any translated content
            if not full_content.strip():
                print(f"⚠️  Warning: No translated content for chapter {chapter_num}")
            else:
                print(f"  ✅ Chapter {chapter_num} translated: {len(full_content)} characters")
            
            return {
                "number": chapter_num,
                "title": self._extract_chapter_title(soup, chapter_num),
                "content": full_content,
            }
            
        except Exception as e:
            error_msg = f"Failed to process chapter {chapter_num}: {e}"
            print(f"❌ {error_msg}")
            
            if self.progress_tracker:
                self.progress_tracker.record_error(chapter_num, error_msg)
            
            raise TranslationError(error_msg)

    def _extract_clean_text(self, soup):
        """Extract clean text from HTML."""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text(separator="\n\n", strip=True)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Debug output
        print(f"    📝 Extracted text preview: {text[:200]}..." if text else "    ⚠️  No text extracted")
        
        return text

    def _create_translation_prompt(self, text: str, from_lang: str, to_lang: str) -> str:
        """Create translation prompt."""
        return (
            f"You are a professional {from_lang}-to-{to_lang} translator. "
            f"Translate the following text naturally and fluently to {to_lang}. "
            f"{self.extra_prompts} "
            f"Maintain readability and consistency with the source text while making it read naturally in {to_lang}. "
            f"Do not add explanations, comments, or notes - only provide the translation.\n\n"
            f"Text to translate:\n{text}"
        )

    def _translate_chunk(self, text, from_lang, to_lang):
        """Translate a single chunk."""
        if not text or not text.strip():
            print("    ⚠️  Empty chunk, skipping translation")
            return ""
        
        prompt = self._create_translation_prompt(text, from_lang, to_lang)
        
        for attempt in range(self.max_retries):
            try:
                print(f"      🔄 Translation attempt {attempt + 1}/{self.max_retries}")
                
                # Call LLM
                result = self.llm.complete(prompt)
                
                # Extract text from result
                if hasattr(result, 'text'):
                    translated_text = result.text.strip()
                elif isinstance(result, str):
                    translated_text = result.strip()
                else:
                    translated_text = str(result).strip()
                
                # Validate translation
                if not translated_text:
                    raise Exception("Empty translation returned from LLM")
                
                print(f"      ✅ Translation successful: {len(translated_text)} characters")
                return translated_text
                
            except Exception as e:
                print(f"      ⚠️  Attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    print(f"      ⏳ Waiting {self.retry_delay} seconds before retry...")
                    time.sleep(self.retry_delay)
                else:
                    raise e
        
        raise TranslationError(f"Failed to translate chunk after {self.max_retries} attempts")

    def _extract_chapter_title(self, soup, chapter_num: int) -> str:
        """Extract chapter title from soup or use fallback."""
        try:
            # Try to find title in various elements
            title_elem = soup.find(["h1", "h2", "h3", "title"])
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) < 100:  # Reasonable title length
                    return title
            
            # Try to find in any element with 'title' or 'chapter' in class/id
            for elem in soup.find_all(attrs={'class': re.compile(r'title|chapter', re.I)}):
                title = elem.get_text(strip=True)
                if title and len(title) < 100:
                    return title
            
            for elem in soup.find_all(attrs={'id': re.compile(r'title|chapter', re.I)}):
                title = elem.get_text(strip=True)
                if title and len(title) < 100:
                    return title
                    
        except Exception as e:
            print(f"    ⚠️  Could not extract title: {e}")
        
        # Fallback to chapter number
        return f"Chapter {chapter_num}"