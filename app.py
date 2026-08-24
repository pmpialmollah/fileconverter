"""
File Converter
==============
A Flask web application with two independent pipelines:

  Pipeline A: Any document (PDF/DOCX/XLSX/PPTX/HTML/TXT) -> clean Markdown
              via Microsoft's `markitdown` library.

  Pipeline B: Markdown -> beautifully styled, print-ready PDF document
              via `markdown` (HTML rendering) + `weasyprint` (PDF rendering),
              with full Bengali (বাংলা) + English bilingual typography support.

Author: Principal Full-Stack Engineer
"""

import os
import uuid
import logging
import traceback
from datetime import datetime, timedelta

from flask import (
    Flask, request, jsonify, render_template,
    send_file, after_this_request
)
from werkzeug.utils import secure_filename

from markitdown import MarkItDown
import markdown as md_lib
from weasyprint import HTML, CSS

# --------------------------------------------------------------------------
# App configuration
# --------------------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload limit
app.config["JSON_AS_ASCII"] = False  # allow raw UTF-8 (Bengali) in JSON responses
app.config["UPLOAD_DIR"] = UPLOAD_DIR
app.config["OUTPUT_DIR"] = OUTPUT_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("file_converter")

# Allowed input extensions for Pipeline A (Document -> Markdown)
ALLOWED_DOC_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
    "html", "htm", "txt", "csv", "json", "xml",
}

# Allowed input extensions for Pipeline B (Markdown -> PDF)
ALLOWED_MD_EXTENSIONS = {"md", "markdown", "txt"}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def allowed_file(filename: str, allowed_set: set) -> bool:
    """Check whether the filename has an extension present in allowed_set."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_set
    )


def safe_temp_path(directory: str, original_filename: str) -> str:
    """
    Build a collision-safe path inside `directory` for `original_filename`,
    preserving the original extension but using a random UUID for the stem.
    Prevents path traversal and overwrite collisions under concurrent use.
    """
    original_filename = secure_filename(original_filename) or "file"
    ext = ""
    if "." in original_filename:
        ext = "." + original_filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return os.path.join(directory, unique_name)


def cleanup_file(path: str) -> None:
    """Best-effort removal of a temp file; never raises."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError as exc:
        logger.warning("Failed to clean up temp file %s: %s", path, exc)


def build_cheat_sheet_html(markdown_text: str, title: str = "File Converter") -> str:
    """
    Convert raw Markdown text into a full, styled HTML document ready for
    WeasyPrint rendering. Wraps the markdown-generated HTML fragment inside
    the cheat-sheet template (templates/pdf_template.html rendered via
    Jinja is NOT used here directly because we need it as a raw string for
    WeasyPrint's HTML.write_pdf pipeline -- Flask's render_template is used
    instead so Jinja escaping/UTF-8 handling stays consistent).
    """
    extensions = [
        "extra",        # tables, fenced_code, footnotes, abbreviations, etc.
        "tables",
        "fenced_code",
        "toc",
        "codehilite",
        "sane_lists",
        "nl2br",
    ]
    extension_configs = {
        "codehilite": {"guess_lang": False, "noclasses": True},
        "toc": {"anchorlink": False},
    }

    html_fragment = md_lib.markdown(
        markdown_text,
        extensions=extensions,
        extension_configs=extension_configs,
        output_format="html5",
    )

    rendered = render_template(
        "pdf_template.html",
        title=title,
        content=html_fragment,
        generated_on=datetime.now().strftime("%d %B %Y, %I:%M %p"),
        fonts_dir=FONTS_DIR,
    )
    return rendered


def markdown_to_pdf_bytes(markdown_text: str, title: str = "File Converter") -> bytes:
    """Run the full Markdown -> HTML -> PDF pipeline and return PDF bytes."""
    html_string = build_cheat_sheet_html(markdown_text, title=title)
    # base_url lets WeasyPrint resolve any relative file:// font/asset paths
    pdf_bytes = HTML(string=html_string, base_url=BASE_DIR).write_pdf()
    return pdf_bytes


