# Translate Books with LLMs using LlamaIndex

This project harnesses the power of LLMs through LlamaIndex to translate eBooks from any language into your preferred language, maintaining the integrity and structure of the original content. Imagine having access to a vast world of literature, regardless of the original language, right at your fingertips.

This tool not only translates the text but also carefully compiles each element of the eBook – chapters, footnotes, and all – into perfectly formatted output files. We support multiple output formats (EPUB, PDF, Markdown) and multiple LLM providers through LlamaIndex for maximum flexibility and choice.

## 🚀 Supported LLM Providers

- **OpenAI**: GPT-4o, GPT-4o-mini, GPT-3.5-turbo and other OpenAI models
- **Azure OpenAI**: Use OpenAI models through Microsoft Azure
- **Google Gemini**: Gemini-1.5-flash, Gemini-1.5-pro and other Gemini models
- **Ollama**: Run local models like Llama 3.1, Mistral, CodeLlama, etc.

## 🛠️ Installation

To install the necessary components for our project, follow these simple steps:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
```

Remember to configure your API keys in `config.yaml` for the providers you want to use.

## ⚙️ Configuration

Edit `config.yaml` to add your API keys and configure models:

### OpenAI
```yaml
openai:
  api_key: "your-openai-api-key"
  model: "gpt-4o"
```

### Azure OpenAI
```yaml
azure:
  api_key: "your-azure-api-key"
  endpoint: "https://your-resource-name.openai.azure.com/"
  api_version: "2025-01-01-preview"
  deployment_name: "your-deployment-name"
```

### Google Gemini
```yaml
gemini:
  api_key: "your-gemini-api-key"
  model: "gemini-2.5-flash-preview-05-20"  # Options: gemini-1.5-flash, gemini-1.5-pro, etc.
```

### Ollama (Local)
```yaml
ollama:
  model: "llama3.1"
  base_url: "http://localhost:11434"
