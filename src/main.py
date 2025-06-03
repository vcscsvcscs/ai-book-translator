#!/usr/bin/env python3
"""
Main CLI entry point for the book translator.
"""

import argparse
import sys

from config.config_loader import ConfigLoader
from llm.factory import LLMFactory
from translation.translator import BookTranslator
from epub.reader import EPUBReader
from epub.analyzer import EnhancedEpubAnalyzer
from utils.exceptions import TranslationError, ConfigurationError


def create_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Translate eBooks using various LLM providers via LlamaIndex.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show chapters
  python main.py show-chapters --input book.epub

  # Translate with OpenAI
  python main.py translate --input book.epub --output translated.epub 
                 --config config.yaml --llm-provider openai --from-lang EN --to-lang PL

  # Resume translation
  python main.py translate --input book.epub --output translated.epub 
                 --config config.yaml --llm-provider openai --from-chapter 5
        """,
    )

    subparsers = parser.add_subparsers(dest="mode", help="Mode of operation")

    # Translate command
    translate_parser = subparsers.add_parser("translate", help="Translate a book")
    translate_parser.add_argument("--input", required=True, help="Input EPUB file path")
    translate_parser.add_argument(
        "--output", required=True, help="Output EPUB file path"
    )
    translate_parser.add_argument(
        "--config", required=True, help="Configuration file path"
    )
    translate_parser.add_argument(
        "--from-chapter", type=int, help="Starting chapter (1-based)"
    )
    translate_parser.add_argument(
        "--to-chapter", type=int, help="Ending chapter (1-based)"
    )
    translate_parser.add_argument(
        "--from-lang", default="EN", help="Source language code"
    )
    translate_parser.add_argument(
        "--to-lang", default="PL", help="Target language code"
    )
    translate_parser.add_argument(
        "--progress-file",
        help="File to save translation progress",
        default="data/progress.json",
    )
    translate_parser.add_argument(
        "--llm-provider",
        choices=["openai", "azure", "gemini", "ollama"],
        required=True,
        help="LLM provider to use",
    )
    translate_parser.add_argument(
        "--chunk-size",
        type=int,
        default=20000,
        help="Maximum chunk size for translation",
    )
    translate_parser.add_argument(
        "--max-retries", type=int, default=3, help="Maximum retry attempts"
    )
    translate_parser.add_argument(
        "--extra-prompts",
        type=str,
        default="Preserve paragraph breaks and formatting structure. ",
        help="Extra prompts for translation",
    )

    # Show chapters command
    show_parser = subparsers.add_parser(
        "show-chapters", help="Analyze and show book chapters"
    )
    show_parser.add_argument("--input", required=True, help="Input EPUB file path")
    show_parser.add_argument(
        "--detailed", action="store_true", help="Show detailed chapter info"
    )
    show_parser.add_argument(
        "--model",
        default="gpt-4o",
        help="Model name for tokenization (default: gpt-4o)",
    )
    show_parser.add_argument(
        "--from-lang", default="en", help="Source language code (default: en)"
    )
    show_parser.add_argument(
        "--to-lang", help="Target language code for translation cost estimation"
    )

    return parser


def handle_show_chapters(args):
    """Handle show-chapters command."""
    try:
        # Create EPUBReader first
        reader = EPUBReader(args.input)

        # Create analyzer with the reader
        analyzer = EnhancedEpubAnalyzer(reader, args.model)

        # Show chapters with optional translation estimation
        analyzer.show_chapters(
            detailed=args.detailed,
            source_language=args.from_lang,
            target_language=args.to_lang,
        )

    except Exception as e:
        print(f"Error analyzing book: {e}")
        return 1
    return 0


def handle_translate(args):
    """Handle translate command."""
    try:
        # Load configuration
        config_loader = ConfigLoader(args.config)
        config = config_loader.load()

        # Create LLM instance
        llm_factory = LLMFactory(config)
        llm = llm_factory.create_llm(args.llm_provider)

        # Create translator
        translator = BookTranslator(
            llm=llm,
            chunk_size=args.chunk_size,
            max_retries=args.max_retries,
            extra_prompts=args.extra_prompts,
            progress_file=args.progress_file,
        )

        # Perform translation
        translator.translate_book(
            input_path=args.input,
            output_path=args.output,
            from_chapter=args.from_chapter or 1,
            to_chapter=args.to_chapter or 9999,
            from_lang=args.from_lang,
            to_lang=args.to_lang,
        )

        print(f"✅ Translation completed successfully: {args.output}")

    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        return 1
    except TranslationError as e:
        print(f"❌ Translation error: {e}")
        return 1
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

    return 0


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        return 1

    if args.mode == "show-chapters":
        return handle_show_chapters(args)
    elif args.mode == "translate":
        return handle_translate(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
