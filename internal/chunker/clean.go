package chunker

import (
	"regexp"
	"strings"
)

var (
	reHTMLTag     = regexp.MustCompile(`<[^>]+>`)
	reHTMLEntity  = regexp.MustCompile(`&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;`)
	reMultiSpace  = regexp.MustCompile(`[ \t]{2,}`)
	reMultiNewline = regexp.MustCompile(`\n{3,}`)
)

// CleanText strips HTML tags, decodes common entities, and normalises whitespace.
func CleanText(text string) string {
	// Remove HTML tags
	text = reHTMLTag.ReplaceAllString(text, " ")

	// Decode common HTML entities
	text = strings.NewReplacer(
		"&amp;", "&",
		"&lt;", "<",
		"&gt;", ">",
		"&quot;", `"`,
		"&apos;", "'",
		"&nbsp;", " ",
		"&mdash;", "—",
		"&ndash;", "–",
		"&hellip;", "…",
		"&laquo;", "«",
		"&raquo;", "»",
		"&ldquo;", "\u201C",
		"&rdquo;", "\u201D",
		"&lsquo;", "\u2018",
		"&rsquo;", "\u2019",
	).Replace(text)

	// Remove remaining numeric/hex entities
	text = reHTMLEntity.ReplaceAllString(text, "")

	// Normalise whitespace
	text = reMultiSpace.ReplaceAllString(text, " ")
	text = reMultiNewline.ReplaceAllString(text, "\n\n")

	return strings.TrimSpace(text)
}
