"""
Qwen LLM provider implementation for local Qwen2 models (e.g., PULI-Trio-Q).
"""
from typing import Dict, Any, Optional
from llama_index.core.llms import LLM
from ..base import BaseLLMProvider
from utils.exceptions import ConfigurationError

try:
    from transformers import Qwen2ForCausalLM, AutoTokenizer
    import torch
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    Qwen2ForCausalLM = None
    AutoTokenizer = None
    torch = None


class QwenLLMWrapper(LLM):
    """Custom wrapper for Qwen2 models."""
    
    def __init__(
        self,
        model_name: str,
        device_map: str = "auto",
        max_new_tokens: int = 512,
        temperature: float = 0.2,
        max_seq_length: int = 32768,
        **kwargs
    ):
        if not HAS_TRANSFORMERS:
            raise ConfigurationError(
                "transformers library is required for Qwen provider. "
                "Install with: pip install transformers torch accelerate"
            )
        
        super().__init__(**kwargs)
        self._model_name = model_name
        self._device_map = device_map
        self._max_new_tokens = max_new_tokens
        self._temperature = temperature
        self._max_seq_length = max_seq_length  # PULI-Trio-Q max_seq_length = 32768
        
        print(f"🤖 Loading Qwen model: {model_name}")
        
        # Determine device (Mac MPS support)
        if torch.backends.mps.is_available():
            self._device = torch.device("mps")
            print(f"   Using MPS (Metal Performance Shaders)")
        elif torch.cuda.is_available():
            self._device = torch.device("cuda")
            print(f"   Using CUDA")
        else:
            self._device = torch.device("cpu")
            print(f"   Using CPU")
        
        # Load tokenizer (matching PULI README example)
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        # Load model (matching working Mac example)
        print(f"   Using Qwen2ForCausalLM for {model_name}")
        # Use float16 for MPS/CUDA, float32 for CPU
        dtype = torch.float16 if self._device.type != "cpu" else torch.float32
        
        self._model = Qwen2ForCausalLM.from_pretrained(
            model_name,
            torch_dtype=dtype,
            device_map="auto",
            trust_remote_code=True,
        ).to(self._device)
        
    def complete(self, prompt: str, **kwargs) -> Any:
        """Generate completion for the given prompt using model.generate() (Mac optimized)."""
        from llama_index.core.base.llms.types import CompletionResponse
        
        max_new_tokens = kwargs.get("max_new_tokens", self._max_new_tokens)
        temperature = kwargs.get("temperature", self._temperature)
        
        # Check if prompt exceeds max_seq_length (PULI-Trio-Q limit: 32768)
        # Tokenize the prompt to check length
        prompt_tokens = self._tokenizer.encode(prompt, add_special_tokens=False)
        prompt_length = len(prompt_tokens)
        
        # Calculate total sequence length (prompt + max_new_tokens)
        total_length = prompt_length + max_new_tokens
        
        if total_length > self._max_seq_length:
            # Warn and adjust max_new_tokens if needed
            available_tokens = self._max_seq_length - prompt_length
            if available_tokens < 1:
                raise ConfigurationError(
                    f"Prompt too long: {prompt_length} tokens exceeds max_seq_length "
                    f"({self._max_seq_length}). Please reduce the input size."
                )
            
            print(
                f"⚠️  Warning: Prompt ({prompt_length} tokens) + max_new_tokens ({max_new_tokens}) "
                f"exceeds max_seq_length ({self._max_seq_length}). "
                f"Reducing max_new_tokens to {available_tokens}."
            )
            max_new_tokens = max(1, available_tokens - 100)  # Leave some buffer
        
        # Tokenize input and move to device (Mac optimized approach)
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
        
        # Generate text using model.generate() (matching working Mac example)
        # Use lower temperature for better translation quality
        generate_kwargs = {
            "max_new_tokens": max_new_tokens,
            "do_sample": temperature > 0,
        }
        
        if temperature > 0:
            generate_kwargs["temperature"] = temperature
        else:
            # Use greedy decoding for better consistency when temperature is 0
            generate_kwargs["do_sample"] = False
        
        # Add any additional kwargs (excluding ones we've already handled)
        for key, value in kwargs.items():
            if key not in ["max_new_tokens", "temperature"]:
                generate_kwargs[key] = value
        
        # Generate using model.generate() (works better on Mac with MPS)
        with torch.no_grad():
            outputs = self._model.generate(**inputs, **generate_kwargs)
        
        # Decode the output
        generated_text = self._tokenizer.decode(outputs[0], skip_special_tokens=False)
        
        # Extract only the generated part (remove the prompt)
        # First try to find "Translation in HU:" or "Translation:" marker (for translation prompts)
        if "Translation in HU:" in generated_text:
            generated_text = generated_text.split("Translation in HU:")[-1].strip()
        elif "Translation in EN:" in generated_text:
            generated_text = generated_text.split("Translation in EN:")[-1].strip()
        elif "Translation:" in generated_text:
            generated_text = generated_text.split("Translation:")[-1].strip()
        elif prompt in generated_text:
            generated_text = generated_text.split(prompt, 1)[-1].strip()
        
        # Remove special tokens
        generated_text = generated_text.replace("<|im_end|>", "").replace("<|im_start|>", "").strip()
        
        # Clean up any remaining prompt fragments
        if "Text to translate:" in generated_text:
            generated_text = generated_text.split("Text to translate:")[-1].strip()
        
        return CompletionResponse(text=generated_text)
    
    async def acomplete(self, prompt: str, **kwargs) -> Any:
        """Async completion (not implemented for local models)."""
        return self.complete(prompt, **kwargs)
    
    def chat(self, messages, **kwargs):
        """Chat completion - convert messages to prompt and use complete."""
        # Convert messages to a single prompt
        prompt = ""
        for msg in messages:
            role = msg.role if hasattr(msg, 'role') else msg.get('role', 'user')
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            prompt += f"{role}: {content}\n"
        
        response = self.complete(prompt, **kwargs)
        from llama_index.core.base.llms.types import ChatResponse, ChatMessage, MessageRole
        
        return ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=response.text)
        )
    
    async def achat(self, messages, **kwargs):
        """Async chat completion."""
        return self.chat(messages, **kwargs)
    
    def stream_complete(self, prompt: str, **kwargs):
        """Stream completion - not implemented, fallback to complete."""
        response = self.complete(prompt, **kwargs)
        yield response
    
    async def astream_complete(self, prompt: str, **kwargs):
        """Async stream completion."""
        response = await self.acomplete(prompt, **kwargs)
        yield response
    
    def stream_chat(self, messages, **kwargs):
        """Stream chat - not implemented, fallback to chat."""
        response = self.chat(messages, **kwargs)
        yield response
    
    async def astream_chat(self, messages, **kwargs):
        """Async stream chat."""
        response = await self.achat(messages, **kwargs)
        yield response
    
    @property
    def metadata(self):
        """Return model metadata."""
        from llama_index.core.llms.types import LLMMetadata
        return LLMMetadata(
            model_name=str(self._model_name),
            context_window=self._max_seq_length,
            num_output=self._max_new_tokens,
        )


