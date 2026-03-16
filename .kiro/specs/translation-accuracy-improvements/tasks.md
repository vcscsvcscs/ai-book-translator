# Translation Accuracy Improvements - Implementation Tasks

## Task List

- [x] 1. Update Project Model with New Fields
  - [x] 1.1 Add GenreContext field to Project struct
  - [x] 1.2 Add EnablePolishPass field to Project struct
  - [x] 1.3 Add MaxContextTokens field to Project struct with default 32000
  - [x] 1.4 Verify JSON serialization works with new fields
  - [x] 1.5 Test backward compatibility with existing project files

- [x] 2. Enhance System Prompt
  - [x] 2.1 Update BuildSystemPrompt() with accuracy-focused rules
  - [x] 2.2 Add anti-hallucination guard rule
  - [x] 2.3 Preserve style prompt section functionality
  - [x] 2.4 Test prompt generation with various language pairs

- [x] 3. Improve User Prompt
  - [x] 3.1 Update BuildUserMessage() signature to accept genre context
  - [x] 3.2 Add faithful translation instructions
  - [x] 3.3 Implement genre context injection before "Text:" section
  - [x] 3.4 Test with and without genre context

- [x] 4. Implement Sampling Defaults
  - [x] 4.1 Create applyDefault() helper function for float32
  - [x] 4.2 Create applyDefaultInt() helper function for int
  - [x] 4.3 Create computeMaxOutputTokens() helper function
  - [x] 4.4 Update translateChunk() to apply defaults when constructing LLMOptions
  - [x] 4.5 Add default stop tokens: ["\n\nText:", "<|im_end|>"]
  - [x] 4.6 Add default seed: 42
  - [x] 4.7 Test default application with zero-value ModelParams
  - [x] 4.8 Test that non-zero values are not overridden
  - [x] 4.9 Test computeMaxOutputTokens() with various chunk sizes

- [ ] 5. Add Chunk Size Validation
  - [ ] 5.1 Update validateChunkSize() function to accept maxContext parameter
  - [ ] 5.2 Add warning for chunks below 400 tokens
  - [ ] 5.3 Add warning for chunks exceeding maxContext/2
  - [ ] 5.4 Integrate validation into TranslateProject()
  - [ ] 5.5 Test warning appears for chunks below 400 tokens
  - [ ] 5.6 Test warning appears for chunks exceeding context window
  - [ ] 5.7 Test no warning for appropriately sized chunks

- [ ] 6. Implement Two-Pass Translation
  - [ ] 6.1 Create polishTranslation() function
  - [ ] 6.2 Implement polish system prompt
  - [ ] 6.3 Implement improved polish user prompt with strict rules
  - [ ] 6.4 Preserve streaming behavior in polish pass
  - [ ] 6.5 Integrate polish pass into translateChunk()
  - [ ] 6.6 Add error handling with fallback to initial translation
  - [ ] 6.7 Test two-pass flow with EnablePolishPass enabled
  - [ ] 6.8 Test single-pass flow with EnablePolishPass disabled
  - [ ] 6.9 Verify polish prompt prevents summarization

- [ ] 7. Update translateChunk() Integration
  - [ ] 7.1 Pass GenreContext to BuildUserMessage()
  - [ ] 7.2 Apply sampling defaults before backend.ChatStream()
  - [ ] 7.3 Use computeMaxOutputTokens() for dynamic token limits
  - [ ] 7.4 Conditionally call polishTranslation() based on EnablePolishPass
  - [ ] 7.5 Ensure all existing functionality preserved

- [ ] 8. Extend LLMOptions Structure
  - [ ] 8.1 Add Stop []string field to LLMOptions
  - [ ] 8.2 Add Seed int field to LLMOptions
  - [ ] 8.3 Update all LLMOptions construction sites
  - [ ] 8.4 Test backward compatibility

- [ ] 9. Update LLM Backend Implementations
  - [ ] 9.1 Update Ollama backend to pass Stop and Seed
  - [ ] 9.2 Update HTTP backend to pass Stop and Seed
  - [ ] 9.3 Update dlgo backend to pass Stop and Seed (if supported)
  - [ ] 9.4 Handle backends that don't support these features gracefully
  - [ ] 9.5 Test with each backend

