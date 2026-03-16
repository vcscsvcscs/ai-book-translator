# Translation Accuracy Improvements - Design Document

## Overview
This design implements improvements to translation accuracy and stability for local LLMs (especially Qwen 9B via Ollama) by refining prompts, adding intelligent defaults, implementing validation, context window awareness, and providing optional two-pass translation.

## Key Improvements for Local LLMs

### 1. Context Window Management
- MaxContextTokens configuration (default: 32000)
- Dynamic output token budgeting with computeMaxOutputTokens()
- Validation warnings for chunks that may exceed context limits

### 2. Over-Generation Prevention
- Stop tokens: ["\n\nText:", "<|im_end|>"]
- Prevents models from continuing past the translation

### 3. Deterministic Output
- Seed parameter (default: 42)
- Enables reproducible translations for testing and debugging

### 4. Anti-Hallucination Measures
- Accuracy-focused system prompt
- Explicit rule: "If a sentence is unclear, translate it literally rather than guessing"
- Stricter polish pass prompt with no-summarization rules

### 5. Optimized Sampling Parameters
- Temperature: 0.2 (reduced creativity, increased consistency)
- TopP: 0.9 (balanced nucleus sampling)
- TopK: 40 (reasonable vocabulary constraint)
- RepetitionPenalty: 1.1 (prevents loops)

## Architecture

### Component Overview
The changes affect three main components:
1. **Prompt Builder** (`internal/translator/prompt.go`) - Enhanced prompt generation
2. **Translator** (`internal/translator/translator.go`) - Core translation logic with defaults and two-pass support
3. **Project Model** (`internal/model/project.go`) - Extended with new configuration fields

### Design Principles
- Backward compatibility: All changes are additive
- Zero-value defaults: New fields have sensible defaults
- Non-breaking: Existing projects continue to work unchanged
- Minimal surface area: Changes isolated to translation logic

## Detailed Design

### 1. System Prompt Enhancement

**File**: `internal/translator/prompt.go`

**Function**: `BuildSystemPrompt(sourceLang, targetLang, stylePrompt string) string`

**Changes**:
Replace the existing rules section with accuracy-focused instructions:

```go
sb.WriteString("You are a professional literary translator.\n")
sb.WriteString(fmt.Sprintf(
    "Your task is to translate text faithfully from %s to %s.\n\n",
    srcName, tgtName,
))
sb.WriteString("Rules:\n")
sb.WriteString("- Output ONLY the translated text.\n")
```

sb.WriteString("- Do NOT add commentary, explanations, or notes.\n")
sb.WriteString("- Do NOT include the original text.\n")
sb.WriteString("- Preserve the exact meaning of every sentence.\n")
sb.WriteString("- Do NOT invent or replace objects, locations, or actions.\n")
sb.WriteString("- Maintain the original paragraph structure.\n")
sb.WriteString("- Keep character names and proper nouns unchanged.\n")
sb.WriteString("- Prefer accuracy over creativity.\n")
sb.WriteString("- If a sentence is unclear, translate it literally rather than guessing.\n")
sb.WriteString(fmt.Sprintf("- Maintain natural grammar and style in %s.\n", tgtName))
```

**Rationale**: The new rules explicitly prioritize faithful translation and prohibit common LLM hallucination patterns (inventing details, summarizing).

### 2. User Prompt Enhancement

**File**: `internal/translator/prompt.go`

**Function**: `BuildUserMessage(sourceLang, targetLang, text string) string`

**Current Signature**: Keep unchanged for backward compatibility

**New Signature**: Add optional genre context parameter
```go
func BuildUserMessage(sourceLang, targetLang, text string, genreContext string) string
```

**Implementation**:
```go
func BuildUserMessage(sourceLang, targetLang, text, genreContext string) string {
    srcName := model.GetLanguageName(sourceLang)
    tgtName := model.GetLanguageName(targetLang)
    
    var sb strings.Builder
    sb.WriteString(fmt.Sprintf(
        "Translate the following text from %s into %s.\n",
        srcName, tgtName,
    ))
    sb.WriteString("Translate faithfully and preserve the meaning of every sentence. ")
    sb.WriteString("Do not summarize or invent new details.\n\n")
    
    if genreContext != "" {
        sb.WriteString(genreContext)
        sb.WriteString("\n\n")
    }
    
    sb.WriteString("Text:\n")
    sb.WriteString(text)
    
    return sb.String()
}
```

**Rationale**: Stronger instructions reduce model tendency to paraphrase or summarize. Genre context helps with domain-specific vocabulary.

### 3. Project Model Extensions

**File**: `internal/model/project.go`

**Changes**: Add new optional fields to Project struct

```go
type Project struct {
    // ... existing fields ...
    
    // New fields for translation improvements
    GenreContext      string `json:"genre_context,omitempty"`      // Optional genre hint (e.g., "The text is from a fantasy novel.")
    EnablePolishPass  bool   `json:"enable_polish_pass"`           // Enable two-pass translation
    MaxContextTokens  int    `json:"max_context_tokens,omitempty"` // Model context window size
}
```

**Default Values**:
- `GenreContext`: empty string (disabled)
- `EnablePolishPass`: false (disabled)
- `MaxContextTokens`: 32000 (safe default for most local models)

**Rationale**: Optional fields with zero-value defaults ensure backward compatibility. MaxContextTokens helps prevent context overflow with local LLMs.

### 4. Translation Sampling Defaults

**File**: `internal/translator/translator.go`

**Function**: `translateChunk()`

**Changes**: Apply intelligent defaults when ModelParams values are zero

**Implementation**:
```go
// Apply translation-optimized defaults for zero values
opts := LLMOptions{
    MaxTokens:         computeMaxOutputTokens(len(chunk.SourceText), p.MaxContextTokens),
    Temperature:       applyDefault(params.Temperature, 0.2),
    TopK:              applyDefaultInt(params.TopK, 40),
    TopP:              applyDefault(params.TopP, 0.9),
    MinP:              params.MinP,
    PresencePenalty:   params.PresencePenalty,
    RepetitionPenalty: applyDefault(params.RepetitionPenalty, 1.1),
    ThinkingMode:      params.ThinkingMode,
    Stop:              []string{"\n\nText:", "<|im_end|>"},
    Seed:              42,
}
```

**Helper Functions**:
```go
func applyDefault(value, defaultValue float32) float32 {
    if value == 0 {
        return defaultValue
    }
    return value
}

