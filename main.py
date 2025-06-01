import argparse
import re
import yaml
import json
import time
from pathlib import Path
from typing import Optional

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

# LlamaIndex imports
from llama_index.core.llms import LLM
from llama_index.llms.openai import OpenAI
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.gemini import Gemini
from llama_index.llms.ollama import Ollama


def read_config(config_file):
    with open(config_file, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


def split_html_by_sentence(html_str, max_chunk_size=20000):
    sentences = html_str.split(". ")

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) > max_chunk_size:
            chunks.append(current_chunk)
            current_chunk = sentence
        else:
            current_chunk += ". "
            current_chunk += sentence

    if current_chunk:
        chunks.append(current_chunk)

    # Remove dot from the beginning of first chunk
    if chunks and chunks[0].startswith(". "):
        chunks[0] = chunks[0][2:]

    # Add dot to the end of each chunk
    for i in range(len(chunks)):
        if not chunks[i].endswith("."):
            chunks[i] += "."

    return chunks


def system_prompt(from_lang: str, to_lang: str) -> str:
    return (
        f"You are an {from_lang}-to-{to_lang} specialized translator. "
        f"Keep all special characters and HTML tags exactly as in the source text. "
        f"Your translation should be in {to_lang} only. "
        f"Ensure the translation is comfortable to read by avoiding overly literal translations. "
        f"Maintain readability and consistency with the source text. "
        f"Do not add any explanations or comments, just provide the translation."
    )