# --------------------------------------------------------------------------
# Routes: Pages
# --------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the single-page dual-tab UI."""
    return render_template("index.html")


# --------------------------------------------------------------------------
# Routes: Pipeline A — Document -> Markdown
# --------------------------------------------------------------------------

@app.route("/convert-to-md", methods=["POST"])
def convert_to_md():
    """
    Accepts a multipart/form-data upload under field name 'file'.
    Converts the document to Markdown using MarkItDown and returns:
      { success, markdown, filename, download_token }
    The converted .md is also persisted to OUTPUT_DIR so the client can
    fetch it via /download/<token> without re-uploading.
    """
    if "file" not in request.files:
        return jsonify(success=False, error="No file part in the request."), 400

    upload = request.files["file"]
    if upload.filename == "":
        return jsonify(success=False, error="No file was selected."), 400

    if not allowed_file(upload.filename, ALLOWED_DOC_EXTENSIONS):
        ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else "?"
        return jsonify(
            success=False,
            error=(
                f"Unsupported file type '.{ext}'. Supported: "
                + ", ".join(sorted(ALLOWED_DOC_EXTENSIONS))
            ),
        ), 400

    temp_input_path = safe_temp_path(UPLOAD_DIR, upload.filename)

    try:
        upload.save(temp_input_path)

        # Guard against empty files (0 bytes)
        if os.path.getsize(temp_input_path) == 0:
            return jsonify(success=False, error="The uploaded file is empty."), 400

        converter = MarkItDown()
        result = converter.convert(temp_input_path)
        markdown_text = result.text_content or ""

        if not markdown_text.strip():
            return jsonify(
                success=False,
                error="Conversion produced no extractable text. "
                      "The file may be image-only, corrupted, or password-protected.",
            ), 422

        # Persist output as a downloadable .md file (UTF-8 strictly enforced)
        original_stem = secure_filename(
            os.path.splitext(upload.filename)[0]
        ) or "converted"
        token = uuid.uuid4().hex
        output_filename = f"{token}.md"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(markdown_text)

        return jsonify(
            success=True,
            markdown=markdown_text,
            filename=f"{original_stem}.md",
            download_token=token,
        )

    except FileNotFoundError:
        logger.error("Input file missing during conversion: %s", temp_input_path)
        return jsonify(success=False, error="Uploaded file could not be read."), 500

    except UnicodeDecodeError:
        logger.error("Encoding error while processing %s", upload.filename)
        return jsonify(
            success=False,
            error="The file contains an unsupported text encoding and could not be decoded.",
        ), 422

    except Exception as exc:  # noqa: BLE001 - convert to a safe JSON error for the client
        logger.error("MarkItDown conversion failed: %s\n%s", exc, traceback.format_exc())
        return jsonify(
            success=False,
            error=f"Conversion failed: {str(exc)}",
        ), 500

    finally:
        cleanup_file(temp_input_path)


# --------------------------------------------------------------------------
# Routes: Pipeline B — Markdown -> PDF
# --------------------------------------------------------------------------

