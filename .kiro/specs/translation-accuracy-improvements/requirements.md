# Translation Accuracy Improvements for Local LLMs

## Overview
Improve translation accuracy and stability for local LLMs (such as Qwen 9B) running through Ollama by enhancing prompts, adding sampling defaults, implementing validation, and providing optional two-pass translation.

## User Stories

### 1. Improved System Prompt
**As a** user translating books with local LLMs  
**I want** the system prompt to prioritize accuracy over creativity  
**So that** translations faithfully preserve the original meaning without inventing details

### 2. Enhanced User Prompt
**As a** user translating literary content  
**I want** stronger translation instructions in the user prompt  
**So that** the model understands it must translate faithfully without summarizing

### 3. Fantasy Context Hint
**As a** user translating fantasy novels  
**I want** the ability to add genre context to prompts  
**So that** models better understand narrative elements like carriages, villages, and sects

### 4. Translation Sampling Defaults
**As a** user setting up a translation project  
**I want** sensible default sampling parameters for translation tasks  
**So that** I get accurate translations without manual parameter tuning

### 5. Chunk Size Validation
**As a** user configuring chunk sizes  
**I want** warnings when chunk size is too small  
**So that** I can avoid poor translation quality from insufficient context

### 6. Two-Pass Translation Mode
**As a** user seeking higher quality translations  
**I want** an optional polish pass after initial translation  
**So that** I can improve fluency while preserving meaning

### 7. Context Window Awareness
**As a** user working with local LLMs  
**I want** the system to respect model context limits  
**So that** translations don't fail due to context overflow

### 8. Stop Token Configuration
**As a** user translating with local models  
**I want** stop tokens to prevent over-generation  
**So that** models don't continue generating past the translation

### 9. Deterministic Translation
**As a** user needing reproducible results  
**I want** deterministic seed support  
**So that** I can reproduce translations consistently

## Acceptance Criteria

### 1.1 System Prompt Updates
- [ ] Replace existing system prompt rules with accuracy-focused rules
- [ ] System prompt must emphasize faithful translation over creative interpretation
- [ ] Rules must explicitly prohibit inventing or replacing objects, locations, or actions
- [ ] Rules must instruct to preserve exact meaning of every sentence
- [ ] Rules must maintain paragraph structure preservation
- [ ] Rules must keep character names and proper nouns unchanged
- [ ] Rules must prefer accuracy over creativity
- [ ] Style prompt section must be preserved exactly as before (appended under "Style:")

### 1.2 User Prompt Enhancement
- [ ] User prompt must include explicit instruction to translate faithfully
- [ ] User prompt must warn against summarizing or inventing details
- [ ] Format must be: "Translate the following text from {source} into {target}. Translate faithfully and preserve the meaning of every sentence. Do not summarize or invent new details."
- [ ] Text section must follow the instructions

### 1.3 Fantasy Context Hint
- [ ] Add configurable genre context option to Project model
- [ ] When enabled, insert "The text is from a fantasy novel." before "Text:" section
- [ ] Feature must be optional and disabled by default
- [ ] Must work with existing prompt building logic

### 1.4 Translation Sampling Defaults
- [ ] Apply default Temperature: 0.2 when ModelParams.Temperature is zero
- [ ] Apply default TopP: 0.9 when ModelParams.TopP is zero
- [ ] Apply default TopK: 40 when ModelParams.TopK is zero
- [ ] Apply default RepetitionPenalty: 1.1 when ModelParams.RepetitionPenalty is zero
- [ ] Defaults must be applied in translateChunk() when constructing LLMOptions
- [ ] Existing non-zero values must not be overridden
- [ ] Must maintain backward compatibility with existing projects

### 1.5 Chunk Size Validation
- [ ] Create helper function to validate chunk size
- [ ] Log warning when chunk size is below 400 tokens
- [ ] Warning message: "Warning: chunk size below recommended translation length (400 tokens)"
- [ ] Warning must not stop execution
- [ ] Validation must be called during project creation or chunk configuration

### 1.6 Two-Pass Translation Mode
- [ ] Add EnablePolishPass bool field to Project model
- [ ] When enabled, perform initial translation as normal
- [ ] After initial translation, send result back with polish prompt
- [ ] Polish prompt must include strict rules: preserve meaning, no additions/removals, no shortening, no summarizing
- [ ] Store polished version as final chunk translation
- [ ] Must preserve existing streaming behavior during both passes
- [ ] Must work with all LLM backends (Ollama, HTTP, dlgo)
- [ ] Polish pass must use same model and parameters as initial translation

### 1.7 Context Window Awareness
- [ ] Add MaxContextTokens field to Project model with default 32000
- [ ] Update validateChunkSize() to check against context window
- [ ] Warn when chunk size exceeds maxContext/2
- [ ] Implement computeMaxOutputTokens() helper function
- [ ] Reserve 1500 tokens for prompts and overhead
- [ ] Apply computed max tokens when constructing LLMOptions

### 1.8 Stop Token Configuration
- [ ] Add Stop []string field to LLMOptions
- [ ] Set default stop tokens: ["\n\nText:", "<|im_end|>"]
- [ ] Pass stop tokens to all LLM backends
- [ ] Prevent models from continuing past translation

### 1.9 Deterministic Seed Support
- [ ] Add Seed int field to LLMOptions
- [ ] Set default seed to 42 for reproducibility
- [ ] Pass seed to LLM backends that support it
- [ ] Document seed behavior for different backends

### 1.10 Anti-Hallucination Guard
- [ ] Add rule to system prompt: "If a sentence is unclear, translate it literally rather than guessing."
- [ ] Place rule after accuracy rules
- [ ] Test with ambiguous source text

### 1.11 Thinking Mode Default
- [ ] Ensure ThinkingMode defaults to disabled for translation tasks
- [ ] Verify StripThinkingTags() continues to work
- [ ] Document thinking mode behavior

## Non-Functional Requirements

### Backward Compatibility
- [ ] Must not change Project structure in breaking ways (only add fields)
- [ ] Must not change Store format in breaking ways
- [ ] Must not modify Backend interfaces
- [ ] Must not break existing provider integrations (Ollama, HTTP, dlgo)
- [ ] Existing projects must continue to work without migration

### Code Quality
- [ ] Follow existing Go code style in the project
- [ ] Add appropriate comments for new functions
- [ ] Maintain existing error handling patterns
- [ ] Keep functions focused and testable

### Streaming Behavior
- [ ] Must preserve existing streaming token logic
- [ ] Must not modify StripThinkingTags function
- [ ] Must not change streaming callback behavior
- [ ] Token-by-token progress reporting must continue to work

## Technical Constraints

- All changes must be in Go
- Must work with existing LLM backends without modification
- Must integrate with existing UI components without breaking them
- New Project fields must have sensible defaults for backward compatibility
- Validation warnings must use existing logging mechanisms

## Out of Scope

- Changes to UI components (focus on backend logic only)
- Changes to LLM backend implementations
- Changes to chunking algorithms
- Changes to export functionality
- Performance optimizations beyond sampling defaults
