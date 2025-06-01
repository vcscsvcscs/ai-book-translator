# Translate Books with LLMs using LlamaIndex

This project harnesses the power of LLMs through LlamaIndex to translate eBooks from any language into your preferred language, maintaining the integrity and structure of the original content. Imagine having access to a vast world of literature, regardless of the original language, right at your fingertips.

This tool not only translates the text but also carefully compiles each element of the eBook – chapters, footnotes, and all – into a perfectly formatted EPUB file. We now support multiple LLM providers through LlamaIndex for maximum flexibility and choice.

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
cp config.yaml config.yaml
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
  api_version: "2024-02-01"
  deployment_name: "your-deployment-name"
```

### Google Gemini
```yaml
gemini:
  api_key: "your-gemini-api-key"
  model: "gemini-1.5-flash"
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
python main.py show-chapters --input yourbook.epub
```

This command will display all the chapters, helping you to plan your translation process effectively.

### Translate Mode

#### Basic Usage with Different Providers

**Using OpenAI:**
```bash
python main.py translate --input yourbook.epub --output translatedbook.epub --config config.yaml --from-lang EN --to-lang PL --llm-provider openai
```

**Using Azure OpenAI:**
```bash
python main.py translate --input yourbook.epub --output translatedbook.epub --config config.yaml --from-lang EN --to-lang PL --llm-provider azure
```

**Using Google Gemini:**
```bash
python main.py translate --input yourbook.epub --output translatedbook.epub --config config.yaml --from-lang EN --to-lang PL --llm-provider gemini
```

**Using Ollama (Local):**
```bash
python main.py translate --input yourbook.epub --output translatedbook.epub --config config.yaml --from-lang EN --to-lang PL --llm-provider ollama
```

#### Advanced Usage

For more specific needs, such as translating from chapter 13 to chapter 37:

```bash
python main.py translate --input yourbook.epub --output translatedbook.epub --config config.yaml --from-chapter 13 --to-chapter 37 --from-lang EN --to-lang PL --llm-provider openai
```

#### Resume Translation

If translation is interrupted, you can resume from where it left off:

```bash
python main.py translate --input yourbook.epub --output translatedbook.epub --config config.yaml --from-chapter 25 --from-lang EN --to-lang PL --llm-provider openai --progress-file progress.json
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
- Gemini-1.5-flash is fast and cost-effective
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

## 🤝 Contributing

We warmly welcome contributions to this project! Your insights and improvements are invaluable. Currently, we're particularly interested in contributions in the following areas:

- Support for other eBook formats: AZW3, MOBI, PDF
- Integration of a built-in DeDRM tool
- Additional LLM providers
- Translation quality improvements
- Better error handling and recovery

Join us in breaking down language barriers in literature and enhancing the accessibility of eBooks worldwide!

## 📄 License

This project is open source. Please ensure you comply with the terms of service of your chosen LLM provider and respect copyright laws when translating books.