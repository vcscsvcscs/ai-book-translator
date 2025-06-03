# Translation expansion factors by language (approximate multipliers)
# These factors represent how much text typically expands when translating FROM English TO the target language

LANGUAGE_EXPANSION_FACTORS = {
    # Romance Languages
    "es": 1.2,  # Spanish
    "fr": 1.25,  # French
    "it": 1.2,  # Italian
    "pt": 1.2,  # Portuguese
    "ro": 1.2,  # Romanian
    "ca": 1.2,  # Catalan
    # Germanic Languages
    "de": 1.4,  # German
    "nl": 1.3,  # Dutch
    "sv": 1.25,  # Swedish
    "no": 1.25,  # Norwegian
    "da": 1.25,  # Danish
    "is": 1.35,  # Icelandic
    # Slavic Languages
    "ru": 1.3,  # Russian
    "pl": 1.35,  # Polish
    "cs": 1.3,  # Czech
    "sk": 1.3,  # Slovak
    "bg": 1.3,  # Bulgarian
    "mk": 1.3,  # Macedonian
    "sr": 1.3,  # Serbian
    "hr": 1.25,  # Croatian
    "bs": 1.25,  # Bosnian
    "sl": 1.3,  # Slovenian
    "uk": 1.3,  # Ukrainian
    "be": 1.3,  # Belarusian
    # Baltic Languages
    "et": 1.4,  # Estonian
    "lv": 1.35,  # Latvian
    "lt": 1.4,  # Lithuanian
    # Finno-Ugric Languages
    "hu": 1.45,  # Hungarian (Finno-Ugric, but grouped here)
    "fi": 1.4,  # Finnish
    # Turkic Languages
    "tr": 1.3,  # Turkish
    "az": 1.3,  # Azerbaijani
    "kk": 1.35,  # Kazakh
    "ky": 1.35,  # Kyrgyz
    "uz": 1.3,  # Uzbek
    "tk": 1.3,  # Turkmen
    "ug": 1.2,  # Uyghur
    # East Asian Languages
    "zh": 0.8,  # Chinese
    "ja": 0.9,  # Japanese
    "ko": 0.9,  # Korean
    # Southeast Asian Languages
    "th": 0.7,  # Thai
    "vi": 0.8,  # Vietnamese
    "id": 1.15,  # Indonesian
    "ms": 1.15,  # Malay
    "tl": 1.25,  # Tagalog
    "ceb": 1.3,  # Cebuano
    "jv": 1.2,  # Javanese
    "su": 1.25,  # Sundanese
    "my": 0.85,  # Burmese
    "km": 0.9,  # Khmer
    "lo": 0.85,  # Lao
    # Indo-Aryan Languages
    "hi": 1.1,  # Hindi
    "bn": 1.1,  # Bengali
    "ur": 1.15,  # Urdu
    "pa": 1.15,  # Punjabi
    "mr": 1.1,  # Marathi
    "gu": 1.1,  # Gujarati
    "or": 1.15,  # Odia
    "as": 1.2,  # Assamese
    "ne": 1.15,  # Nepali
    "si": 1.1,  # Sinhala
    # Dravidian Languages
    "ta": 1.05,  # Tamil
    "te": 1.1,  # Telugu
    "kn": 1.1,  # Kannada
    "ml": 1.15,  # Malayalam
    # Semitic Languages
    "ar": 1.1,  # Arabic
    "he": 1.1,  # Hebrew
    # Iranian Languages
    "fa": 1.2,  # Persian
    "ps": 1.2,  # Pashto
    "prs": 1.2,  # Dari
    "ku": 1.25,  # Kurdish
    "ckb": 1.25,  # Sorani Kurdish
    "kmr": 1.3,  # Kurmanji Kurdish
    "tg": 1.25,  # Tajik
    # African Languages
    "sw": 1.3,  # Swahili
    "ha": 1.25,  # Hausa
    "yo": 1.3,  # Yoruba
    "am": 1.2,  # Amharic
    # Other Languages
    "el": 1.25,  # Greek
    "ka": 1.2,  # Georgian
    "hy": 1.25,  # Armenian
    "sq": 1.25,  # Albanian
    "mn": 1.35,  # Mongolian
    "bo": 0.95,  # Tibetan
    "dz": 1.0,  # Dzongkha
    "dv": 1.15,  # Maldivian
    # Default fallback
    "default": 1.2,
}

