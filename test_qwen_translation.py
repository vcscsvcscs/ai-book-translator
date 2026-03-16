"""
Translation test using Qwen2ForCausalLM (PULI-Trio-Q) model.
Translates a sample text from the book from English to Hungarian.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from transformers import Qwen2ForCausalLM, AutoTokenizer
from epub.reader import EPUBReader

def load_model():
    """Load the Qwen model and tokenizer."""
    import torch
    
    # Determine device (matching the working Mac example)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"🤖 Using device: {device.type}")
    
    print("🤖 Loading Qwen model: NYTK/PULI-Trio-Q")
    model = Qwen2ForCausalLM.from_pretrained(
        "NYTK/PULI-Trio-Q",
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    ).to(device)
    
    tokenizer = AutoTokenizer.from_pretrained("NYTK/PULI-Trio-Q", trust_remote_code=True)
    
    return model, tokenizer, device

def extract_sample_text(epub_path: str, chapter_num: int = 2, max_length: int = 500) -> str:
    """Extract a sample text from the EPUB book."""
    print(f"📖 Reading EPUB: {epub_path}")
    reader = EPUBReader(epub_path)
    chapters = reader.get_chapters()
    
    if chapter_num > len(chapters):
        chapter_num = len(chapters)
    
    chapter = chapters[chapter_num - 1]
    text = chapter.text_content
    
    # Get first max_length characters
    if len(text) > max_length:
        # Try to cut at a sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind(".")
        last_exclamation = truncated.rfind("!")
        last_question = truncated.rfind("?")
        
        last_sentence = max(last_period, last_exclamation, last_question)
        if last_sentence > max_length * 0.7:
            text = text[:last_sentence + 1]
        else:
            text = truncated + "..."
    
    print(f"📄 Extracted text from Chapter {chapter_num} ({len(text)} characters):")
    print(f"   {text[:100]}...")
    print()
    
    return text

def translate_text(model, tokenizer, device, text: str, from_lang: str = "EN", to_lang: str = "HU") -> str:
    """Translate text using the Qwen model with Göncz Árpád style."""
    import torch
    
    # Create translation prompt matching the translator program structure
    # with Göncz Árpád style instruction
    base_prompt = (
        f"You are a professional {from_lang}-to-{to_lang} translator. "
        f"Translate the following text naturally and fluently to {to_lang}. "
        f"Translate in the style of Göncz Árpád, the renowned Hungarian translator and writer. "
        f"Göncz Árpád's translation style is characterized by: "
        f"elegant and refined language, precise word choice, maintaining the original's literary quality, "
        f"natural Hungarian flow, and preserving the author's voice and tone. "
        f"Preserve paragraph breaks and formatting structure. "
        f"Maintain readability and consistency with the source text while making it read naturally in {to_lang}. "
        f"Do not add explanations, comments, or notes - only provide the translation.\n\n"
        f"Text to translate:\n{text}"
    )
    
    print(f"🔄 Translating from {from_lang} to {to_lang} in Göncz Árpád style...")
    print(f"   Prompt length: {len(base_prompt)} characters")
    print()
    
    # Tokenize input and move to device
    inputs = tokenizer(base_prompt, return_tensors="pt").to(device)
    
    # Generate translation
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=512, temperature=0.2)
    
    # Decode the output
    translated_text = tokenizer.decode(outputs[0], skip_special_tokens=False)
    
    # Extract only the translation part (after "Text to translate:")
    if "Text to translate:" in translated_text:
        translated_text = translated_text.split("Text to translate:")[-1].strip()
        # Remove the original text if it's still there
        if text in translated_text:
            translated_text = translated_text.split(text, 1)[-1].strip()
    elif base_prompt in translated_text:
        # Fallback: extract everything after the prompt
        translated_text = translated_text.split(base_prompt, 1)[-1].strip()
    
    # Remove special tokens
    translated_text = translated_text.replace("<|im_end|>", "").replace("<|im_start|>", "").strip()
    
    return translated_text

def main():
    """Main function to run the translation test."""
    epub_path = "WenChaoGong-WarlockOfTheMagusWorld.epub"
    
    if not Path(epub_path).exists():
        print(f"❌ Error: EPUB file not found: {epub_path}")
        return
    
    try:
        # Load model
        model, tokenizer, device = load_model()
        print()
        
        # Extract sample text from chapter 2
        sample_text = extract_sample_text(epub_path, chapter_num=2, max_length=500)
        
        # Translate
        translated = translate_text(model, tokenizer, device, sample_text, from_lang="EN", to_lang="HU")
        
        # Print results
        print("=" * 80)
        print("ORIGINAL TEXT (English):")
        print("=" * 80)
        print(sample_text)
        print()
        print("=" * 80)
        print("TRANSLATED TEXT (Hungarian):")
        print("=" * 80)
        print(translated)
        print()
        print("=" * 80)
        print("✅ Translation test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