func applyDefaultInt(value, defaultValue int) int {
    if value == 0 {
        return defaultValue
    }
    return value
}

func computeMaxOutputTokens(chunkTokens int, maxContext int) int {
    const reserved = 1500 // For system prompt, user prompt, and overhead
    
    if maxContext == 0 {
        maxContext = 32000 // Default context size
    }
    
    available := maxContext - chunkTokens - reserved
    if available < 512 {
        return 512 // Minimum safe output size
    }
    
    return available
}
```

**Rationale**: 
- Temperature 0.2: Lower temperature reduces creativity, increases consistency
- TopP 0.9: Balanced nucleus sampling for quality
- TopK 40: Reasonable vocabulary constraint
- RepetitionPenalty 1.1: Mild penalty prevents loops without forcing variety
- Stop tokens: Prevent over-generation common in local models
- Seed 42: Deterministic output for reproducibility
- Dynamic MaxTokens: Prevents context overflow

These defaults are optimized for translation tasks where accuracy matters more than creativity.

### 5. Chunk Size Validation

**File**: `internal/translator/translator.go`

**New Function**: `validateChunkSize()`

```go
// validateChunkSize logs warnings for suboptimal chunk configurations.
// Small chunks reduce translation quality by limiting context.
// Large chunks may exceed safe context window limits.
func validateChunkSize(chunkSize int, maxContext int) {
    const recommendedMinTokens = 400
    
    if maxContext == 0 {
        maxContext = 32000 // Default context size
    }
    
    if chunkSize > 0 && chunkSize < recommendedMinTokens {
        log.Printf("Warning: chunk size below recommended translation length (%d tokens)", recommendedMinTokens)
    }
    
    if chunkSize > maxContext/2 {
        log.Printf("Warning: chunk size may exceed safe context window (chunk: %d, max context: %d)", chunkSize, maxContext)
    }
}
```

**Integration Point**: Call during project creation in `TranslateProject()` before starting translation

```go
func (t *Translator) TranslateProject(p *model.Project, onProgress ProgressCallback) error {
    // Validate chunk size against context window
    validateChunkSize(p.ChunkMaxSize, p.MaxContextTokens)
    
    // ... existing logic ...
}
```

**Rationale**: 
- Warns users about suboptimal configuration without blocking execution
- 400 tokens provides sufficient context for coherent translation
- Checking against maxContext/2 ensures room for output and prompts
- Prevents context overflow issues common with local LLMs

### 6. Two-Pass Translation Mode

**File**: `internal/translator/translator.go`

**Changes**: Extend `translateChunk()` to support optional polish pass

**Implementation Strategy**:

1. Perform initial translation (existing logic)
2. If `EnablePolishPass` is true, perform polish pass
3. Store polished result as final translation

**New Function**: `polishTranslation()`

```go
// polishTranslation performs a second pass to improve fluency while preserving meaning.
func (t *Translator) polishTranslation(
    ctx context.Context,
    backend LLMBackend,
    initialTranslation string,
    targetLang string,
    opts LLMOptions,
    onProgress ProgressCallback,
    p *model.Project,
    chapterIdx, chunkIdx int,
) (string, error) {
    tgtName := model.GetLanguageName(targetLang)
    
    systemPrompt := fmt.Sprintf(
        "You are a professional editor improving %s translations.\n"+
        "Your task is to enhance fluency while preserving exact meaning.\n"+
        "Do not add or remove any information.",
        tgtName,
    )
    
    userPrompt := "Edit the following translation to improve fluency.\n\n" +
        "Rules:\n" +
        "- Preserve the exact meaning.\n" +
        "- Do not add or remove information.\n" +
        "- Do not shorten the text.\n" +
        "- Do not summarize.\n" +
        "- Only improve grammar and readability.\n\n" +
        "Translation:\n" +
        initialTranslation
    
    var result strings.Builder
    tokenCount := 0
    startTime := time.Now()
    inThink := false
    
    err := backend.ChatStream(ctx, systemPrompt, userPrompt, func(token string) {
        result.WriteString(token)
        tokenCount++
        
        // Same thinking tag logic as main translation
        combined := result.String()
        openIdx := strings.LastIndex(combined, "<think>")
        closeIdx := strings.LastIndex(combined, "</think>")
        wasThinking := inThink
        inThink = openIdx != -1 && (closeIdx == -1 || closeIdx < openIdx)
        
        trimmed := strings.TrimRight(token, " \t")
        if trimmed == "<think>" || trimmed == "</think>" {
            return
        }
        
        if wasThinking && !inThink {
            token = strings.TrimSuffix(token, "</think>")
            if token == "" {
                return
            }
        }
        
        if onProgress != nil {
            elapsed := time.Since(startTime).Seconds()
            tokPerSec := 0.0
            if elapsed > 0 {
                tokPerSec = float64(tokenCount) / elapsed
            }
            onProgress(ProgressEvent{
                ProjectID:    p.ID,
                ChapterIndex: chapterIdx,
                ChunkIndex:   chunkIdx,
                EventType:    EventToken,
                Token:        token,
                IsThinking:   inThink,
                TokensPerSec: tokPerSec,
            })
        }
    }, opts)
    
    if err != nil {
        return "", err
    }
    
    return StripThinkingTags(result.String()), nil
}
```

**Integration in `translateChunk()`**:

```go
// After initial translation completes successfully
translated := StripThinkingTags(result.String())

