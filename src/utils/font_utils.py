"""
Font utilities for PDF generation.
"""

import os
import platform


def register_unicode_fonts():
    """Register Unicode-compatible fonts for proper character rendering."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # Common Unicode font paths by OS
        font_paths = []
        system = platform.system().lower()

        if system == "windows":
            font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf",
                "C:/Windows/Fonts/times.ttf",
                "C:/Windows/Fonts/DejaVuSans.ttf",
            ]
        elif system == "darwin":  # macOS
            font_paths = [
                "/System/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Times.ttc",
                "/System/Library/Fonts/Helvetica.ttc",
                "/opt/homebrew/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/local/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        else:  # Linux
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
            ]

        # Try to register the first available font
        font_registered = False
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont("UnicodeFont", font_path))
                    font_registered = True
                    print(f"📝 Using Unicode font: {os.path.basename(font_path)}")
                    break
                except Exception:
                    continue

        if not font_registered:
            print("⚠️  No Unicode font found, falling back to built-in fonts")
            print("   Some characters may not display correctly")

    except Exception as e:
        print(f"⚠️  Font registration failed: {e}")


def get_unicode_font_name():
    """Get the name of the registered Unicode font."""
    try:
        from reportlab.pdfbase import pdfmetrics

        # Check if our Unicode font was registered
        if "UnicodeFont" in pdfmetrics.getRegisteredFontNames():
            return "UnicodeFont"
    except Exception:
        pass

    # Fall back to Helvetica which has better Unicode support than Times-Roman
    return "Helvetica"