- [ ] 10. Testing
  - [ ] 10.1 Write unit tests for BuildSystemPrompt()
  - [ ] 10.2 Write unit tests for BuildUserMessage()
  - [ ] 10.3 Write unit tests for applyDefault() helpers
  - [ ] 10.4 Write unit tests for computeMaxOutputTokens()
  - [ ] 10.5 Write unit tests for validateChunkSize()
  - [ ] 10.6 Write unit tests for polishTranslation()
  - [ ] 10.7 Write integration test for full translation flow
  - [ ] 10.8 Test backward compatibility with existing projects
  - [ ] 10.9 Test with Qwen 9B via Ollama (manual)

- [ ] 11. Documentation
  - [ ] 11.1 Add code comments for new functions
  - [ ] 11.2 Document new Project fields
  - [ ] 11.3 Document new LLMOptions fields
  - [ ] 11.4 Update function documentation for signature changes
  - [ ] 11.5 Add usage examples for local LLM configuration

## Task Details

### 1. Update Project Model with New Fields

**Files**: `internal/model/project.go`

**Description**: Add optional configuration fields for genre context, two-pass translation, and context window awareness.

**Implementation**:
```go
type Project struct {
    // ... existing fields ...
    
    GenreContext      string `json:"genre_context,omitempty"`
    EnablePolishPass  bool   `json:"enable_polish_pass"`
    MaxContextTokens  int    `json:"max_context_tokens,omitempty"`
}
```

**Acceptance Criteria**:
- Fields serialize/deserialize correctly
- Existing projects load without errors
- Zero values provide correct defaults (MaxContextTokens defaults to 32000)

### 2. Enhance System Prompt

**Files**: `internal/translator/prompt.go`

**Description**: Replace existing system prompt rules with accuracy-focused instructions and anti-hallucination guard.

**Key Changes**:
- Emphasize faithful translation
- Prohibit inventing details
- Prefer accuracy over creativity
- Add: "If a sentence is unclear, translate it literally rather than guessing."
- Maintain paragraph structure

**Acceptance Criteria**:
- New prompt prioritizes accuracy
- Anti-hallucination guard included
- Style prompt section preserved
- Works with all language pairs

### 3. Improve User Prompt

**Files**: `internal/translator/prompt.go`

**Description**: Strengthen user prompt instructions and add optional genre context.

**Signature Change**:
```go
func BuildUserMessage(sourceLang, targetLang, text, genreContext string) string
```

**Acceptance Criteria**:
- Includes faithful translation instruction
- Genre context appears before "Text:" when provided
- Empty genre context works correctly

### 4. Implement Sampling Defaults

**Files**: `internal/translator/translator.go`

**Description**: Apply translation-optimized defaults for zero-value parameters, including context-aware token limits.

**Defaults**:
- Temperature: 0.2
- TopP: 0.9
- TopK: 40
- RepetitionPenalty: 1.1
- Stop: ["\n\nText:", "<|im_end|>"]
- Seed: 42
- MaxTokens: computed dynamically based on context window

**Helper Functions**:
```go
func applyDefault(value, defaultValue float32) float32
func applyDefaultInt(value, defaultValue int) int
func computeMaxOutputTokens(chunkTokens int, maxContext int) int
```

**Acceptance Criteria**:
- Defaults applied only when value is zero
- Non-zero values not overridden
- computeMaxOutputTokens() prevents context overflow
- Works with all backends

### 5. Add Chunk Size Validation

**Files**: `internal/translator/translator.go`

**Description**: Warn users when chunk size is suboptimal for translation quality or may exceed context limits.

**Implementation**:
```go
func validateChunkSize(chunkSize int, maxContext int) {
    const recommendedMinTokens = 400
    
    if maxContext == 0 {
        maxContext = 32000
    }
    
    if chunkSize > 0 && chunkSize < recommendedMinTokens {
        log.Printf("Warning: chunk size below recommended translation length (%d tokens)", recommendedMinTokens)
    }
    
    if chunkSize > maxContext/2 {
        log.Printf("Warning: chunk size may exceed safe context window (chunk: %d, max context: %d)", chunkSize, maxContext)
    }
}
```

**Acceptance Criteria**:
- Warning logged for chunks < 400 tokens
- Warning logged for chunks > maxContext/2
- No warning for appropriately sized chunks
- Execution not blocked

### 6. Implement Two-Pass Translation

**Files**: `internal/translator/translator.go`