// Optional polish pass
if p.EnablePolishPass {
    polished, err := t.polishTranslation(
        ctx, backend, translated, p.TargetLang, opts,
        onProgress, p, chapterIdx, chunkIdx,
    )
    if err != nil {
        // Log error but use initial translation as fallback
        log.Printf("Polish pass failed: %v, using initial translation", err)
    } else {
        translated = polished
    }
}

// Store final result
chunk.TranslatedText = translated
```

**Rationale**: Two-pass approach separates concerns - first pass focuses on accuracy, second pass on fluency. Fallback to initial translation ensures robustness.

### 7. LLMOptions Extensions

**File**: `internal/translator/llm.go`

**Changes**: Add fields for stop tokens and deterministic seed

```go
type LLMOptions struct {
    MaxTokens         int
    Temperature       float32
    TopK              int
    TopP              float32
    MinP              float32
    PresencePenalty   float32
    RepetitionPenalty float32
    ThinkingMode      string   // model.ThinkingDisabled / Enabled / Budget
    Stop              []string // Stop sequences to prevent over-generation
    Seed              int      // Deterministic seed for reproducibility
}
```

**Default Values**:
- `Stop`: `[]string{"\n\nText:", "<|im_end|>"}`
- `Seed`: `42`

**Rationale**: 
- Stop tokens prevent local models from continuing past the translation
- Seed enables reproducible translations for testing and debugging
- Both fields are optional and backward compatible

### 8. Backend Integration

**Files**: `internal/translator/llm_ollama.go`, `internal/translator/llm_http.go`, `internal/translator/llm_dlgo.go`

**Changes**: Update backend implementations to pass Stop and Seed to LLM APIs

**Note**: Implementation details depend on each backend's API. Backends that don't support these features should ignore them gracefully.

## Data Flow

### Standard Translation Flow
```
Source Text
    ↓
BuildSystemPrompt() → System Prompt
    ↓
BuildUserMessage() → User Prompt (with optional genre context)
    ↓
Apply Sampling Defaults → LLMOptions
    ↓
backend.ChatStream() → Initial Translation
    ↓
[Optional] polishTranslation() → Polished Translation
    ↓
StripThinkingTags() → Final Translation
    ↓
Store in Chunk
```

### Two-Pass Translation Flow
```
Initial Translation
    ↓
Polish System Prompt
    ↓
Polish User Prompt (with initial translation)
    ↓
Same LLMOptions
    ↓
