# Setup & Installation Guide

## File Converter

This guide walks through everything needed to run the app locally: system
dependencies for WeasyPrint, Bengali font setup, the Python environment,
and starting the server.

---

## 1. Why system dependencies matter

WeasyPrint does **not** render PDFs itself — it hands layout and text
shaping off to **Pango** (text layout + complex script shaping, which is
what makes Bengali conjuncts render correctly instead of as broken boxes),
**Cairo** (2D graphics), **GDK-Pixbuf** (image loading), and **fontconfig**
(font discovery). These are native C libraries, not Python packages, so
`pip install weasyprint` alone is not enough — the OS-level libraries must
exist first, or `import weasyprint` will fail with an `OSError` mentioning
`libgobject` or `libpango`.

Install system dependencies **before** `pip install -r requirements.txt`.

---

## 2. System-level dependencies by OS

### Ubuntu / Debian Linux

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-pip python3-venv python3-dev \
    libpango-1.0-0 libpangocairo-1.0-0 \
    libcairo2 libgdk-pixbuf2.0-0 \
    libffi-dev libjpeg-dev libopenjp2-7-dev \
    fontconfig fonts-dejavu-core \
    shared-mime-info
```

`fontconfig` is what lets WeasyPrint discover installed fonts (including
Bengali fonts you install in step 3). `shared-mime-info` improves file-type
detection used by some `markitdown` parsers.

### Fedora / RHEL / CentOS

```bash
sudo dnf install -y \
    python3-pip python3-devel \
    pango cairo cairo-gobject \
    gdk-pixbuf2 \
    libffi-devel \
    fontconfig dejavu-sans-fonts
```

### macOS (via Homebrew)

```bash
brew install python pango cairo gdk-pixbuf libffi fontconfig
```

If you're on Apple Silicon and pip can't find the native libs, export:

```bash
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
```

Add that line to your `~/.zshrc` or `~/.bash_profile` so it persists across
terminal sessions.

### Windows

WeasyPrint on native Windows requires the GTK3 runtime (which bundles
Pango/Cairo/GDK-Pixbuf). Two supported paths:

**Option A — GTK3 Runtime installer (simplest):**

1. Download the GTK3 runtime installer from the MSYS2/GTK project (search
   "GTK3 runtime Windows installer" — the commonly used one is maintained
   at `gtk-for-windows-runtime-environment-installer` on GitHub releases).
2. Run the installer, accepting defaults (it installs to `C:\Program Files\GTK3-Runtime Win64`).
3. Restart your terminal so `PATH` picks up the new DLLs.
4. Proceed with the normal `pip install -r requirements.txt`.

**Option B — WSL2 (recommended for reliability):**

1. Install WSL2 with an Ubuntu distro: `wsl --install -d Ubuntu`.
2. Follow the **Ubuntu / Debian Linux** instructions above _inside_ WSL2.
3. Run the Flask app inside WSL2; it's reachable from Windows at
   `http://localhost:5000` as normal.

WSL2 avoids the notoriously fiddly native GTK3-on-Windows DLL path issues,
so it's the path of least resistance if Option A gives you `OSError:
cannot load library 'libgobject-2.0-0'` errors.

---

## 3. Bengali font installation

The app **bundles static, print-safe instances of Noto Sans Bengali and
Noto Sans** directly inside the project's `fonts/` directory and loads them
via `@font-face` `file://` URLs in `templates/pdf_template.html`. This means
**PDF output is reproducible across machines regardless of what's installed
system-wide** — you do not strictly need to install any fonts system-wide
for the PDF pipeline to work.

The bundled fonts are already present at:

```
fonts/NotoSans-Static-Regular.ttf
fonts/NotoSans-Static-Bold.ttf
fonts/NotoSansBengali-Static-Regular.ttf
fonts/NotoSansBengali-Static-Bold.ttf
```