def translate_chunk(
    llm: LLM,
    text: str,
    from_lang: str = "EN",
    to_lang: str = "BG",
    max_retries: int = 3,
    retry_delay: int = 180,
) -> str | None:
    prompt = f"{system_prompt(from_lang, to_lang)}\n\nText to translate:\n{text}"

    for attempt in range(max_retries):
        try:
            response = llm.complete(prompt)
            return response.text.strip()
        except Exception as e:
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                if attempt < max_retries - 1:
                    print(
                        f"Rate limit hit. Waiting {retry_delay} seconds before retry {attempt + 1}/{max_retries}"
                    )
                    time.sleep(retry_delay)
                    continue
            print(f"Error in translation attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(5)  # Short delay before retry


def save_progress(progress_file, chapter, chunk_index, total_chunks):
    with open(progress_file, "w") as f:
        json.dump(
            {
                "chapter": chapter,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "timestamp": time.time(),
            },
            f,
        )


def load_progress(progress_file):
    if Path(progress_file).exists():
        with open(progress_file, "r") as f:
            return json.load(f)
    return None


def translate_text(
    llm: LLM,
    text: str,
    from_lang: str = "English",
    to_lang: str = "Hungarian",
    progress_file: Optional[str] = None,
    chapter: Optional[int] = None,
) -> str:
    translated_chunks = []
    chunks = split_html_by_sentence(text)

    # Load progress if available
    start_chunk = 0
    if progress_file and chapter is not None:
        progress = load_progress(progress_file)
        if progress and progress["chapter"] == chapter:
            start_chunk = progress["chunk_index"]
            translated_chunks = [
                ""
            ] * start_chunk  # Placeholder for already translated chunks

    for i, chunk in enumerate(chunks[start_chunk:], start=start_chunk):
        print(f"\tTranslating chunk {i + 1}/{len(chunks)}...")
        try:
            translated_chunk = translate_chunk(llm, chunk, from_lang, to_lang)
            translated_chunks.append(translated_chunk)

            if progress_file and chapter is not None:
                save_progress(progress_file, chapter, i + 1, len(chunks))

        except Exception as e:
            print(f"Error translating chunk {i + 1}: {str(e)}")
            raise

    return " ".join(translated_chunks)


def translate(
    llm: LLM,
    input_epub_path: str,
    output_epub_path: str,
    from_chapter: int = 0,
    to_chapter: int = 9999,
    from_lang: str = "EN",
    to_lang: str = "HU",
    progress_file: Optional[str] = None,
):
    book = epub.read_epub(input_epub_path)

    current_chapter = 1
    chapters_count = len(
        [i for i in book.get_items() if i.get_type() == ebooklib.ITEM_DOCUMENT]
    )

    try:
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                if from_chapter <= current_chapter <= to_chapter:
                    print(
                        "Processing chapter %d/%d..."
                        % (current_chapter, chapters_count)
                    )
                    soup = BeautifulSoup(item.content, "html.parser")
                    translated_text = translate_text(
                        llm,
                        str(soup),
                        from_lang,
                        to_lang,
                        progress_file,
                        current_chapter,
                    )
                    item.content = translated_text.encode("utf-8")

                    # Save intermediate progress after each chapter
                    epub.write_epub(f"{output_epub_path}.partial", book, {})

                current_chapter += 1

        # Clean up progress file and write final epub
        if progress_file is not None and Path(progress_file).exists():
            Path(progress_file).unlink()
        if Path(f"{output_epub_path}.partial").exists():
            Path(f"{output_epub_path}.partial").unlink()

        epub.write_epub(output_epub_path, book, {})

    except Exception as e:
        print(f"Translation interrupted: {str(e)}")
        print(
            f"Progress saved. You can resume from chapter {current_chapter} using --from-chapter {current_chapter}"
        )
        # Keep the progress file and partial epub in case of error
        raise


def show_chapters(input_epub_path):
    book = epub.read_epub(input_epub_path)

    total_characters = 0
    current_chapter = 1
    chapters_count = len(
        [i for i in book.get_items() if i.get_type() == ebooklib.ITEM_DOCUMENT]
    )

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            chapter_length = len(item.content)
            total_characters += chapter_length
            print(
                f"▶️  Chapter {current_chapter}/{chapters_count} ({chapter_length} characters)"
            )
            soup = BeautifulSoup(item.content, "html.parser")
            chapter_beginning = soup.text[0:250]
            chapter_beginning = re.sub(r"\n{2,}", "\n", chapter_beginning)
            print(chapter_beginning + "\n\n")

            current_chapter += 1

    print(f"Total characters in the book: {total_characters}")


def initialize_llm_client(provider: str, config: dict) -> LLM:
    """
    Initialize the LLM client based on the provider.
    """
    if provider == "openai":
        api_key = config["openai"]["api_key"]
        model = config["openai"].get("model", "gpt-4o")
        print(f"Initializing OpenAI with model: {model}")
        return OpenAI(
            api_key=api_key,
            model=model,
            temperature=0.2,
        )

    elif provider == "azure":
        api_key = config["azure"]["api_key"]
        azure_endpoint = config["azure"]["endpoint"]
        api_version = config["azure"].get("api_version", "2024-02-01")
        deployment_name = config["azure"]["deployment_name"]
        print(f"Initializing Azure OpenAI with deployment: {deployment_name}")
        return AzureOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
            deployment_name=deployment_name,
            temperature=0.2,
        )

    elif provider == "gemini":
        api_key = config["gemini"]["api_key"]
        model = config["gemini"].get("model", "gemini-1.5-flash")
        print(f"Initializing Gemini with model: {model}")
        return Gemini(
            api_key=api_key,
            model=model,
            temperature=0.2,
        )

    elif provider == "ollama":
        model = config["ollama"].get("model", "llama3.1")
        base_url = config["ollama"].get("base_url", "http://localhost:11434")
        print(f"Initializing Ollama with model: {model} at {base_url}")
        return Ollama(
            model=model,
            base_url=base_url,
            temperature=0.2,
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")


if __name__ == "__main__":
    # Create the top-level parser
    parser = argparse.ArgumentParser(
        description="App to translate or show chapters of a book using LlamaIndex."
    )
    subparsers = parser.add_subparsers(dest="mode", help="Mode of operation.")

    # Create the parser for the "translate" mode
    parser_translate = subparsers.add_parser("translate", help="Translate a book.")
    parser_translate.add_argument("--input", required=True, help="Input file path.")
    parser_translate.add_argument("--output", required=True, help="Output file path.")
    parser_translate.add_argument(
        "--config", required=True, help="Configuration file path."
    )
    parser_translate.add_argument(
        "--from-chapter", type=int, help="Starting chapter for translation."
    )
    parser_translate.add_argument(
        "--to-chapter", type=int, help="Ending chapter for translation."
    )
    parser_translate.add_argument("--from-lang", help="Source language.", default="EN")
    parser_translate.add_argument("--to-lang", help="Target language.", default="PL")
    parser_translate.add_argument(
        "--progress-file", help="File to save translation progress."
    )
    parser_translate.add_argument(
        "--llm-provider",
        choices=["openai", "azure", "gemini", "ollama"],
        required=True,
        help="LLM provider to use for translation.",
    )

    # Create the parser for the "show-chapters" mode
    parser_show = subparsers.add_parser(
        "show-chapters", help="Show the list of chapters."
    )
    parser_show.add_argument("--input", required=True, help="Input file path.")

    # Parse the arguments
    args = parser.parse_args()

    # Call the appropriate function based on the mode
    if args.mode == "translate":
        config = read_config(args.config)
        from_chapter = int(args.from_chapter or 0)
        to_chapter = int(args.to_chapter or 9999)
        from_lang = args.from_lang
        to_lang = args.to_lang

        llm_client = initialize_llm_client(args.llm_provider, config)

        # Perform translation
        translate(
            llm_client,
            args.input,
            args.output,
            from_chapter,
            to_chapter,
            from_lang,
            to_lang,
            args.progress_file,
        )

    elif args.mode == "show-chapters":
        show_chapters(args.input)

    else:
        parser.print_help()
