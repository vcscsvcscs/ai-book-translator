"""
Example usage of Qwen2ForCausalLM with PULI-Trio-Q model.
This matches the example from the PULI README.
Optimized for Mac with MPS (Metal Performance Shaders).
"""
from transformers import Qwen2ForCausalLM, AutoTokenizer
import torch

# Determine device (matching the working Mac example)
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Using device: {device.type}")

# Load model and tokenizer
print("Loading model...")
model = Qwen2ForCausalLM.from_pretrained(
    "NYTK/PULI-Trio-Q",
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
).to(device)

tokenizer = AutoTokenizer.from_pretrained("NYTK/PULI-Trio-Q", trust_remote_code=True)

# Test prompt
prompt = "Elmesélek egy történetet a nyelvtechnológiáról."

print(f"\nGenerating text with prompt: {prompt}")
print("-" * 80)

# Tokenize input and move to device
inputs = tokenizer(prompt, return_tensors="pt").to(device)

# Generate text (matching PULI README example)
print("Generating...")
with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=30)

# Decode the output
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=False)

# Extract only the generated part (remove the prompt)
if prompt in generated_text:
    generated_text = generated_text.split(prompt, 1)[-1].strip()

# Remove special tokens
generated_text = generated_text.replace("<|im_end|>", "").replace("<|im_start|>", "").strip()

print("\nGenerated text:")
print(generated_text)