> **Why "static instance" and not the variable font directly?** Google
> Fonts ships Noto Sans / Noto Sans Bengali as variable fonts (one file
> covering a weight range). WeasyPrint's Pango-based text shaper is more
> reliable with static, single-weight TTFs for complex-script (Bengali)
> shaping. The bundled files were generated with `fonttools varLib.instancer`
> pinned to weight 400 and 700. If you ever need to regenerate them:
>
> ```bash
> pip install fonttools
> fonttools varLib.instancer NotoSansBengali-VF.ttf wght=400 wdth=100 -o NotoSansBengali-Static-Regular.ttf
> fonttools varLib.instancer NotoSansBengali-VF.ttf wght=700 wdth=100 -o NotoSansBengali-Static-Bold.ttf
> ```

### Optional: using Kalpurush or SolaimanLipi instead

If you prefer the more traditional Bangladeshi desktop-publishing look of
**Kalpurush** or **SolaimanLipi** (both are freeware, commonly bundled with
Avro Keyboard / distributed by omicronlab.com):

1. Download `Kalpurush.ttf` and/or `SolaimanLipi.ttf`.
2. Place them in the project's `fonts/` directory.
3. In `templates/pdf_template.html`, uncomment the two `@font-face` blocks
   for `Kalpurush` / `SolaimanLipi` (they're already written, just commented
   out) and adjust the `font-family` stacks in the `body` and `:lang(bn)`
   rules to put your preferred font first.

### Optional: system-wide installation (for viewing raw HTML in a browser)

If you want the raw `pdf_template.html` to also look correct when opened
directly in a browser (outside of WeasyPrint), install the fonts system-wide:

**Ubuntu/Debian:**

```bash
mkdir -p ~/.local/share/fonts
cp fonts/*.ttf ~/.local/share/fonts/
fc-cache -f -v
```

**macOS:** double-click each `.ttf` file in Finder and click "Install Font",
or copy them to `~/Library/Fonts/`.

**Windows:** right-click each `.ttf` file → "Install".

Verify Linux font registration:

```bash
fc-list | grep -i "noto sans bengali"
```

---

## 4. Python environment setup

From the project root:

```bash
# 1. Create a virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows (cmd)
venv\Scripts\Activate.ps1       # Windows (PowerShell)

# 3. Upgrade pip (recommended)
pip install --upgrade pip

# 4. Install project dependencies
pip install -r requirements.txt
```

### Verifying WeasyPrint can actually import (before running the app)

```bash
python3 -c "import weasyprint; print('WeasyPrint OK:', weasyprint.__version__)"
```

If this fails with something like:

```
OSError: cannot load library 'libgobject-2.0-0': ...
```

it means step 2 (system dependencies) was skipped or the libraries aren't
on your library search path. Revisit section 2 for your OS.

### Verifying MarkItDown extras installed correctly

```bash
python3 -c "from markitdown import MarkItDown; print('MarkItDown OK')"
```

If PDF/DOCX/PPTX/XLSX conversions fail with import errors about missing
`pdfminer`, `mammoth`, `python-pptx`, or `openpyxl`, double check that
`requirements.txt` installed `markitdown[all]` and not the bare
`markitdown` package (see the comment in `requirements.txt`).

---

## 5. Running the app locally

```bash
python3 app.py
```

By default this starts the Flask development server on:

```
http://127.0.0.1:5000
```

Open that URL in your browser. You should see the dual-tab interface —
**"Document → Markdown"** and **"Markdown → PDF"**.

### Environment variables

| Variable      | Default | Purpose                                           |
| ------------- | ------- | ------------------------------------------------- |
| `FLASK_DEBUG` | `1`     | Set to `0` to disable Flask debug mode/tracebacks |

```bash
FLASK_DEBUG=0 python3 app.py
```

### Running with Gunicorn (production-style local run)

The dev server (`app.run(...)`) is fine for local testing, but for anything
resembling production use `gunicorn` (already in `requirements.txt`):

```bash
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 120 app:app
```

`--timeout 120` is worth keeping generous since large document conversions
(especially big PDFs/PPTX via `markitdown`) and PDF rendering can take a
few seconds longer than Gunicorn's 30s default under load.

---

## 6. Quick smoke test checklist

After starting the server, verify both pipelines work end-to-end:

