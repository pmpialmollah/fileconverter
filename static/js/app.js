/**
 * IELTS Study Sheet Converter & PDF Generator — Frontend Controller
 * Handles: tab switching, drag-and-drop uploads, AJAX conversion calls,
 * live preview rendering, and download triggers for both pipelines.
 */

(() => {
    "use strict";

    // ---------------------------------------------------------------
    // Tab switching
    // ---------------------------------------------------------------
    const tabBtnA = document.getElementById("tab-btn-a");
    const tabBtnB = document.getElementById("tab-btn-b");
    const panelA = document.getElementById("tab-panel-a");
    const panelB = document.getElementById("tab-panel-b");

    function activateTab(which) {
        const aActive = which === "a";
        tabBtnA.classList.toggle("active-tab", aActive);
        tabBtnB.classList.toggle("active-tab", !aActive);
        tabBtnA.setAttribute("aria-selected", String(aActive));
        tabBtnB.setAttribute("aria-selected", String(!aActive));
        panelA.classList.toggle("hidden", !aActive);
        panelB.classList.toggle("hidden", aActive);
    }
    tabBtnA.addEventListener("click", () => activateTab("a"));
    tabBtnB.addEventListener("click", () => activateTab("b"));

    // ---------------------------------------------------------------
    // Generic helpers
    // ---------------------------------------------------------------
    function showError(el, message) {
        el.textContent = message;
        el.classList.remove("hidden");
    }
    function hideError(el) {
        el.classList.add("hidden");
        el.textContent = "";
    }
    function humanFileSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        const units = ["KB", "MB", "GB"];
        let i = -1;
        do { bytes /= 1024; i++; } while (bytes >= 1024 && i < units.length - 1);
        return `${bytes.toFixed(1)} ${units[i]}`;
    }

    function setupDropzone(dropzoneEl, inputEl, onFileSelected) {
        dropzoneEl.addEventListener("click", () => inputEl.click());

        inputEl.addEventListener("change", () => {
            if (inputEl.files && inputEl.files[0]) {
                onFileSelected(inputEl.files[0]);
            }
        });

        ["dragenter", "dragover"].forEach((evtName) => {
            dropzoneEl.addEventListener(evtName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzoneEl.classList.add("dragover");
            });
        });

        ["dragleave", "drop"].forEach((evtName) => {
            dropzoneEl.addEventListener(evtName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzoneEl.classList.remove("dragover");
            });
        });

        dropzoneEl.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            if (dt && dt.files && dt.files[0]) {
                // Sync onto the underlying <input type="file"> too so a
                // subsequent form submission (if ever needed) stays consistent.
                try {
                    inputEl.files = dt.files;
                } catch (_err) {
                    /* Some browsers disallow programmatic FileList assignment; ignore. */
                }
                onFileSelected(dt.files[0]);
            }
        });
    }

    // =================================================================
    // TAB A — Document -> Markdown
    // =================================================================
    const dropzoneA = document.getElementById("dropzone-a");
    const fileInputA = document.getElementById("file-input-a");
    const filenameA = document.getElementById("filename-a");
    const convertBtnA = document.getElementById("convert-btn-a");
    const convertBtnALabel = document.getElementById("convert-btn-a-label");
    const spinnerA = document.getElementById("spinner-a");
    const previewA = document.getElementById("preview-a");
    const errorA = document.getElementById("error-a");
    const copyBtnA = document.getElementById("copy-btn-a");
    const downloadBtnA = document.getElementById("download-btn-a");

    let selectedFileA = null;
    let lastMdDownload = null; // { token, filename }

    setupDropzone(dropzoneA, fileInputA, (file) => {
        selectedFileA = file;
        filenameA.textContent = `${file.name} · ${humanFileSize(file.size)}`;
        filenameA.classList.remove("hidden");
        convertBtnA.disabled = false;
        hideError(errorA);
    });

    convertBtnA.addEventListener("click", async () => {
        if (!selectedFileA) return;

        hideError(errorA);
        convertBtnA.disabled = true;
        convertBtnALabel.textContent = "Converting…";
        spinnerA.classList.remove("hidden");
        copyBtnA.disabled = true;
        downloadBtnA.disabled = true;

        const formData = new FormData();
        formData.append("file", selectedFileA);

        try {
            const res = await fetch("/convert-to-md", { method: "POST", body: formData });
            const data = await res.json();

            if (!res.ok || !data.success) {
                throw new Error(data.error || `Server returned status ${res.status}`);
            }

            previewA.textContent = data.markdown;
            lastMdDownload = { token: data.download_token, filename: data.filename };
            copyBtnA.disabled = false;
            downloadBtnA.disabled = false;
        } catch (err) {
            showError(errorA, err.message || "Something went wrong during conversion.");
            previewA.textContent = "Converted Markdown will appear here…";
        } finally {
            convertBtnA.disabled = false;
            convertBtnALabel.textContent = "Convert to Markdown";
            spinnerA.classList.add("hidden");
        }
    });

    copyBtnA.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(previewA.textContent);
            const original = copyBtnA.textContent;
            copyBtnA.textContent = "Copied!";
            setTimeout(() => { copyBtnA.textContent = original; }, 1200);
        } catch (_err) {
            showError(errorA, "Clipboard copy failed. Please select and copy manually.");
        }
    });

    downloadBtnA.addEventListener("click", () => {
        if (!lastMdDownload) return;
        const url = `/download/${lastMdDownload.token}?name=${encodeURIComponent(lastMdDownload.filename)}`;
        window.location.href = url;
    });

    // =================================================================
    // TAB B — Markdown -> PDF
    // =================================================================
    const modePasteBtn = document.getElementById("mode-paste");
    const modeUploadBtn = document.getElementById("mode-upload");
    const pasteContainer = document.getElementById("paste-container");
    const uploadContainer = document.getElementById("upload-container");
    const markdownTextarea = document.getElementById("markdown-textarea");
    const pdfTitleInput = document.getElementById("pdf-title");

    const dropzoneB = document.getElementById("dropzone-b");
    const fileInputB = document.getElementById("file-input-b");
    const filenameB = document.getElementById("filename-b");

    const convertBtnB = document.getElementById("convert-btn-b");
    const convertBtnBLabel = document.getElementById("convert-btn-b-label");
    const spinnerB = document.getElementById("spinner-b");
    const errorB = document.getElementById("error-b");

    const pdfPreviewEmpty = document.getElementById("pdf-preview-empty");
    const pdfPreviewFrame = document.getElementById("pdf-preview-frame");
    const downloadBtnB = document.getElementById("download-btn-b");

    let inputModeB = "paste"; // "paste" | "upload"
    let selectedFileB = null;
    let lastPdfDownload = null; // { token, filename }

    function setInputMode(mode) {
        inputModeB = mode;
        const isPaste = mode === "paste";
        pasteContainer.classList.toggle("hidden", !isPaste);
        uploadContainer.classList.toggle("hidden", isPaste);
        modePasteBtn.classList.toggle("bg-white", isPaste);
        modePasteBtn.classList.toggle("shadow-sm", isPaste);
        modePasteBtn.classList.toggle("text-slate-900", isPaste);
        modePasteBtn.classList.toggle("text-slate-500", !isPaste);
        modeUploadBtn.classList.toggle("bg-white", !isPaste);
        modeUploadBtn.classList.toggle("shadow-sm", !isPaste);
        modeUploadBtn.classList.toggle("text-slate-900", !isPaste);
        modeUploadBtn.classList.toggle("text-slate-500", isPaste);
    }
    modePasteBtn.addEventListener("click", () => setInputMode("paste"));
    modeUploadBtn.addEventListener("click", () => setInputMode("upload"));

    setupDropzone(dropzoneB, fileInputB, (file) => {
        selectedFileB = file;
        filenameB.textContent = `${file.name} · ${humanFileSize(file.size)}`;
        filenameB.classList.remove("hidden");
        hideError(errorB);
    });

    convertBtnB.addEventListener("click", async () => {
        hideError(errorB);

        const title = pdfTitleInput.value.trim() || "IELTS Study Sheet";
        const formData = new FormData();
        formData.append("title", title);

        if (inputModeB === "upload") {
            if (!selectedFileB) {
                showError(errorB, "Please choose a .md file to upload first.");
                return;
            }
            formData.append("file", selectedFileB);
        } else {
            const text = markdownTextarea.value.trim();
            if (!text) {
                showError(errorB, "Please paste some Markdown content first.");
                return;
            }
            formData.append("markdown_text", text);
        }

        convertBtnB.disabled = true;
        convertBtnBLabel.textContent = "Generating…";
        spinnerB.classList.remove("hidden");
        downloadBtnB.disabled = true;

        try {
            const res = await fetch("/convert-to-pdf", { method: "POST", body: formData });
            const data = await res.json();

            if (!res.ok || !data.success) {
                throw new Error(data.error || `Server returned status ${res.status}`);
            }

            lastPdfDownload = { token: data.download_token, filename: data.filename };

            const previewUrl = `/download/${data.download_token}?inline=1`;
            pdfPreviewFrame.src = previewUrl;
            pdfPreviewFrame.classList.remove("hidden");
            pdfPreviewEmpty.classList.add("hidden");
            downloadBtnB.disabled = false;
        } catch (err) {
            showError(errorB, err.message || "Something went wrong while generating the PDF.");
        } finally {
            convertBtnB.disabled = false;
            convertBtnBLabel.textContent = "Generate PDF Cheat Sheet";
            spinnerB.classList.add("hidden");
        }
    });

    downloadBtnB.addEventListener("click", () => {
        if (!lastPdfDownload) return;
        const url = `/download/${lastPdfDownload.token}?name=${encodeURIComponent(lastPdfDownload.filename)}`;
        window.location.href = url;
    });
})();