# Language code to full name mapping for display purposes
LANGUAGE_NAMES = {
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "nl": "Dutch",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "pl": "Polish",
    "cs": "Czech",
    "hu": "Hungarian",
    "tr": "Turkish",
    "el": "Greek",
    "he": "Hebrew",
    "th": "Thai",
    "vi": "Vietnamese",
    "hi": "Hindi",
    "bn": "Bengali",
    "ur": "Urdu",
    "fa": "Persian",
    "sw": "Swahili",
    "ha": "Hausa",
    "yo": "Yoruba",
    "am": "Amharic",
    "id": "Indonesian",
    "ms": "Malay",
    "tl": "Tagalog",
    "ceb": "Cebuano",
    "jv": "Javanese",
    "su": "Sundanese",
    "my": "Burmese",
    "km": "Khmer",
    "lo": "Lao",
    "mn": "Mongolian",
    "bo": "Tibetan",
    "ne": "Nepali",
    "si": "Sinhala",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "mr": "Marathi",
    "or": "Odia",
    "as": "Assamese",
    "mk": "Macedonian",
    "bg": "Bulgarian",
    "sr": "Serbian",
    "hr": "Croatian",
    "bs": "Bosnian",
    "sl": "Slovenian",
    "sk": "Slovak",
    "et": "Estonian",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "ro": "Romanian",
    "sq": "Albanian",
    "ka": "Georgian",
    "hy": "Armenian",
    "az": "Azerbaijani",
    "kk": "Kazakh",
    "ky": "Kyrgyz",
    "uz": "Uzbek",
    "tg": "Tajik",
    "tk": "Turkmen",
    "ps": "Pashto",
    "prs": "Dari",
    "ku": "Kurdish",
    "ckb": "Sorani",
    "kmr": "Kurmanji",
    "ug": "Uyghur",
    "dz": "Dzongkha",
    "dv": "Maldivian",
    "uk": "Ukrainian",
    "be": "Belarusian",
    "ca": "Catalan",
    "is": "Icelandic",
    "en": "English",
}


def get_expansion_factor(source_lang: str, target_lang: str) -> float:
    """
    Get the expansion factor for translating from source_lang to target_lang.

    Args:
        source_lang: Source language code (e.g., 'en')
        target_lang: Target language code (e.g., 'es')

    Returns:
        Expansion factor as a float
    """
    # If translating from English, use the standard factors
    if source_lang.lower() == "en":
        return LANGUAGE_EXPANSION_FACTORS.get(
            target_lang.lower(), LANGUAGE_EXPANSION_FACTORS["default"]
        )

    # If translating to English, use the inverse of the source language factor
    if target_lang.lower() == "en":
        source_factor = LANGUAGE_EXPANSION_FACTORS.get(
            source_lang.lower(), LANGUAGE_EXPANSION_FACTORS["default"]
        )
        return 1.0 / source_factor

    # For non-English to non-English translations, use a compound factor
    # This is an approximation: source -> English -> target
    source_to_en = 1.0 / LANGUAGE_EXPANSION_FACTORS.get(
        source_lang.lower(), LANGUAGE_EXPANSION_FACTORS["default"]
    )
    en_to_target = LANGUAGE_EXPANSION_FACTORS.get(
        target_lang.lower(), LANGUAGE_EXPANSION_FACTORS["default"]
    )
    return source_to_en * en_to_target


def get_language_name(lang_code: str) -> str:
    """Get the full language name from a language code."""
    return LANGUAGE_NAMES.get(lang_code.lower(), lang_code.upper())
