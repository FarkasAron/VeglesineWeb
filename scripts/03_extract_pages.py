"""
03_extract_pages.py
-------------------
Extracts text layout and embedded images from every unprocessed PDF in the
manifest using PyMuPDF (fitz). Falls back to Tesseract OCR for scanned pages.

Output per PDF  (pdf_stem = filename without .pdf):
  scripts/data/extracted/{pdf_stem}/page_{n}.json   — layout data for page n
  scripts/data/extracted/{pdf_stem}/figures/        — embedded image PNGs

Per-page JSON schema:
  {
    "pdf_filename": str,
    "page_number": int,          # 1-indexed
    "width": float,
    "height": float,
    "ocr_used": bool,
    "text_blocks": [
      {
        "block_no": int,
        "bbox": [x0, y0, x1, y1],
        "lines": [
          {
            "bbox": [...],
            "spans": [
              {
                "text": str,
                "font": str,
                "size": float,
                "flags": int,    # 4=bold, 2=italic, 1=superscript
                "color": int,
                "bbox": [...]
              }
            ]
          }
        ]
      }
    ],
    "image_blocks": [
      {
        "block_no": int,
        "bbox": [x0, y0, x1, y1],
        "image_filename": str,   # relative to extracted/{pdf_stem}/figures/
        "width": int,
        "height": int
      }
    ]
  }

Run standalone:
  python scripts/03_extract_pages.py

Called by the Streamlit launcher (pipeline_app.py).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

import fitz  # PyMuPDF

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPTS_DIR   = Path(__file__).parent
DATA_DIR      = SCRIPTS_DIR / "data"
MANIFEST_PATH = DATA_DIR / "manifest.json"
EXTRACTED_DIR = DATA_DIR / "extracted"

# A page is considered scanned (needs OCR) when the total extractable text
# across all blocks is shorter than this threshold.
OCR_TEXT_THRESHOLD = 80   # characters

# Render scale for OCR rasterisation (higher = better Tesseract accuracy)
OCR_DPI_SCALE = 2.0


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict) -> None:
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# OCR helpers
# ---------------------------------------------------------------------------

def _ocr_page(page: fitz.Page, log: Callable) -> list[dict]:
    """
    Rasterise `page` and run Tesseract OCR.
    Returns a list of text_blocks in the same schema as the digital path,
    but each block has a single line with a single span containing the full
    OCR text for that word/paragraph box.
    """
    try:
        import pytesseract
        from PIL import Image
        import io
    except ImportError:
        log("    [OCR] pytesseract/Pillow not installed — skipping OCR for this page.")
        return []

    # Point pytesseract at the Tesseract executable if it's not on PATH
    _TESSERACT_CANDIDATES = [
        r"C:\Users\aronf\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    if not pytesseract.pytesseract.tesseract_cmd or pytesseract.pytesseract.tesseract_cmd == "tesseract":
        import shutil
        if not shutil.which("tesseract"):
            for candidate in _TESSERACT_CANDIDATES:
                if Path(candidate).exists():
                    pytesseract.pytesseract.tesseract_cmd = candidate
                    break

    mat = fitz.Matrix(OCR_DPI_SCALE, OCR_DPI_SCALE)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    img = Image.open(io.BytesIO(pix.tobytes("png")))

    data = pytesseract.image_to_data(
        img, lang="hun",
        output_type=pytesseract.Output.DICT,
        config="--psm 6",
    )

    blocks: list[dict] = []
    block_no = 0
    n = len(data["text"])

    for i in range(n):
        word = data["text"][i].strip()
        if not word or int(data["conf"][i]) < 30:
            continue

        # Scale bounding box back to PDF coordinates
        scale = 1.0 / OCR_DPI_SCALE
        x0 = data["left"][i] * scale
        y0 = data["top"][i] * scale
        x1 = (data["left"][i] + data["width"][i]) * scale
        y1 = (data["top"][i] + data["height"][i]) * scale

        blocks.append({
            "block_no": block_no,
            "bbox": [x0, y0, x1, y1],
            "lines": [{
                "bbox": [x0, y0, x1, y1],
                "spans": [{
                    "text": word,
                    "font": "ocr",
                    "size": 12.0,
                    "flags": 0,
                    "color": 0,
                    "bbox": [x0, y0, x1, y1],
                }],
            }],
        })
        block_no += 1

    return blocks


# ---------------------------------------------------------------------------
# Per-PDF extraction
# ---------------------------------------------------------------------------

def extract_pdf(
    pdf_path: Path,
    out_dir: Path,
    log: Callable[[str], None] = print,
) -> dict:
    """
    Extract all pages of `pdf_path` into `out_dir`.

    Returns a summary:
      pages: int, images_saved: int, ocr_pages: int, ocr_used: bool
    """
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    total_images = 0
    ocr_pages = 0

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1
        w, h = page.rect.width, page.rect.height

        # ── Text blocks ─────────────────────────────────────────────────────
        raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_MEDIABOX_CLIP)
        all_text = "".join(
            span["text"]
            for block in raw.get("blocks", [])
            if block.get("type") == 0
            for line in block.get("lines", [])
            for span in line.get("spans", [])
        )

        ocr_used = len(all_text.strip()) < OCR_TEXT_THRESHOLD

        if ocr_used:
            log(f"    Page {page_number}: scanned — applying OCR...")
            try:
                text_blocks = _ocr_page(page, log)
                ocr_pages += 1
            except Exception as ocr_err:
                log(f"    [OCR] Failed: {ocr_err}. Saving page with empty text (needs manual review).")
                text_blocks = []
                ocr_used = False   # mark as not OCR'd so step 04 knows to flag it
        else:
            text_blocks = []
            for block in raw.get("blocks", []):
                if block.get("type") != 0:
                    continue
                text_blocks.append({
                    "block_no": block["number"],
                    "bbox": list(block["bbox"]),
                    "lines": [
                        {
                            "bbox": list(line["bbox"]),
                            "spans": [
                                {
                                    "text": span["text"],
                                    "font": span.get("font", ""),
                                    "size": round(span.get("size", 0), 2),
                                    "flags": span.get("flags", 0),
                                    "color": span.get("color", 0),
                                    "bbox": list(span["bbox"]),
                                }
                                for span in line.get("spans", [])
                            ],
                        }
                        for line in block.get("lines", [])
                    ],
                })

        # ── Image blocks ─────────────────────────────────────────────────────
        image_blocks = []
        img_counter = 0

        for block in raw.get("blocks", []):
            if block.get("type") != 1:   # type 1 = image block
                continue

            # Save the image from the page's image list via xref
            xref = block.get("xref", 0)
            if xref > 0:
                try:
                    base_img = doc.extract_image(xref)
                    ext = base_img.get("ext", "png")
                    fname = f"page_{page_number}_img_{img_counter}.{ext}"
                    (figures_dir / fname).write_bytes(base_img["image"])
                    img_counter += 1
                    total_images += 1
                except Exception:
                    fname = None
            else:
                fname = None

            image_blocks.append({
                "block_no": block.get("number", img_counter),
                "bbox": list(block["bbox"]),
                "image_filename": fname,
                "width": block.get("width", 0),
                "height": block.get("height", 0),
            })

        # ── Write page JSON ──────────────────────────────────────────────────
        page_data = {
            "pdf_filename": pdf_path.name,
            "page_number": page_number,
            "width": round(w, 2),
            "height": round(h, 2),
            "ocr_used": ocr_used,
            "text_blocks": text_blocks,
            "image_blocks": image_blocks,
        }

        page_json = out_dir / f"page_{page_number}.json"
        page_json.write_text(json.dumps(page_data, ensure_ascii=False, indent=2), encoding="utf-8")

    page_count = len(doc)
    doc.close()

    return {
        "pages": page_count,
        "images_saved": total_images,
        "ocr_pages": ocr_pages,
        "ocr_used": ocr_pages > 0,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    log: Callable[[str], None] = print,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    """
    Extract all PDFs in the manifest that haven't been extracted yet.
    Skips solution PDFs (is_solution_pdf=True) — they are processed together
    with their feladatsor in step 04.

    Returns summary: extracted, skipped, ocr_files, total_images
    """
    log("=== 03 - PDF szoveg es kep kinyeres ===")
    manifest = load_manifest()

    targets = [
        (fname, entry)
        for fname, entry in manifest.items()
        if entry.get("classified")
        and not entry.get("extracted")
        and not entry.get("skip_reason")
    ]

    if not targets:
        log("Nincs feldolgozando PDF. Minden mar ki van nyerve, vagy le kell tolteni a fajlokat.")
        return {"extracted": 0, "skipped": 0, "ocr_files": 0, "total_images": 0}

    total = len(targets)
    extracted_count = 0
    ocr_count = 0
    image_count = 0

    for idx, (fname, entry) in enumerate(targets):
        if progress_callback:
            progress_callback(idx, total)

        local_path = SCRIPTS_DIR / entry["local_path"]
        if not local_path.exists():
            log(f"  [HIBA] Nem talalhato: {local_path}")
            continue

        pdf_stem = local_path.stem
        out_dir = EXTRACTED_DIR / pdf_stem
        out_dir.mkdir(parents=True, exist_ok=True)

        log(f"  [{idx+1}/{total}] {fname} ...")
        try:
            result = extract_pdf(local_path, out_dir, log=log)
            entry["extracted"] = True
            entry["extraction"] = {
                "pages": result["pages"],
                "images_saved": result["images_saved"],
                "ocr_used": result["ocr_used"],
                "ocr_pages": result["ocr_pages"],
                "out_dir": str(out_dir.relative_to(SCRIPTS_DIR.parent)),
            }
            save_manifest(manifest)
            extracted_count += 1
            ocr_count += 1 if result["ocr_used"] else 0
            image_count += result["images_saved"]
            log(f"    OK - {result['pages']} oldal, {result['images_saved']} kep"
                + (" [OCR]" if result["ocr_used"] else ""))
        except Exception as exc:
            log(f"    HIBA: {exc}")

    if progress_callback:
        progress_callback(total, total)

    log(
        f"\nKesz: {extracted_count} PDF feldolgozva, "
        f"{ocr_count} OCR-rel, "
        f"{image_count} kep ossz."
    )
    return {
        "extracted": extracted_count,
        "skipped": total - extracted_count,
        "ocr_files": ocr_count,
        "total_images": image_count,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()
    sys.exit(0)