```

For Ollama, make sure you have Ollama installed and running locally with your desired model pulled.

## 🎮 Usage

Our script comes with a variety of parameters to suit your needs. Here's how you can make the most out of it:

### Show Chapters

Before diving into translation, it's recommended to use the `show-chapters` mode to review the structure of your book:

```bash
python -m src.main show-chapters --input yourbook.epub
```

**Additional options:**
- `--detailed`: Show detailed chapter statistics (word count, token count, etc.)
- `--model`: Model name for tokenization (default: gpt-4o)
- `--from-lang`: Source language code (default: en)
- `--to-lang`: Target language code for translation cost estimation

**Example with cost estimation:**
```bash
python -m src.main show-chapters --input yourbook.epub --detailed --from-lang EN --to-lang PL
```

This command will display all the chapters with statistics and cost estimates, helping you to plan your translation process effectively.

### Translate Mode

#### Basic Usage with Different Providers

**Using OpenAI:**
```bash
python -m src.main translate --input yourbook.epub --output translatedbook --config config.yaml --from-lang EN --to-lang PL --llm-provider openai
```

**Using Azure OpenAI:**
```bash
python -m src.main translate --input yourbook.epub --output translatedbook --config config.yaml --from-lang EN --to-lang PL --llm-provider azure
```

**Using Google Gemini:**
```bash
python -m src.main translate --input yourbook.epub --output translatedbook --config config.yaml --from-lang EN --to-lang PL --llm-provider gemini
```

**Using Ollama (Local):**
```bash
python -m src.main translate --input yourbook.epub --output translatedbook --config config.yaml --from-lang EN --to-lang PL --llm-provider ollama
```

**Note:** The output path should be specified without extension. The tool will generate files with appropriate extensions based on the selected output formats.

#### Output Formats

By default, the tool generates Markdown output. You can specify multiple output formats:

```bash
python -m src.main translate --input yourbook.epub --output translatedbook --config config.yaml --from-lang EN --to-lang PL --llm-provider openai --output-formats epub pdf markdown
```

Supported formats:
- `markdown` (default): Plain Markdown file
- `epub`: EPUB eBook format
- `pdf`: PDF document (requires `reportlab` package: `pip install reportlab`)

#### Advanced Usage

**Translate specific chapters:**
```bash
python -m src.main translate --input yourbook.epub --output translatedbook --config config.yaml --from-chapter 13 --to-chapter 37 --from-lang EN --to-lang PL --llm-provider openai
```

**Customize translation parameters:**
```bash
python -m src.main translate --input yourbook.epub --output translatedbook --config config.yaml --from-lang EN --to-lang PL --llm-provider openai --chunk-size 2000 --max-retries 5 --extra-prompts "Maintain formal tone and preserve technical terms."
```

**Available parameters:**
- `--chunk-size`: Maximum chunk size for translation (default: 1000)
- `--max-retries`: Maximum retry attempts for failed translations (default: 3)
- `--extra-prompts`: Additional instructions for the translation (default: "Preserve paragraph breaks and formatting structure.")
- `--output-formats`: Output formats to generate (default: markdown)
- `--progress-file`: File to save translation progress (default: data/progress.json)

#### Resume Translation

If translation is interrupted, you can resume from where it left off:

```bash
python -m src.main translate --input yourbook.epub --output translatedbook --config config.yaml --from-chapter 25 --from-lang EN --to-lang PL --llm-provider openai --progress-file data/progress.json
```

### Fix Filtered Chunks

Sometimes LLM providers may filter certain content chunks due to content policies. The `fix-chunks` command allows you to re-translate these filtered chunks:

```bash
python -m src.main fix-chunks --input yourbook.epub --output fixedbook --config config.yaml --progress-file data/progress.json --llm-provider openai --from-lang EN --to-lang PL
```

**Fixing strategies:**
- `--strategy original_prompt`: Retry with the original translation prompt (default)
- `--strategy alternative_prompt`: Use an alternative prompt with different wording

**Example:**
```bash
python -m src.main fix-chunks --input yourbook.epub --output fixedbook --config config.yaml --progress-file data/progress.json --llm-provider gemini --from-lang EN --to-lang PL --strategy alternative_prompt --output-formats epub markdown
```

## 📚 Language Codes

Use standard language codes for translation:
- EN: English
- PL: Polish  
- DE: German
- FR: French
- ES: Spanish
- IT: Italian
- PT: Portuguese
- RU: Russian
- JA: Japanese
- KO: Korean
- ZH: Chinese
- And many more...

## 🔧 Provider-Specific Notes

### OpenAI
- Requires an OpenAI API key
- Supports latest models including GPT-4o
- Generally provides high-quality translations

### Azure OpenAI
- Requires Azure subscription and OpenAI resource
- Use your deployment name, not the model name
- Provides enterprise-grade security and compliance

### Google Gemini
- Requires Google AI Studio API key
- Gemini-1.5-flash and Gemini-2.5-flash are fast and cost-effective
- Gemini-1.5-pro offers higher quality for complex translations

### Ollama
- Runs completely locally - no API costs
- Requires Ollama to be installed and running
- Pull models using: `ollama pull llama3.1`
- Slower than cloud providers but completely private

## 📖 Converting from AZW3 to EPUB

For books in AZW3 format (Amazon Kindle), use Calibre (https://calibre-ebook.com) to convert them to EPUB before using this tool.

## 🔐 DRM (Digital Rights Management)

Amazon eBooks (AZW3 format) are encrypted with your device's serial number. To decrypt these books, use the DeDRM tool (https://dedrm.com). You can find your Kindle's serial number at https://www.amazon.com/hz/mycd/digital-console/alldevices.

## 🚨 Error Handling

The tool includes robust error handling:
- **Rate limiting**: Automatically retries with delays
- **Progress saving**: Resume interrupted translations
- **Partial saves**: Intermediate progress is saved after each chapter
- **Multiple providers**: Switch providers if one fails
- **Content filtering**: Track and fix chunks blocked by content filters using the `fix-chunks` command
- **Chunk caching**: Translated chunks are cached to avoid re-translation

## 📝 Project Structure

The project is organized into the following modules:

- `src/main.py`: Main CLI entry point
- `src/config/`: Configuration loading and management
- `src/epub/`: EPUB reading, writing, and analysis
- `src/llm/`: LLM provider implementations (OpenAI, Azure, Gemini, Ollama)
- `src/translation/`: Core translation logic, chunking, caching, and progress tracking
- `src/translation/output/`: Output format generators (EPUB, PDF, Markdown)
- `src/utils/`: Utility functions for text processing, fonts, and exceptions

## 🤝 Contributing

We warmly welcome contributions to this project! Your insights and improvements are invaluable. Currently, we're particularly interested in contributions in the following areas:

- Support for other eBook formats: AZW3, MOBI
- Integration of a built-in DeDRM tool
- Additional LLM providers
- Translation quality improvements
- Better error handling and recovery
- Performance optimizations

Join us in breaking down language barriers in literature and enhancing the accessibility of eBooks worldwide!

## 📄 License

This project is open source. Please ensure you comply with the terms of service of your chosen LLM provider and respect copyright laws when translating books.