class QwenProvider(BaseLLMProvider):
    """Qwen LLM provider for local Qwen2 models."""
    
    @staticmethod
    def create_llm(config: Dict[str, Any]) -> LLM:
        """Create Qwen LLM instance."""
        QwenProvider.validate_config(config)
        
        model_name = config.get("model", "NYTK/PULI-Trio-Q")
        device_map = config.get("device_map", "auto")
        max_new_tokens = config.get("max_new_tokens", 512)
        temperature = config.get("temperature", 0.2)
        max_seq_length = config.get("max_seq_length", 32768)  # PULI-Trio-Q default
        
        print(f"🤖 Initializing Qwen with model: {model_name}")
        if "puli" in model_name.lower():
            print(f"   PULI-Trio-Q max_seq_length: {max_seq_length} tokens")
        
        return QwenLLMWrapper(
            model_name=model_name,
            device_map=device_map,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            max_seq_length=max_seq_length,
        )
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate Qwen configuration."""
        required_keys = QwenProvider.get_required_config_keys()
        
        for key in required_keys:
            if key not in config or not config[key]:
                raise ConfigurationError(f"Qwen {key} is required")
        
        # Validate model name
        model = config.get("model", "NYTK/PULI-Trio-Q")
        if not isinstance(model, str) or not model:
            raise ConfigurationError("Qwen model must be a non-empty string")
        
        # Validate device_map if specified
        device_map = config.get("device_map", "auto")
        valid_device_maps = ["auto", "cpu", "cuda", "cuda:0", "cuda:1"]
        if device_map not in valid_device_maps and not device_map.startswith("cuda:"):
            print(
                f"⚠️  Warning: device_map '{device_map}' not in common values: {valid_device_maps}. "
                "Make sure it's valid for your setup."
            )
        
        # Check if transformers is available
        if not HAS_TRANSFORMERS:
            raise ConfigurationError(
                "transformers library is required for Qwen provider. "
                "Install with: pip install transformers torch accelerate"
            )
        
        return True
    
    @staticmethod
    def get_required_config_keys() -> list:
        """Return required configuration keys."""
        return ["model"]
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "model": "NYTK/PULI-Trio-Q",
            "device_map": "auto",
            "max_new_tokens": 512,
            "temperature": 0.2,
            "max_seq_length": 32768,  # PULI-Trio-Q max_seq_length = 32768
        }

