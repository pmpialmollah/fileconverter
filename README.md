# File Converter

A Flask web app with two independent tools:

1. **Document → Markdown** — Convert PDF, DOCX, XLSX, PPTX, HTML, or TXT
   files into clean Markdown using Microsoft's `markitdown`.
2. **Markdown → PDF** — Convert Markdown (pasted or uploaded) into a
   styled, print-ready PDF using `markdown` + `weasyprint`, with full
   bilingual **English + বাংলা (Bengali)** typography support.

## Quick Start

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Then open **http://127.0.0.1:5000** in your browser.

> ⚠️ WeasyPrint requires native system libraries (Pango, Cairo, GDK-Pixbuf)
> to be installed _before_ `pip install` will work. **See
> [SETUP_GUIDE.md](SETUP_GUIDE.md) for full OS-specific installation
> instructions**, Bengali font setup, and troubleshooting.

## Authoring convention for rich documents

Pipeline B accepts plain Markdown, but also passes raw HTML through
(standard Python-Markdown behavior), so you can use these conventions in
your `.md` source for a cleaner document layout:

**Vocabulary entry block:**

```html
<div class="vocab-entry">
  <span class="word">Ubiquitous</span> <span class="pos">(adj.)</span> —
  <span class="bn-meaning">সর্বব্যাপী</span>
  <div class="synonyms">Synonyms: omnipresent, widespread</div>
  <div class="example">
    Example: Smartphones are ubiquitous today. — স্মার্টফোন আজ সর্বব্যাপী।
  </div>
</div>
```

**Callout boxes** (`vocab`, `grammar`, `tip`, `warning`):

```html
<div class="callout grammar">
  <span class="callout-label">Grammar Note</span>
  Use present perfect for ongoing relevance.
</div>
```

**Two-column dense layout** for long vocab lists:

```html
<div class="two-col">... markdown or list content ...</div>
```

Plain Markdown (headings, lists, tables, bold/italic, blockquotes) works
as-is with no special markup required.

## Project structure

See [SETUP_GUIDE.md § 8](SETUP_GUIDE.md#8-project-structure-reference).

# fileconverter