1. **Tab A (Document → Markdown):** Upload any `.docx` or `.pdf` file
   containing both English and Bengali text. Confirm the preview shows
   correct Bengali characters (not `?????` or mojibake), then click
   "Download .md" and open the downloaded file in a text editor to confirm
   it's valid UTF-8.

2. **Tab B (Markdown → PDF):** Paste this into the textarea:

   ```markdown
   # Test Sheet

   **Ubiquitous** (adj.) — সর্বব্যাপী

   Synonyms: omnipresent, widespread

   | Word      | Bengali      |
   | --------- | ------------ |
   | Resilient | স্থিতিস্থাপক |
   ```

   Click "Generate PDF". The preview pane should show a styled PDF with the
   Bengali text rendered as connected script (conjuncts like
   ব্য, স্থ should look like single joined glyphs, not separate broken
   pieces or empty boxes). Click "Download PDF" to confirm the file saves
   correctly.

---

## 7. Common troubleshooting

| Symptom                                                                                | Likely cause                                                                                                                    | Fix                                                                                                                                                                                                         |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OSError: cannot load library 'libgobject-2.0-0'` on `import weasyprint`               | System deps (Pango/Cairo/GDK-Pixbuf) not installed                                                                              | Revisit section 2 for your OS                                                                                                                                                                               |
| Bengali text shows as empty boxes (☐☐☐) in the PDF                                     | Font files missing from `fonts/` or `@font-face` `src` path wrong                                                               | Confirm `fonts/*.ttf` exist; check the `fonts_dir` path passed into `pdf_template.html` resolves correctly (it's derived from `BASE_DIR` in `app.py` — don't move `app.py` without updating relative paths) |
| Bengali conjuncts look "broken apart" (e.g. ক্ষ renders as ক + ্ + ষ visibly separate) | Using a font without proper Bengali OpenType shaping tables, or a variable font Pango can't shape correctly                     | Use the bundled static Noto Sans Bengali instances; avoid raw variable-font `.ttf` files for body text                                                                                                      |
| `markitdown` conversion fails on `.pptx`/`.xlsx`/`.docx` with `ImportError`            | Installed bare `markitdown` instead of `markitdown[all]`                                                                        | `pip install "markitdown[all]==0.1.5"`                                                                                                                                                                      |
| Upload succeeds but Markdown preview is empty                                          | Source file is image-only/scanned (no extractable text layer)                                                                   | Expected — MarkItDown does not perform OCR by default; the app returns a clear error message in this case                                                                                                   |
| `413 Request Entity Too Large`                                                         | File exceeds the 25 MB upload cap                                                                                               | Increase `MAX_CONTENT_LENGTH` in `app.py` if you need larger uploads                                                                                                                                        |
| PDF generates but layout looks squeezed/overlapping on some machines                   | A parent OS is substituting Bengali fallback glyphs incorrectly on a _browser_ preview of the raw HTML (not through WeasyPrint) | This only affects browser preview of the raw template, not the actual WeasyPrint-rendered PDF; install fonts system-wide per section 3 if you need browser parity                                           |

---

## 8. Project structure reference

```
file-converter/
├── app.py                       # Flask app: routes, conversion pipelines, error handling
├── requirements.txt             # Pinned Python dependencies
├── SETUP_GUIDE.md               # This file
├── fonts/
│   ├── NotoSans-Static-Regular.ttf
│   ├── NotoSans-Static-Bold.ttf
│   ├── NotoSansBengali-Static-Regular.ttf
│   └── NotoSansBengali-Static-Bold.ttf
├── templates/
│   ├── index.html               # Dual-tab UI (drag-drop, AJAX, live preview)
│   └── pdf_template.html        # WeasyPrint-rendered document HTML/CSS
├── static/
│   ├── css/
│   │   └── style.css            # Supplementary styles beyond Tailwind CDN utilities
│   └── js/
│       └── app.js               # Tab switching, drag-drop, fetch()-based AJAX logic
├── uploads/                     # Transient input files (auto-cleaned per-request)
└── outputs/                     # Generated .md/.pdf files served via /download/<token>
                                  # (auto-purged after 2 hours on server start)
```
