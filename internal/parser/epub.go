package parser

import (
	"archive/zip"
	"bytes"
	"encoding/xml"
	"fmt"
	"io"
	"os"
	"path"
	"strings"

	"golang.org/x/net/html"
)

type EPUBParser struct{}

type containerXML struct {
	XMLName   xml.Name `xml:"container"`
	Rootfiles []struct {
		FullPath  string `xml:"full-path,attr"`
		MediaType string `xml:"media-type,attr"`
	} `xml:"rootfiles>rootfile"`
}

type opfPackage struct {
	XMLName  xml.Name    `xml:"package"`
	Metadata opfMetadata `xml:"metadata"`
	Manifest opfManifest `xml:"manifest"`
	Spine    opfSpine    `xml:"spine"`
}

type opfMetadata struct {
	Titles []string `xml:"title"`
}

type opfManifest struct {
	Items []opfItem `xml:"item"`
}

type opfItem struct {
	ID        string `xml:"id,attr"`
	Href      string `xml:"href,attr"`
	MediaType string `xml:"media-type,attr"`
}

type opfSpine struct {
	ItemRefs []opfItemRef `xml:"itemref"`
}

type opfItemRef struct {
	IDRef string `xml:"idref,attr"`
}

func (p *EPUBParser) Parse(filePath string) ([]ParsedChapter, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("read epub: %w", err)
	}

	zipReader, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return nil, fmt.Errorf("open epub zip: %w", err)
	}

	containerData, err := readZipFile(zipReader, "META-INF/container.xml")
	if err != nil {
		return nil, fmt.Errorf("read epub container.xml: %w", err)
	}

	var container containerXML
	if err := xml.Unmarshal(containerData, &container); err != nil {
		return nil, fmt.Errorf("parse epub container.xml: %w", err)
	}
	if len(container.Rootfiles) == 0 {
		return nil, fmt.Errorf("no rootfile found in epub container.xml")
	}

	rootFile := container.Rootfiles[0].FullPath
	rootDir := path.Dir(rootFile)

	opfData, err := readZipFile(zipReader, rootFile)
	if err != nil {
		return nil, fmt.Errorf("read OPF: %w", err)
	}

	var pkg opfPackage
	if err := xml.Unmarshal(opfData, &pkg); err != nil {
		return nil, fmt.Errorf("parse OPF: %w", err)
	}

	itemMap := make(map[string]opfItem)
	for _, item := range pkg.Manifest.Items {
		itemMap[item.ID] = item
	}

	var chapters []ParsedChapter
	for i, ref := range pkg.Spine.ItemRefs {
		item, ok := itemMap[ref.IDRef]
		if !ok {
			continue
		}
		if !isContentType(item.MediaType) {
			continue
		}

		href := item.Href
		if rootDir != "." && rootDir != "" {
			href = rootDir + "/" + item.Href
		}

		content, err := readZipFile(zipReader, href)
		if err != nil {
			continue
		}

		text := extractText(content)
		if strings.TrimSpace(text) == "" {
			continue
		}

		title := fmt.Sprintf("Chapter %d", i+1)

		chapters = append(chapters, ParsedChapter{
			Title:   title,
			Content: text,
			Ref:     item.Href,
		})
	}

	if len(chapters) == 0 {
		return nil, fmt.Errorf("no text content found in epub")
	}

	return chapters, nil
}

func readZipFile(zr *zip.Reader, name string) ([]byte, error) {
	for _, f := range zr.File {
		if f.Name == name {
			rc, err := f.Open()
			if err != nil {
				return nil, err
			}
			defer rc.Close()
			return io.ReadAll(rc)
		}
	}
	return nil, fmt.Errorf("file %s not found in zip", name)
}

func isContentType(mediaType string) bool {
	return mediaType == "application/xhtml+xml" || mediaType == "text/html"
}

func extractText(xhtmlData []byte) string {
	doc, err := html.Parse(bytes.NewReader(xhtmlData))
	if err != nil {
		return string(xhtmlData)
	}

	var sb strings.Builder
	var walk func(*html.Node)
	walk = func(n *html.Node) {
		if n.Type == html.TextNode {
			text := strings.TrimSpace(n.Data)
			if text != "" {
				sb.WriteString(text)
				sb.WriteString(" ")
			}
		}
		if n.Type == html.ElementNode {
			switch n.Data {
			case "p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote":
				sb.WriteString("\n")
			}
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
		if n.Type == html.ElementNode {
			switch n.Data {
			case "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote":
				sb.WriteString("\n")
			}
		}
	}
	walk(doc)

	lines := strings.Split(sb.String(), "\n")
	var cleaned []string
	for _, l := range lines {
		l = strings.TrimSpace(l)
		if l != "" {
			cleaned = append(cleaned, l)
		}
	}
	return strings.Join(cleaned, "\n")
}
