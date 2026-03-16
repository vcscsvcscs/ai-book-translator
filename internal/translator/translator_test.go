package translator

import (
	"testing"
)

func TestApplyDefault(t *testing.T) {
	tests := []struct {
		name         string
		value        float32
		defaultValue float32
		expected     float32
	}{
		{
			name:         "zero value returns default",
			value:        0,
			defaultValue: 0.2,
			expected:     0.2,
		},
		{
			name:         "non-zero value returns value",
			value:        0.5,
			defaultValue: 0.2,
			expected:     0.5,
		},
		{
			name:         "negative value returns value",
			value:        -0.1,
			defaultValue: 0.2,
			expected:     -0.1,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := applyDefault(tt.value, tt.defaultValue)
			if result != tt.expected {
				t.Errorf("applyDefault(%v, %v) = %v, want %v", tt.value, tt.defaultValue, result, tt.expected)
			}
		})
	}
}

func TestApplyDefaultInt(t *testing.T) {
	tests := []struct {
		name         string
		value        int
		defaultValue int
		expected     int
	}{
		{
			name:         "zero value returns default",
			value:        0,
			defaultValue: 40,
			expected:     40,
		},
		{
			name:         "non-zero value returns value",
			value:        100,
			defaultValue: 40,
			expected:     100,
		},
		{
			name:         "negative value returns value",
			value:        -10,
			defaultValue: 40,
			expected:     -10,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := applyDefaultInt(tt.value, tt.defaultValue)
			if result != tt.expected {
				t.Errorf("applyDefaultInt(%v, %v) = %v, want %v", tt.value, tt.defaultValue, result, tt.expected)
			}
		})
	}
}

func TestComputeMaxOutputTokens(t *testing.T) {
	tests := []struct {
		name        string
		chunkTokens int
		maxContext  int
		expected    int
	}{
		{
			name:        "default context with small chunk",
			chunkTokens: 1000,
			maxContext:  0,
			expected:    29500, // 32000 - 1000 - 1500
		},
		{
			name:        "custom context with medium chunk",
			chunkTokens: 5000,
			maxContext:  16000,
			expected:    9500, // 16000 - 5000 - 1500
		},
		{
			name:        "large chunk near context limit",
			chunkTokens: 30000,
			maxContext:  32000,
			expected:    512, // minimum safe output size
		},
		{
			name:        "chunk exceeds context limit",
			chunkTokens: 35000,
			maxContext:  32000,
			expected:    512, // minimum safe output size
		},
		{
			name:        "small context window",
			chunkTokens: 500,
			maxContext:  2000,
			expected:    512, // 2000 - 500 - 1500 = 0, but minimum is 512
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := computeMaxOutputTokens(tt.chunkTokens, tt.maxContext)
			if result != tt.expected {
				t.Errorf("computeMaxOutputTokens(%v, %v) = %v, want %v", tt.chunkTokens, tt.maxContext, result, tt.expected)
			}
		})
	}
}