**Description**: Add optional polish pass to improve fluency while preserving meaning, with strict rules to prevent summarization.

**Components**:
1. `polishTranslation()` function
2. Polish system prompt
3. Improved polish user prompt with explicit rules
4. Integration with `translateChunk()`

**Polish User Prompt**:
```
Edit the following translation to improve fluency.

Rules:
- Preserve the exact meaning.
- Do not add or remove information.
- Do not shorten the text.
- Do not summarize.
- Only improve grammar and readability.

Translation:
{initial_translation}
```

**Acceptance Criteria**:
- Polish pass only runs when EnablePolishPass is true
- Streaming works during polish pass
- Falls back to initial translation on error
- Thinking tags handled correctly
- Polish prompt prevents summarization

### 7. Update translateChunk() Integration

**Files**: `internal/translator/translator.go`

**Description**: Integrate all new features into main translation logic.

**Changes**:
- Pass genre context to BuildUserMessage()
- Apply sampling defaults
- Use computeMaxOutputTokens() for dynamic limits
- Conditionally run polish pass
- Maintain existing error handling

**Acceptance Criteria**:
- All features work together
- Existing functionality preserved
- Progress reporting works correctly
- Context overflow prevented

### 8. Extend LLMOptions Structure

**Files**: `internal/translator/llm.go`

**Description**: Add fields for stop tokens and deterministic seed.

**Implementation**:
```go
type LLMOptions struct {
    // ... existing fields ...
    Stop []string // Stop sequences to prevent over-generation
    Seed int      // Deterministic seed for reproducibility
}
```

**Acceptance Criteria**:
- Fields added to LLMOptions
- All construction sites updated
- Backward compatible with existing code

### 9. Update LLM Backend Implementations

**Files**: `internal/translator/llm_ollama.go`, `internal/translator/llm_http.go`, `internal/translator/llm_dlgo.go`

**Description**: Update backends to pass Stop and Seed to LLM APIs.

**Implementation Notes**:
- Ollama: Pass via API request options
- HTTP: Pass via request body (if supported)
- dlgo: Check if supported, ignore gracefully if not

**Acceptance Criteria**:
- Stop tokens prevent over-generation in Ollama
- Seed enables reproducible output
- Backends without support handle gracefully
- No breaking changes to backend interfaces

### 10. Testing

**Files**: Create test files as needed

**Description**: Comprehensive testing of all new functionality.

**Test Coverage**:
- Unit tests for all new functions
- Integration tests for full flow
- Backward compatibility tests
- Edge case handling
- Manual testing with Qwen 9B

**Acceptance Criteria**:
- All tests pass
- Code coverage for new code > 80%
- No regressions in existing functionality
- Qwen 9B produces accurate translations

### 11. Documentation

**Files**: All modified files

**Description**: Add clear documentation for new features.

**Requirements**:
- Function comments follow Go conventions
- Complex logic explained
- Usage examples for local LLM configuration
- Document MaxContextTokens, Stop, and Seed fields

**Acceptance Criteria**:
- All public functions documented
- New fields explained
- Code is self-documenting
- Local LLM setup guide included

## Implementation Order

Recommended implementation sequence:

1. Start with LLMOptions extensions (Task 8) - foundation for other changes
2. Update Project model (Task 1) - add configuration fields
3. Update prompts (Tasks 2-3) - independent and testable
4. Add sampling defaults and helpers (Task 4) - includes computeMaxOutputTokens
5. Add validation (Task 5) - uses maxContext from Project
6. Update backends (Task 9) - pass Stop and Seed to APIs
7. Implement two-pass translation (Task 6) - most complex feature
8. Integrate everything (Task 7) - bring it all together
9. Testing (Task 10) - validate everything works
10. Documentation (Task 11) - finalize

## Testing Strategy

### Unit Tests
- Test each function in isolation
- Mock LLM backends for translation tests
- Verify edge cases and error handling

### Integration Tests
- Test full translation flow end-to-end
- Test with real project structures
- Verify backward compatibility

### Manual Testing
- Test with Qwen 9B via Ollama
- Compare translation quality
- Verify UI compatibility (if applicable)

## Success Criteria

- [ ] All tasks completed
- [ ] All tests passing
- [ ] No breaking changes to existing functionality
- [ ] Code follows project style guidelines
- [ ] Documentation complete and accurate