@app.route("/convert-to-pdf", methods=["POST"])
def convert_to_pdf():
    """
    Accepts EITHER:
      - multipart/form-data with a 'file' field (a .md/.markdown/.txt upload), OR
      - multipart/form-data / JSON with a 'markdown_text' field (pasted text)
    Optional form field 'title' sets the PDF document title / header.

    Returns the rendered PDF inline as a downloadable stream, and a base64-free
    preview is not sent back (PDFs are binary); instead a download_token+URL
    pattern is used so the frontend can preview via an <iframe>/<embed> pointing
    at /download/<token>.
    """
    markdown_text = None
    title = "File Converter"
    temp_input_path = None

    try:
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            markdown_text = payload.get("markdown_text")
            title = payload.get("title") or title
        else:
            title = request.form.get("title") or title

            if "file" in request.files and request.files["file"].filename:
                upload = request.files["file"]
                if not allowed_file(upload.filename, ALLOWED_MD_EXTENSIONS):
                    ext = (
                        upload.filename.rsplit(".", 1)[-1].lower()
                        if "." in upload.filename else "?"
                    )
                    return jsonify(
                        success=False,
                        error=f"Unsupported file type '.{ext}'. Please upload .md, .markdown, or .txt",
                    ), 400

                temp_input_path = safe_temp_path(UPLOAD_DIR, upload.filename)
                upload.save(temp_input_path)

                if os.path.getsize(temp_input_path) == 0:
                    return jsonify(success=False, error="The uploaded file is empty."), 400

                try:
                    with open(temp_input_path, "r", encoding="utf-8") as f:
                        markdown_text = f.read()
                except UnicodeDecodeError:
                    return jsonify(
                        success=False,
                        error="The file is not valid UTF-8 text. Please save it as UTF-8 and retry.",
                    ), 422
            else:
                markdown_text = request.form.get("markdown_text")

        if not markdown_text or not markdown_text.strip():
            return jsonify(
                success=False,
                error="No Markdown content provided. Paste text or upload a .md file.",
            ), 400

        pdf_bytes = markdown_to_pdf_bytes(markdown_text, title=title)

        token = uuid.uuid4().hex
        output_filename = f"{token}.pdf"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

        safe_title = secure_filename(title) or "File_Converter"

        return jsonify(
            success=True,
            filename=f"{safe_title}.pdf",
            download_token=token,
            size_kb=round(len(pdf_bytes) / 1024, 1),
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("PDF generation failed: %s\n%s", exc, traceback.format_exc())
        return jsonify(
            success=False,
            error=f"PDF generation failed: {str(exc)}",
        ), 500

    finally:
        cleanup_file(temp_input_path)


# --------------------------------------------------------------------------
# Routes: Download / Preview retrieval
# --------------------------------------------------------------------------

@app.route("/download/<token>")
def download(token):
    """
    Serve a previously generated .md or .pdf file by its opaque token.
    `token` is a hex UUID with no path separators, so this is safe against
    path traversal; we additionally validate the format defensively.
    """
    if not token.isalnum() or len(token) > 64:
        return jsonify(success=False, error="Invalid download token."), 400

    for ext, mimetype in ((".md", "text/markdown; charset=utf-8"), (".pdf", "application/pdf")):
        candidate = os.path.join(OUTPUT_DIR, f"{token}{ext}")
        if os.path.exists(candidate):
            requested_name = request.args.get("name")
            download_name = secure_filename(requested_name) if requested_name else f"download{ext}"
            return send_file(
                candidate,
                mimetype=mimetype,
                as_attachment=request.args.get("inline") != "1",
                download_name=download_name,
            )

    return jsonify(success=False, error="File not found or has expired."), 404


# --------------------------------------------------------------------------
# Error handlers
# --------------------------------------------------------------------------

@app.errorhandler(413)
def too_large(_exc):
    return jsonify(success=False, error="File too large. Maximum upload size is 25 MB."), 413


@app.errorhandler(404)
def not_found(_exc):
    if request.path.startswith(("/convert-to-md", "/convert-to-pdf", "/download")):
        return jsonify(success=False, error="Endpoint not found."), 404
    return render_template("index.html"), 200


@app.errorhandler(500)
def server_error(exc):
    logger.error("Unhandled server error: %s\n%s", exc, traceback.format_exc())
    return jsonify(success=False, error="An unexpected server error occurred."), 500


# --------------------------------------------------------------------------
# Housekeeping: purge stale output files older than 2 hours on each start
# --------------------------------------------------------------------------

def purge_old_outputs(max_age_hours: int = 2) -> None:
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    for fname in os.listdir(OUTPUT_DIR):
        fpath = os.path.join(OUTPUT_DIR, fname)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                os.remove(fpath)
        except OSError:
            continue


if __name__ == "__main__":
    purge_old_outputs()
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode, use_reloader=False)