backend.ChatStream() → Polished Translation
    ↓
StripThinkingTags() → Final Translation
```

## Error Handling

### Polish Pass Failures
- If polish pass fails, fall back to initial translation
- Log error for debugging
- Do not fail the entire chunk translation

### Validation Warnings
- Chunk size warnings are non-blocking
- Use standard Go logging (log.Printf)
- No user interaction required

### Backward Compatibility
- Zero values for new Project fields mean "disabled"
- Existing projects load without errors
- No database migration required

## Testing Strategy

### Unit Tests

**prompt_test.go**:
- Test BuildSystemPrompt() generates correct accuracy-focused rules
- Test BuildUserMessage() with and without genre context
- Test genre context formatting

**translator_test.go**:
- Test applyDefault() and applyDefaultInt() helper functions
- Test validateChunkSize() warning logic
- Test polishTranslation() with mock backend
- Test two-pass flow with EnablePolishPass enabled/disabled

### Integration Tests
- Test full translation with new defaults
- Test two-pass translation end-to-end
- Test backward compatibility with existing projects

### Manual Testing
- Translate sample text with Qwen 9B via Ollama
- Compare output quality with/without polish pass
- Verify genre context improves domain understanding
- Confirm chunk size warnings appear appropriately

## Performance Considerations

### Two-Pass Translation
- Doubles LLM inference time per chunk
- Optional feature - users opt-in for quality
- Progress reporting works for both passes
- No memory overhead (streaming maintained)

### Sampling Defaults
- No performance impact
- May improve inference speed slightly (lower temperature)

### Validation
- Negligible overhead (single comparison per project)

## Migration Path

### Existing Projects
- Load successfully with new code
- New fields default to disabled state
- No data migration required
- Users can enable features via UI updates (future work)

### New Projects
- Can use new features immediately
- Defaults provide good baseline behavior
- Genre context and polish pass remain opt-in

## Future Enhancements

### Potential Improvements
1. Configurable genre context presets (fantasy, sci-fi, technical, etc.)
2. UI controls for EnablePolishPass toggle
3. Per-chunk polish pass (selective polishing)
4. A/B comparison view (initial vs polished)
5. Custom polish prompts
6. Adaptive sampling based on chunk complexity

### Not in Scope
- UI changes (backend-only for now)
- Custom prompt templates
- Multi-model translation
- Quality metrics/scoring

## Correctness Properties

### Property 1: Backward Compatibility
**Validates**: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6

**Property**: Existing projects must load and translate successfully with new code

**Test Strategy**: Load existing project JSON, verify all fields parse correctly, execute translation

### Property 2: Default Application
**Validates**: Requirements 1.4

**Property**: When ModelParams values are zero, translation defaults must be applied

**Test Strategy**: Property-based test with zero-value ModelParams, verify LLMOptions contains defaults

### Property 3: Genre Context Injection
**Validates**: Requirements 1.3

**Property**: When GenreContext is non-empty, it must appear in user prompt before "Text:"

**Test Strategy**: Generate user message with genre context, verify format and position

### Property 4: Polish Pass Idempotency
**Validates**: Requirements 1.6

**Property**: Polish pass must not add or remove information from translation

**Test Strategy**: Manual review (difficult to automate), compare initial vs polished for content preservation

### Property 5: Streaming Preservation
**Validates**: Non-functional requirements

**Property**: Token streaming must work identically for both translation passes

**Test Strategy**: Verify onProgress callbacks fire correctly, thinking tag handling unchanged

## Dependencies

### Internal Dependencies
- `internal/model`: Extended with new Project fields
- `internal/translator`: Core changes to prompt and translation logic
- `internal/store`: No changes (JSON serialization handles new fields automatically)

### External Dependencies
- No new external dependencies
- Existing LLM backends work unchanged

## Rollout Plan

### Phase 1: Core Implementation
1. Update prompt.go with new prompts
2. Add Project model fields
3. Implement sampling defaults
4. Add chunk size validation

### Phase 2: Two-Pass Translation
1. Implement polishTranslation()
2. Integrate into translateChunk()
3. Add error handling and fallback

### Phase 3: Testing & Validation
1. Unit tests for all new functions
2. Integration tests for full flow
3. Manual testing with Qwen 9B

### Phase 4: Documentation
1. Update README with new features
2. Document sampling defaults
3. Add usage examples for two-pass mode

## Success Metrics

### Quality Improvements
- Reduced hallucination rate (manual evaluation)
- Improved translation accuracy (BLEU score comparison)
- Better handling of fantasy/domain-specific terms

### Usability
- Users can enable features without code changes
- Clear warnings guide configuration
- Backward compatibility maintained (zero breaking changes)

### Performance
- Two-pass mode completes within 2x time of single pass
- No memory overhead from new features
- Streaming remains responsive
