package model

// LanguageNames maps ISO 639-1 codes to full English names.
var LanguageNames = map[string]string{
	"af": "Afrikaans", "am": "Amharic", "ar": "Arabic", "as": "Assamese",
	"az": "Azerbaijani", "be": "Belarusian", "bg": "Bulgarian", "bn": "Bengali",
	"bo": "Tibetan", "bs": "Bosnian", "ca": "Catalan", "ckb": "Sorani Kurdish",
	"cs": "Czech", "cy": "Welsh", "da": "Danish", "de": "German",
	"dv": "Maldivian", "dz": "Dzongkha", "el": "Greek", "en": "English",
	"es": "Spanish", "et": "Estonian", "eu": "Basque", "fa": "Persian",
	"fi": "Finnish", "fr": "French", "gu": "Gujarati", "ha": "Hausa",
	"he": "Hebrew", "hi": "Hindi", "hr": "Croatian", "hu": "Hungarian",
	"hy": "Armenian", "id": "Indonesian", "is": "Icelandic", "it": "Italian",
	"ja": "Japanese", "jv": "Javanese", "ka": "Georgian", "kk": "Kazakh",
	"km": "Khmer", "kmr": "Kurmanji Kurdish", "kn": "Kannada", "ko": "Korean",
	"ku": "Kurdish", "ky": "Kyrgyz", "lo": "Lao", "lt": "Lithuanian",
	"lv": "Latvian", "mk": "Macedonian", "ml": "Malayalam", "mn": "Mongolian",
	"mr": "Marathi", "ms": "Malay", "my": "Burmese", "ne": "Nepali",
	"nl": "Dutch", "no": "Norwegian", "or": "Odia", "pa": "Punjabi",
	"pl": "Polish", "ps": "Pashto", "pt": "Portuguese", "ro": "Romanian",
	"ru": "Russian", "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian",
	"sq": "Albanian", "sr": "Serbian", "su": "Sundanese", "sv": "Swedish",
	"sw": "Swahili", "ta": "Tamil", "te": "Telugu", "tg": "Tajik",
	"th": "Thai", "tl": "Tagalog", "tk": "Turkmen", "tr": "Turkish",
	"ug": "Uyghur", "uk": "Ukrainian", "ur": "Urdu", "uz": "Uzbek",
	"vi": "Vietnamese", "yo": "Yoruba", "zh": "Chinese",
}

// ExpansionFactors maps target language codes to approximate text expansion
// multipliers when translating FROM English.
var ExpansionFactors = map[string]float64{
	"es": 1.20, "fr": 1.25, "it": 1.20, "pt": 1.20, "ro": 1.20, "ca": 1.20,
	"de": 1.40, "nl": 1.30, "sv": 1.25, "no": 1.25, "da": 1.25, "is": 1.35,
	"ru": 1.30, "pl": 1.35, "cs": 1.30, "sk": 1.30, "bg": 1.30, "mk": 1.30,
	"sr": 1.30, "hr": 1.25, "bs": 1.25, "sl": 1.30, "uk": 1.30, "be": 1.30,
	"et": 1.40, "lv": 1.35, "lt": 1.40,
	"hu": 1.45, "fi": 1.40,
	"tr": 1.30, "az": 1.30, "kk": 1.35, "ky": 1.35, "uz": 1.30, "tk": 1.30, "ug": 1.20,
	"zh": 0.80, "ja": 0.90, "ko": 0.90,
	"th": 0.70, "vi": 0.80, "id": 1.15, "ms": 1.15, "tl": 1.25,
	"my": 0.85, "km": 0.90, "lo": 0.85,
	"hi": 1.10, "bn": 1.10, "ur": 1.15, "pa": 1.15, "mr": 1.10,
	"gu": 1.10, "or": 1.15, "ne": 1.15, "si": 1.10,
	"ta": 1.05, "te": 1.10, "kn": 1.10, "ml": 1.15,
	"ar": 1.10, "he": 1.10,
	"fa": 1.20, "ps": 1.20, "ku": 1.25, "tg": 1.25,
	"sw": 1.30, "ha": 1.25, "yo": 1.30, "am": 1.20,
	"el": 1.25, "ka": 1.20, "hy": 1.25, "sq": 1.25, "mn": 1.35,
}

// GetLanguageName returns the full name for a language code, falling back to the code uppercased.
func GetLanguageName(code string) string {
	if name, ok := LanguageNames[code]; ok {
		return name
	}
	return code
}

// GetExpansionFactor returns the text expansion factor for a source→target translation.
func GetExpansionFactor(sourceLang, targetLang string) float64 {
	const defaultFactor = 1.2
	if sourceLang == "en" {
		if f, ok := ExpansionFactors[targetLang]; ok {
			return f
		}
		return defaultFactor
	}
	if targetLang == "en" {
		if f, ok := ExpansionFactors[sourceLang]; ok {
			return 1.0 / f
		}
		return 1.0 / defaultFactor
	}
	srcFactor, ok1 := ExpansionFactors[sourceLang]
	if !ok1 {
		srcFactor = defaultFactor
	}
	tgtFactor, ok2 := ExpansionFactors[targetLang]
	if !ok2 {
		tgtFactor = defaultFactor
	}
	return (1.0 / srcFactor) * tgtFactor
}

// SortedLanguageOptions returns "code - Name" strings sorted for UI display.
func SortedLanguageOptions() []string {
	// Hand-ordered common languages first, then alphabetical
	priority := []string{"en", "zh", "ja", "ko", "de", "fr", "es", "it", "pt", "ru", "ar", "hu", "pl", "cs", "tr"}
	seen := map[string]bool{}
	var result []string
	for _, code := range priority {
		if name, ok := LanguageNames[code]; ok {
			result = append(result, code+" - "+name)
			seen[code] = true
		}
	}
	// Remaining alphabetically
	codes := make([]string, 0, len(LanguageNames))
	for code := range LanguageNames {
		if !seen[code] {
			codes = append(codes, code)
		}
	}
	// simple sort
	for i := 0; i < len(codes); i++ {
		for j := i + 1; j < len(codes); j++ {
			if codes[i] > codes[j] {
				codes[i], codes[j] = codes[j], codes[i]
			}
		}
	}
	for _, code := range codes {
		result = append(result, code+" - "+LanguageNames[code])
	}
	return result
}

// CodeFromOption extracts the language code from a "code - Name" option string.
func CodeFromOption(option string) string {
	if idx := len(option); idx > 0 {
		for i, c := range option {
			if c == ' ' {
				return option[:i]
			}
		}
	}
	return option
}
